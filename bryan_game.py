"""Motor narrativo de Bryan. MongoDB guarda contenido y progreso por separado.

Los botones envían acciones, nunca destinos ni puntos. El historial es de lectura.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import secrets

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

STORY_VERSION = 1
FIRST_SCENE = 'bryan_s01'
COOKIE = 'uf_player'
INITIAL_FLAGS = {
    'mesa_intacta': True, 'bicicleta_arreglada': False, 'pollo_alimentado': False,
    'foto_encontrada': False, 'ayudo_fiesta': False, 'agua': False,
    'puntos_responsabilidad': 0, 'final': ''
}
FINAL_NAMES = {'A':'Por lo menos ayudaste', 'B':'Ya no me pidan favores', 'C':'El favor más caro'}

def matches(when, flags):
    return all(flags.get(key) == value for key, value in (when or {}).items())

def resolve_lines(lines, flags):
    return [{'character': x['character'], 'text': x['text']} for x in lines if matches(x.get('when'), flags)]

def effects(part, changes):
    changes = changes or {}
    part['flags'].update(changes.get('set', {}))
    part['flags']['puntos_responsabilidad'] = max(0, min(3,
        part['flags']['puntos_responsabilidad'] + changes.get('responsibility', 0)))
    for item in changes.get('remove_inventory', []):
        if item in part['inventory']: part['inventory'].remove(item)
    for item in changes.get('add_inventory', []):
        if item not in part['inventory']: part['inventory'].append(item)

def record(part, character, text, kind='dialogue'):
    part['history'].append({
        'character': character, 'text': text, 'kind': kind,
        'scene_id':part['scene_id'], 'title':part['scene_title'],
        'background':part['background'], 'objective':part['objective'],
        'theme':part.get('theme','day'), 'evidence':part.get('evidence','')
    })

def record_current(part):
    current = part['lines'][part['line_index']]
    record(part, current['character'], current['text'])

def enter_scene(part, scene):
    if scene.get('calculate_final'):
        flags = part['flags']; points = flags['puntos_responsabilidad']
        flags['final'] = 'A' if points >= 3 and flags['ayudo_fiesta'] else 'C' if points <= 1 else 'B'
    effects(part, scene.get('entry_effects'))
    part.update({
        'scene_id':scene['_id'], 'scene_title':scene['title'], 'background':scene['background'],
        'objective':scene['objective'], 'theme':scene.get('theme','day'), 'evidence':scene.get('evidence',''),
        'lines':resolve_lines(scene['dialogues'],part['flags']) or [{'character':'NARRADOR','text':'Observa el lugar. Puedes explorar antes de continuar.'}],
        'line_index':0, 'pending_next':None, 'used_choices':[], 'puzzle_progress':[],
        'needs_cleanup':False, 'complete':bool(scene.get('ending'))
    })
    record_current(part)

def new_part(owner_hash, scene):
    now = datetime.now(timezone.utc)
    part = {'owner_hash':owner_hash, 'case_id':'bryan', 'story_version':STORY_VERSION,
            'revision':0, 'csrf':secrets.token_urlsafe(32), 'created_at':now, 'updated_at':now,
            'flags':deepcopy(INITIAL_FLAGS), 'inventory':[], 'history':[],
            'decisions':[], 'puzzles_solved':[], 'puzzle_errors':0}
    enter_scene(part, scene)
    return part

def ready(part):
    return part['line_index'] == len(part['lines']) - 1

def available_choices(part, scene):
    if not ready(part) or part.get('pending_next'): return []
    return [x for x in scene.get('choices', []) if matches(x.get('when'),part['flags'])
            and not (x.get('once') and x['id'] in part['used_choices'])]

def respond(part, lines, next_scene=None):
    resolved = resolve_lines(lines, part['flags'])
    part['pending_next'] = next_scene
    if resolved:
        part['lines'].extend(resolved)
        part['line_index'] += 1
        record_current(part)
        return True
    return False

def advance(part, scene, action, value, get_scene):
    """Devuelve si la acción es válida; solo se ejecuta sobre el avance actual."""
    if action == 'next':
        if not ready(part):
            part['line_index'] += 1; record_current(part); return True
        destination = part.get('pending_next') or scene.get('next')
        if destination:
            enter_scene(part,get_scene(destination)); return True
        return False
    if not ready(part) or part.get('pending_next') or part.get('complete'): return False
    if action == 'choice':
        selected = next((x for x in available_choices(part,scene) if x['id'] == value),None)
        if not selected: return False
        if selected.get('once'): part['used_choices'].append(selected['id'])
        part['decisions'].append({'scene_id':scene['_id'],'id':selected['id'],'text':selected['text']})
        record(part,'ELECCIÓN',selected['text'],'choice')
        effects(part,selected.get('effects'))
        destination = selected.get('next')
        if not respond(part,selected.get('response',[]),destination) and destination:
            enter_scene(part,get_scene(destination))
        return True
    puzzle = scene.get('puzzle')
    if not puzzle: return False
    if action == 'hint':
        respond(part,[{'character':'PISTA','text':puzzle['hint']}]); return True
    if action == 'cleanup':
        if not part.get('needs_cleanup'): return False
        part['needs_cleanup'] = False; part['puzzle_progress'] = []
        respond(part,[{'character':'NARRADOR','text':'Bryan recoge las sillas caídas. Puedes volver a intentarlo.'}]); return True
    if action != 'puzzle' or part.get('needs_cleanup'): return False
    allowed = [x['id'] for x in puzzle['options']]
    if value not in allowed or value in part['puzzle_progress']: return False
    if puzzle['type'] == 'sequence':
        correct = value == puzzle['sequence'][len(part['puzzle_progress'])]
    else:
        correct = value == puzzle['answer']
    text = next(x['text'] for x in puzzle['options'] if x['id'] == value)
    record(part,'INTERACCIÓN',text,'puzzle')
    if not correct:
        part['puzzle_errors'] += 1; part['puzzle_progress'] = []
        part['needs_cleanup'] = bool(puzzle.get('cleanup'))
        respond(part,puzzle['wrong']); return True
    part['puzzle_progress'].append(value)
    done = puzzle['type'] == 'single' or part['puzzle_progress'] == puzzle['sequence']
    if done:
        if scene['_id'] not in part['puzzles_solved']: part['puzzles_solved'].append(scene['_id'])
        respond(part,puzzle['success'],puzzle['next'])
    else:
        respond(part,[{'character':'NARRADOR','text':f'{text}: apartado. Continúa con el siguiente objeto.'}])
    return True

def create_game_blueprint(database):
    bp = Blueprint('bryan', __name__)
    scenes = database['escenas']; saves = database['partidas']
    seeded = False

    def seed():
        nonlocal seeded
        if seeded: return
        path = Path(__file__).parent / 'data' / 'caso_bryan.json'
        for doc in json.loads(path.read_text(encoding='utf-8')):
            # Respeta las escenas editadas en MongoDB y conserva los documentos antiguos.
            scenes.update_one({'_id':doc['_id']},{'$setOnInsert':doc},upsert=True)
        saves.create_index([('owner_hash',1),('case_id',1),('story_version',1),('created_at',-1)])
        seeded = True

    def get_scene(id):
        scene = scenes.find_one({'_id':id,'case_id':'bryan','schema_version':2})
        if not scene: abort(404,description='No se encontró la escena del guion.')
        return scene

    def load():
        seed()
        token = request.cookies.get(COOKIE,'')
        if not re_token(token): token = secrets.token_urlsafe(32)
        owner = sha256(token.encode()).hexdigest()
        part = saves.find_one({'owner_hash':owner,'case_id':'bryan','story_version':STORY_VERSION},sort=[('created_at',-1),('_id',-1)])
        if part is None:
            part = new_part(owner,get_scene(FIRST_SCENE))
            part['_id'] = saves.insert_one(part).inserted_id
        return part, token

    def response_with_cookie(response, token):
        response.set_cookie(COOKIE,token,max_age=60*60*24*30,httponly=True,
                            secure=bool(os.environ.get('RENDER')) or request.is_secure,samesite='Lax')
        response.headers['Cache-Control'] = 'no-store'
        return response

    def play():
        part, token = load()
        if request.method == 'POST':
            supplied = request.form.get('csrf','')
            if not secrets.compare_digest(supplied,part['csrf']): abort(400,description='Esta partida cambió. Recarga la página para continuar.')
            try: revision = int(request.form.get('revision','-1'))
            except ValueError: abort(400,description='El avance recibido no es válido.')
            if revision != part['revision']:
                return response_with_cookie(redirect(url_for('juego_bryan'),code=303),token)
            action = request.form.get('action','')
            if action == 'restart':
                fresh = new_part(part['owner_hash'],get_scene(FIRST_SCENE))
                fresh['_id'] = saves.insert_one(fresh).inserted_id
            else:
                scene = get_scene(part['scene_id'])
                if not advance(part,scene,action,request.form.get('value',''),get_scene):
                    abort(400,description='Esa acción no está disponible en este momento.')
                part['revision'] += 1; part['updated_at'] = datetime.now(timezone.utc)
                saves.replace_one({'_id':part['_id'],'revision':revision},part)
            return response_with_cookie(redirect(url_for('juego_bryan'),code=303),token)
        scene = get_scene(part['scene_id'])
        last = len(part['history'])-1
        cursor = request.args.get('h',type=int)
        if cursor is None: cursor = last
        cursor = max(0,min(cursor,last)); reading = cursor != last
        entry = part['history'][cursor]
        puzzle = scene.get('puzzle') if ready(part) and not part.get('pending_next') and not part['complete'] else None
        options = [x for x in (puzzle or {}).get('options',[]) if x['id'] not in part['puzzle_progress']]
        can_next = not ready(part) or bool(part.get('pending_next') or scene.get('next'))
        response = make_response(render_template('juego.html',part=part,scene=scene,entry=entry,
            reading=reading,cursor=cursor,last=last,choices=available_choices(part,scene),puzzle=puzzle,
            puzzle_options=options,can_next=can_next,final_names=FINAL_NAMES))
        return response_with_cookie(response,token)

    @bp.route('/caso/bryan/historial')
    def history():
        part, token = load()
        response = make_response(render_template('juego_historial.html',part=part,final_names=FINAL_NAMES))
        return response_with_cookie(response,token)

    return bp, play

def re_token(token):
    return 32 <= len(token) <= 100 and all(c.isascii() and (c.isalnum() or c in '_-') for c in token)
