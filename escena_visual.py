"""Presentación de escenas: coordenadas sobre la ilustración, sin reglas de juego.

Las áreas clicables solo se activan si el motor ofrece la acción correspondiente.
Los fondos y las zonas comparten plano para conservar su posición al redimensionar.
"""
SALON = 'img/escenas/BG05_salon_pinceladas.png'
ALMACEN = 'img/escenas/BG06_almacen_pinceladas.png'
PHOTO = 'img/escenas/foto_salon_1987.png'

# x, y, ancho, alto en porcentajes del fondo completo.
AREAS = {
    'bryan_s01': {'telefono': (64, 62, 8, 6)},
    'bryan_s01_mensaje': {
        'zapato': (43, 76, 7, 7), 'ventilador': (75, 31, 8, 24),
        'mochila': (70, 55, 9, 23),
    },
    'bryan_s02': {'alimentar': (29, 48, 10, 10)},
    'bryan_s03_orden': {
        'mesa': (29, 52, 29, 7), 'caja': (26, 39, 13, 13),
        'maceta': (47, 31, 10, 21), 'cubeta': (39, 40, 8, 13),
    },
    'bryan_s03_pata': {'revisar': (49, 58, 6, 22), 'salir': (58, 9, 18, 47)},
    'bryan_s04': {'agua': (30, 47, 10, 12)},
    'bryan_s05': {'recoger': (47, 45, 17, 18), 'irse': (73, 48, 21, 14)},
    'bryan_s07': {'almacen': (1, 12, 6, 56)},
    'bryan_s08': {
        'pila_a': (53, 35, 14, 48), 'pila_b': (67, 30, 18, 57),
        'mesa': (76, 55, 22, 12),
    },
    'bryan_s08_explorar': {
        'foto': (11, 34, 11, 12), 'puerta': (29, 14, 15, 51),
        'mesa': (76, 55, 22, 12),
    },
    'bryan_s09_tablero': {
        'a': (11, 18, 6, 5), 'b': (11, 24, 6, 5), 'c': (11, 30, 6, 5),
    },
    'bryan_s09_luces': {'ayudar': (48, 47, 49, 13), 'marcharse': (20, 16, 7, 41)},
    'bryan_s11_mensaje': {'abrir_foto': (44, 25, 23, 26)},
    'bryan_s11_foto': {'ampliar': (44, 25, 23, 26)},
}


def presentation(entry, choices, puzzle_options, active, part):
    scene_id = entry['scene_id']
    background = {
        'img/escenas/BG02_cocina_bryan.png': 'img/escenas/BG02_cocina_pinceladas.png',
        'img/escenas/BG03_patio_bryan.png': 'img/escenas/BG03_patio_pinceladas.png',
        'img/escenas/BG04_calle_tienda_salon.png': 'img/escenas/BG04_calle_pinceladas.png',
    }.get(entry['background'], entry['background'])
    bryan_inicio = scene_id == 'bryan_s01' and entry['character'] == 'BRYAN'
    if bryan_inicio:
        if entry.get('text') == 'Cinco minutos más':
            background = 'img/escenas/BG01_bryan_con_celular.png'
        elif entry.get('text') == '¿No tienen otra persona a quien molestar?':
            background = 'img/escenas/BG01_bryan_sentado.png'
        else:
            background = 'img/escenas/BG01_bryan_al_borde.png'
    elif scene_id == 'bryan_s01' and entry['character'] == 'NARRADOR':
        background = 'img/escenas/BG01_celular_1037.png'
    elif scene_id == 'bryan_s01_mensaje':
        if entry.get('text') == 'La mesa…':
            background = 'img/escenas/BG01_bryan_la_mesa.png'
        elif entry.get('interaction') == 'zapato':
            background = 'img/escenas/BG01_bryan_se_calza.png'
        elif entry.get('interaction') in ('mochila', 'ventilador'):
            suffix = '_calzado' if entry.get('shoes_on') else ''
            background = f"img/escenas/BG01_bryan_{entry['interaction']}{suffix}.png"
        elif entry.get('text') == '¡LA MESA!' or entry.get('interaction') == 'cocina':
            shoes_on = entry.get('shoes_on', active and 'zapato' in part.get('used_choices', ()))
            background = ('img/escenas/BG01_bryan_explora_calzado.png' if shoes_on
                          else 'img/escenas/BG01_bryan_la_mesa.png')
        else:
            background = 'img/escenas/BG01_bryan_lee_mensaje.png'
    elif 'BG05_' in background:
        background = SALON
    elif 'BG06_' in background:
        background = ALMACEN
    portrait = None
    if entry['character'] == 'BRYAN':
        if scene_id.startswith('bryan_s11_'):
            portrait = 'bryan_sorprendido.png'
        elif scene_id in ('bryan_s02', 'bryan_s11'):
            portrait = 'bryan_cocina.png'
    hotspots = []
    if active and not part.get('needs_cleanup'):
        for action, options in [('choice', choices), ('puzzle', puzzle_options)]:
            for option in options:
                area = AREAS.get(scene_id, {}).get(option['id'])
                if area:
                    hotspots.append(dict(action=action, value=option['id'], label=option['text'],
                                         x=area[0], y=area[1], w=area[2], h=area[3]))
    photo_on_shelf = scene_id in ('bryan_s08', 'bryan_s08_explorar')
    photo_large = scene_id in ('bryan_s11_mensaje', 'bryan_s11_foto', 'bryan_s11_detalle')
    return dict(background=background, portrait=portrait, hotspots=hotspots, photo=PHOTO,
                photo_on_shelf=photo_on_shelf, photo_large=photo_large,
                can_inspect=bool((entry.get('evidence') or
                                 (photo_on_shelf and part['flags'].get('foto_encontrada')))
                                 and not any(h['value'] in ('ampliar', 'abrir_foto', 'foto') for h in hotspots)),
                detail=entry.get('evidence') == 'gafete')
