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
from escena_visual import presentation

from flask import Blueprint, abort, g, make_response, redirect, render_template, request, url_for

STORY_VERSION = 1
FIRST_SCENE = 'bryan_s01'
BEDROOM_SCENE = 'bryan_s01_mensaje'
BEDROOM_REALIZATION = '¡LA MESA!'
BEDROOM_EXPLORE = 'La mesa plegable… ¿Dónde la dejé?'
BEDROOM_EXPLORATION_LINES = {
    'mochila': 'Solo tengo que llevar la mesa.',
    'ventilador': 'Luego veo qué le pasa.',
    'zapato': 'Listo. Ahora sí, a la cocina.',
    'cocina': 'Los dejé junto al buró.',
}
COOKIE = 'uf_player'
INITIAL_FLAGS = {
    'mesa_intacta': True, 'bicicleta_arreglada': False, 'pollo_alimentado': False,
    'foto_encontrada': False, 'ayudo_fiesta': False, 'agua': False,
    'puntos_responsabilidad': 0, 'final': ''
}
FINAL_NAMES = {'A':'Por lo menos ayudaste', 'B':'Ya no me pidan favores', 'C':'El favor más caro'}
TEST_CHECKPOINTS = {
    'dormitorio': {'scene': FIRST_SCENE, 'title': 'Dormitorio',
                   'description': 'Desde el despertador, sin decisiones previas.'},
    'cocina': {'scene': 'bryan_s02', 'title': 'Cocina',
               'description': 'Teléfono revisado y tenis puestos. Decide qué hacer con Pollo.'},
    'patio': {'scene': 'bryan_s03', 'title': 'Patio',
              'description': 'Pasos anteriores completados y Pollo alimentado. Busca la mesa.'},
}


def prepare_test_part(owner, checkpoint, get_scene):
    """Prepara un punto de prueba recorriendo las mismas reglas del juego."""
    target = TEST_CHECKPOINTS[checkpoint]['scene']
    part = new_part(owner, get_scene(FIRST_SCENE))
    for _ in range(200):
        if part['scene_id'] == target:
            return part
        scene = get_scene(part['scene_id'])
        choices = available_choices(part, scene)
        desired = {'bryan_s01': 'telefono', 'bryan_s01_mensaje':
                   'cocina' if 'zapato' in part['used_choices'] else 'zapato',
                   'bryan_s02': 'alimentar'}.get(part['scene_id'])
        if any(choice['id'] == desired for choice in choices):
            valid = advance(part, scene, 'choice', desired, get_scene)
        else:
            valid = advance(part, scene, 'next', '', get_scene)
        if not valid:
            break
    abort(409, description='El guion cambió y este punto de prueba necesita actualizarse. Tu partida no se modificó.')

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
    if part['scene_id'] == BEDROOM_SCENE:
        part['history'][-1].update(
            interaction=part.get('bedroom_interaction'),
            shoes_on='zapato' in part['used_choices'],
        )

def record_current(part):
    current = part['lines'][part['line_index']]
    record(part, current['character'], current['text'])

def enter_scene(part, scene):
    part.pop('bedroom_interaction', None)
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

def before_bedroom_exploration(part, scene):
    if scene['_id'] != BEDROOM_SCENE or not ready(part):
        return False
    last = part['history'][-1]
    return last['kind'] == 'dialogue' and last['text'] == BEDROOM_REALIZATION


def available_choices(part, scene):
    if (not ready(part) or part.get('pending_next') or part.get('bedroom_interaction')
            or before_bedroom_exploration(part, scene)):
        return []
    choices = [x for x in scene.get('choices', []) if matches(x.get('when'),part['flags'])
               and not (x.get('once') and x['id'] in part['used_choices'])]
    if scene['_id'] != BEDROOM_SCENE:
        return choices
    door_label = 'Salir a la cocina' if 'zapato' in part['used_choices'] else 'Ir a la cocina'
    labels = {'zapato': 'Ponerse los tenis', 'cocina': door_label}
    return [dict(choice, text=labels[choice['id']]) if choice['id'] in labels else choice
            for choice in choices]

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
        if before_bedroom_exploration(part, scene):
            record(part, 'BRYAN', BEDROOM_EXPLORE, 'exploration')
            return True
        if scene['_id'] == BEDROOM_SCENE and not part.get('pending_next'):
            interaction = part.pop('bedroom_interaction', None)
            if interaction:
                record(part, 'BRYAN', BEDROOM_EXPLORATION_LINES[interaction], 'exploration')
                return True
        destination = part.get('pending_next') or scene.get('next')
        if destination:
            enter_scene(part,get_scene(destination)); return True
        return False
    if not ready(part) or part.get('pending_next') or part.get('complete'): return False
    if action == 'choice':
        selected = next((x for x in available_choices(part,scene) if x['id'] == value),None)
        if not selected: return False
        if scene['_id'] == BEDROOM_SCENE and value == 'cocina' and 'zapato' not in part['used_choices']:
            part['bedroom_interaction'] = value
            return respond(part, [{'character':'BRYAN', 'text':'Un momento. Todavía estoy en calcetas.'}])
        if selected.get('once'): part['used_choices'].append(selected['id'])
        part['decisions'].append({'scene_id':scene['_id'],'id':selected['id'],'text':selected['text']})
        record(part,'ELECCIÓN',selected['text'],'choice')
        effects(part,selected.get('effects'))
        destination = selected.get('next')
        response = selected.get('response', [])
        if scene['_id'] == BEDROOM_SCENE:
            if value in ('zapato', 'mochila', 'ventilador'):
                part['bedroom_interaction'] = value
                if value == 'zapato':
                    response = [{'character':'BRYAN', 'text':'Ahí está el otro. Con razón solo veía uno.'}]
            elif value == 'cocina' and destination:
                part['bedroom_interaction'] = 'salir'
                response = [{'character':'BRYAN', 'text':'Si me apuro, todavía llego.'}]
        if not respond(part, response, destination):
            part.pop('bedroom_interaction', None)
            if destination:
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

def create_game_blueprint(database, points_store=None):
    bp = Blueprint('bryan', __name__)
    scenes = database['escenas']; saves = database['partidas']
    test_saves = database['partidas_prueba']
    seeded = False

    def seed():
        nonlocal seeded
        if seeded: return
        path = Path(__file__).parent / 'data' / 'caso_bryan.json'
        for doc in json.loads(path.read_text(encoding='utf-8')):
            # Respeta las escenas editadas en MongoDB y conserva los documentos antiguos.
            scenes.update_one({'_id':doc['_id']},{'$setOnInsert':doc},upsert=True)
        saves.create_index([('owner_hash',1),('case_id',1),('story_version',1),('created_at',-1)])
        test_saves.create_index('expires_at', expireAfterSeconds=0)
        seeded = True

    def get_scene(id):
        scene = scenes.find_one({'_id':id,'case_id':'bryan','schema_version':2})
        if not scene: abort(404,description='No se encontró la escena del guion.')
        return scene

    def require_admin():
        if not g.get('account') or g.account.get('role') != 'admin' or not g.get('access_session'):
            abort(403, description='El modo de prueba requiere una cuenta de administrador.')

    def load(testing=False):
        if testing:
            require_admin()
        seed()
        if testing:
            return test_saves.find_one({'_id': g.access_session['_id']}), None
        token = request.cookies.get(COOKIE,'')
        if not re_token(token): token = secrets.token_urlsafe(32)
        access = g.get('access_session')
        owner = access['owner'] if access else sha256(token.encode()).hexdigest()
        part = saves.find_one({'owner_hash':owner,'case_id':'bryan','story_version':STORY_VERSION},sort=[('created_at',-1),('_id',-1)])
        if part is None:
            part = new_part(owner,get_scene(FIRST_SCENE))
            if access and access['guest']:
                part['expires_at'] = access['expires_at']
            part['_id'] = saves.insert_one(part).inserted_id
        return part, token

    def response_with_cookie(response, token):
        if not g.get('access_session'):
            response.set_cookie(COOKIE,token,max_age=60*60*24*30,httponly=True,
                                secure=bool(os.environ.get('RENDER')) or request.is_secure,samesite='Lax')
        response.headers['Cache-Control'] = 'no-store'
        return response

    @bp.route('/admin/pruebas/bryan', methods=['GET', 'POST'])
    def test_menu():
        require_admin()
        seed()
        if request.method == 'POST':
            if not secrets.compare_digest(request.form.get('csrf', ''), g.access_session['csrf']):
                abort(400, description='El formulario venció. Recarga la página.')
            checkpoint = request.form.get('checkpoint', '')
            if checkpoint not in TEST_CHECKPOINTS:
                abort(400, description='Selecciona un punto de prueba válido.')
            part = prepare_test_part(g.access_session['owner'], checkpoint, get_scene)
            part.update(_id=g.access_session['_id'], expires_at=g.access_session['expires_at'])
            # Un único espacio de pruebas por sesión; nunca entra en partidas ni saldos.
            test_saves.replace_one({'_id': part['_id']}, part, upsert=True)
            return redirect(url_for('bryan.test_play'), code=303)
        return response_with_cookie(make_response(render_template('pruebas_bryan.html',
            checkpoints=TEST_CHECKPOINTS, has_test=bool(test_saves.find_one({'_id': g.access_session['_id']})))), None)

    @bp.route('/admin/pruebas/bryan/jugar', methods=['GET', 'POST'])
    def test_play():
        return play(testing=True)

    def play(testing=False):
        part, token = load(testing)
        if part is None:
            return redirect(url_for('bryan.test_menu'))
        play_endpoint = 'bryan.test_play' if testing else 'juego_bryan'
        history_endpoint = 'bryan.test_history' if testing else 'bryan.history'
        storage = test_saves if testing else saves
        if request.method == 'POST':
            supplied = request.form.get('csrf','')
            if not secrets.compare_digest(supplied,part['csrf']): abort(400,description='Esta partida cambió. Recarga la página para continuar.')
            try: revision = int(request.form.get('revision','-1'))
            except ValueError: abort(400,description='El avance recibido no es válido.')
            if revision != part['revision']:
                return response_with_cookie(redirect(url_for(play_endpoint),code=303),token)
            action = request.form.get('action','')
            if action == 'restart':
                fresh = new_part(part['owner_hash'],get_scene(FIRST_SCENE))
                if 'expires_at' in part:
                    fresh['expires_at'] = part['expires_at']
                if testing:
                    fresh['_id'] = part['_id']
                    storage.replace_one({'_id': part['_id'], 'csrf': part['csrf'], 'revision': revision}, fresh)
                else:
                    fresh['_id'] = saves.insert_one(fresh).inserted_id
            else:
                scene = get_scene(part['scene_id'])
                if not advance(part,scene,action,request.form.get('value',''),get_scene):
                    abort(400,description='Esa acción no está disponible en este momento.')
                part['revision'] += 1; part['updated_at'] = datetime.now(timezone.utc)
                storage.replace_one({'_id':part['_id'],'csrf':part['csrf'],'revision':revision},part)
            return response_with_cookie(redirect(url_for(play_endpoint),code=303),token)
        wallet = points_store.sync(part['owner_hash']) if points_store and not testing else None
        scene = get_scene(part['scene_id'])
        last = len(part['history'])-1
        cursor = request.args.get('h',type=int)
        if cursor is None: cursor = last
        cursor = max(0,min(cursor,last)); reading = cursor != last
        entry = part['history'][cursor]
        if (not reading and scene['_id'] == BEDROOM_SCENE and ready(part)
                and 'shoes_on' not in entry and part.get('used_choices')):
            # Las partidas antiguas guardaban la última frase en lugar del regreso a explorar.
            shoes_on = 'zapato' in part['used_choices']
            text = 'Listo. Ya puedo bajar.' if shoes_on else 'Me faltan los tenis.'
            entry = dict(entry, kind='exploration', character='BRYAN', text=text, shoes_on=shoes_on)
        puzzle = scene.get('puzzle') if ready(part) and not part.get('pending_next') and not part['complete'] else None
        options = [x for x in (puzzle or {}).get('options',[]) if x['id'] not in part['puzzle_progress']]
        can_next = (not ready(part) or before_bedroom_exploration(part, scene)
                    or bool(part.get('pending_next') or part.get('bedroom_interaction') or scene.get('next')))
        choices = available_choices(part, scene)
        visual = presentation(entry, choices, options,
                              not reading and not can_next and bool(puzzle or choices), part)
        response = make_response(render_template('juego.html',part=part,scene=scene,entry=entry,
            reading=reading,cursor=cursor,last=last,choices=choices,puzzle=puzzle,
            puzzle_options=options,can_next=can_next,final_names=FINAL_NAMES,wallet=wallet,visual=visual,
            testing=testing, play_endpoint=play_endpoint, history_endpoint=history_endpoint))
        return response_with_cookie(response,token)

    @bp.route('/caso/bryan/historial')
    def history():
        return show_history()

    @bp.get('/admin/pruebas/bryan/historial')
    def test_history():
        return show_history(testing=True)

    def show_history(testing=False):
        part, token = load(testing)
        if part is None:
            return redirect(url_for('bryan.test_menu'))
        response = make_response(render_template('juego_historial.html',part=part,final_names=FINAL_NAMES,
            testing=testing, play_endpoint='bryan.test_play' if testing else 'juego_bryan'))
        return response_with_cookie(response,token)

    return bp, play

def re_token(token):
    return 32 <= len(token) <= 100 and all(c.isascii() and (c.isalnum() or c in '_-') for c in token)
