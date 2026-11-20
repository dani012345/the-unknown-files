"""Archivos desbloqueables y merch de demostración con inventario por unidad.

Cada cambio que afecta inventario, reservas o saldo utiliza una transacción.
Los archivos privados nunca se incluyen en las respuestas del catálogo público.
"""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
import secrets

from bson import ObjectId
from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, send_file, url_for
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from werkzeug.exceptions import HTTPException

HOLD_SECONDS = 300
ART = {
    'sobre': 'img/tienda/sobre-pinceladas-v1.png',
    'pin': 'img/tienda/pin-real-fondo-pintado-v1.png',
    'expediente': 'img/tienda/expediente-real-fondo-pintado-v1.png',
    'llavero': 'img/tienda/llavero-real-fondo-pintado-v1.png',
    'libreta': 'img/tienda/libreta-real-fondo-pintado-v1.png',
    'taza': 'img/tienda/taza-real-fondo-pintado-v1.png',
    'bolsa': 'img/tienda/bolsa-real-fondo-pintado-v1.png',
    'credencial': 'img/tienda/credencial-real-fondo-pintado-v1.png',
    'separadores': 'img/tienda/separadores-real-fondo-pintado-v1.png',
    'pin anterior': 'img/tienda/pin-pollo-pinceladas-v1.png',
    'expediente anterior': 'img/tienda/expediente-pinceladas-v1.png',
}
INITIAL_PRODUCTS = [
    {'_id': 'fecha-reverso', 'nombre': 'La fecha del reverso', 'tipo': 'archivo', 'precio': 10,
     'descripcion': 'Una nota de observación sobre una fotografía del caso de Bryan.',
     'nivel': 'Spoiler del caso 001 · medio', 'imagen': ART['sobre'], 'publicado': True,
     'contenido': 'Al reverso de la fotografía del almacén se lee «1987». Más tarde, Mamá envía otra fotografía de una celebración en ese mismo salón, también de 1987.\n\nSon dos registros del mismo evento. La fecha conecta ambos hallazgos; el caso deja abierta la pregunta sobre lo que ocurrió allí.'},
    {'_id': 'hombre-gafete', 'nombre': 'El hombre del fondo', 'tipo': 'archivo', 'precio': 20,
     'descripcion': 'Una comparación reservada para quienes quieran adelantarse al cierre del caso.',
     'nivel': 'Spoiler del caso 001 · alto', 'imagen': ART['sobre'], 'publicado': True,
     'contenido': 'El hombre del fondo lleva un gafete con el nombre «RAMIRO». Si Bryan encontró la fotografía del almacén, al final puede comparar las dos imágenes: el hombre aparece en ambas.\n\nEl expediente todavía no explica por qué. Esta observación conserva la anomalía como una pregunta abierta; no demuestra por sí sola el significado de ningún símbolo.'},
    {'_id': 'pin-pollo', 'nombre': 'Pollo, jefe de la casa', 'tipo': 'merch', 'precio': 30,
     'descripcion': 'Pin ilustrado en tonos crema y bronce, con una pequeña llave de archivo. Edición de colección.',
     'nivel': 'Edición limitada · 3 unidades iniciales', 'imagen': ART['pin'], 'publicado': True, 'unidades': 3},
    {'_id': 'expediente-bryan', 'nombre': 'El expediente de Bryan', 'tipo': 'merch', 'precio': 60,
     'descripcion': 'Concepto de réplica del expediente: carpeta, fotografías y pequeños objetos de investigación.',
     'nivel': 'Edición limitada · 1 unidad inicial', 'imagen': ART['expediente'], 'publicado': True, 'unidades': 1},
    {'_id': 'llavero-archivo', 'nombre': 'La llave del archivo', 'tipo': 'merch', 'precio': 25,
     'descripcion': 'Llavero de bronce envejecido con una pequeña llave y placa U.F. Para llevar un fragmento del archivo contigo.',
     'nivel': 'Edición limitada · 5 unidades iniciales', 'imagen': ART['llavero'], 'publicado': True, 'unidades': 5},
    {'_id': 'libreta-investigador', 'nombre': 'Notas del investigador', 'tipo': 'merch', 'precio': 45,
     'descripcion': 'Libreta de tela gris carbón, hojas color crema y detalles de bronce. Incluye una pluma para registrar tus teorías.',
     'nivel': 'Edición limitada · 4 unidades iniciales', 'imagen': ART['libreta'], 'publicado': True, 'unidades': 4},
    {'_id': 'taza-turno-nocturno', 'nombre': 'Turno nocturno', 'tipo': 'merch', 'precio': 40,
     'descripcion': 'Taza de cerámica gris carbón con interior crema y sello U.F. Una compañera para las noches entre expedientes.',
     'nivel': 'Edición limitada · 4 unidades iniciales', 'imagen': ART['taza'], 'publicado': True, 'unidades': 4},
    {'_id': 'bolsa-expedientes', 'nombre': 'Bolsa del archivo central', 'tipo': 'merch', 'precio': 55,
     'descripcion': 'Bolsa de lona beige con asas oscuras y la marca del archivo. Espacio para tus carpetas, cuadernos y descubrimientos.',
     'nivel': 'Edición limitada · 3 unidades iniciales', 'imagen': ART['bolsa'], 'publicado': True, 'unidades': 3},
    {'_id': 'credencial-archivo', 'nombre': 'Identificación de colección', 'tipo': 'merch', 'precio': 35,
     'descripcion': 'Placa U.F. de metal oscuro con marco de bronce y cinta de tejido beige. Una pieza de colección del archivo central.',
     'nivel': 'Edición limitada · 3 unidades iniciales', 'imagen': ART['credencial'], 'publicado': True, 'unidades': 3},
    {'_id': 'separadores-archivo', 'nombre': 'Entre páginas y pistas', 'tipo': 'merch', 'precio': 20,
     'descripcion': 'Set de tres separadores en papel texturizado y metal, con borlas oscuras. Para marcar el lugar de la siguiente pista.',
     'nivel': 'Edición limitada · 6 unidades iniciales', 'imagen': ART['separadores'], 'publicado': True, 'unidades': 6},
]
PUBLIC_FIELDS = ('_id', 'nombre', 'tipo', 'precio', 'descripcion', 'nivel', 'imagen', 'publicado')


def now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()


class ShopStore:
    def __init__(self, database, points):
        self.db, self.points = database, points
        self.products = database['productos_tienda']
        self.units = database['unidades_tienda']
        self.holds = database['reservas_tienda']
        self.orders = database['compras_tienda']
        self.prepared = False

    def prepare(self):
        if self.prepared:
            return
        self.holds.create_index('folio', unique=True)
        self.holds.create_index('owner', unique=True, partialFilterExpression={'estado': 'temporal'})
        self.holds.create_index([('estado', 1), ('expira_en', 1)])
        self.orders.create_index([('owner', 1), ('epoch', 1), ('producto', 1)], unique=True)
        self.units.create_index([('producto', 1), ('estado', 1)])
        for product in INITIAL_PRODUCTS:
            initial = dict(product)
            if product['_id'] in ('pin-pollo', 'expediente-bryan'):
                initial['arte_catalogo_revision'] = 2
            try:
                self.products.update_one({'_id': product['_id']}, {'$setOnInsert': initial}, upsert=True)
            except DuplicateKeyError:
                pass  # Otro worker insertó el mismo catálogo inicial.
            for number in range(product.get('unidades', 0)):
                unit = {'_id': f"{product['_id']}:{number+1:03}", 'producto': product['_id'], 'estado': 'libre'}
                try:
                    self.units.update_one({'_id': unit['_id']}, {'$setOnInsert': unit}, upsert=True)
                except DuplicateKeyError:
                    pass
        # Cambia solo las portadas iniciales antiguas, una vez. Conserva los
        # precios, las ediciones del administrador y todas las unidades vendidas.
        for sku, old_image, new_image in (
            ('pin-pollo', ART['pin anterior'], ART['pin']),
            ('expediente-bryan', ART['expediente anterior'], ART['expediente']),
        ):
            self.products.update_one({'_id': sku, 'imagen': old_image,
                                      'arte_catalogo_revision': {'$exists': False}},
                {'$set': {'imagen': new_image, 'arte_catalogo_revision': 2}})
        self.prepared = True

    def transaction(self, callback):
        # El callback puede repetirse: no envía mensajes ni llama servicios externos.
        try:
            with self.db.client.start_session() as session:
                return session.with_transaction(callback, read_concern=ReadConcern('snapshot'),
                                                write_concern=WriteConcern('majority'))
        except OperationFailure as error:
            if error.code == 20:
                abort(503, description='Las compras necesitan MongoDB Atlas o un MongoDB local configurado como replica set. No se realizó la operación.')
            raise

    def release(self, folio, state='vencida', owner=None, force=False):
        def operation(session):
            query = {'folio': folio, 'estado': 'temporal'}
            if owner is not None:
                query['owner'] = owner
            if state == 'vencida' and not force:
                query['expira_en'] = {'$lte': now()}
            hold = self.holds.find_one_and_update(query,
                {'$set': {'estado': state, 'actualizada_en': now()}}, session=session)
            if hold:
                self.units.update_one({'_id': hold['unidad'], 'reserva': hold['_id'], 'estado': 'reservada'},
                    {'$set': {'estado': 'libre'}, '$unset': {'reserva': ''}}, session=session)
            return bool(hold)
        return self.transaction(operation)

    def expire(self):
        for hold in self.holds.find({'estado': 'temporal', 'expira_en': {'$lte': now()}}, {'folio': 1}):
            self.release(hold['folio'])

    def product(self, sku, private=False):
        product = self.products.find_one({'_id': sku})
        if not product or not product.get('publicado') and not private:
            abort(404, description='Este artículo no está disponible en el archivo.')
        return product if private else {key: product.get(key) for key in PUBLIC_FIELDS}

    def owned(self, owner, epoch, sku):
        return self.orders.find_one({'owner': owner, 'epoch': epoch, 'producto': sku})

    def debit(self, owner, wallet, product, session):
        epoch = wallet.get('economy_epoch', 0)
        result = self.points.wallets.update_one(
            {'_id': owner, 'revision': wallet['revision'], 'balance': {'$gte': product['precio']},
             'economy_epoch': epoch if epoch else {'$in': [0, None]}},
            {'$inc': {'balance': -product['precio'], 'revision': 1}, '$push': {'transactions': {
                'label': 'Tienda · ' + product['nombre'], 'amount': -product['precio'], 'at': now()}}}, session=session)
        if result.modified_count != 1:
            abort(409, description='Tu saldo cambió o no alcanza. Recarga antes de confirmar.')

    def buy_file(self, owner, epoch, sku, quoted_price):
        def operation(session):
            product = self.products.find_one({'_id': sku, 'tipo': 'archivo', 'publicado': True}, session=session)
            if not product or not product.get('contenido', '').strip():
                abort(404, description='Este archivo todavía no está publicado.')
            wallet = self.points.wallets.find_one({'_id': owner}, session=session)
            if wallet.get('economy_epoch', 0) != epoch:
                abort(409, description='Tu partida se reinició. Revisa el saldo antes de comprar.')
            previous = self.orders.find_one({'owner': owner, 'epoch': epoch, 'producto': sku}, session=session)
            if previous:
                return previous['_id']
            if product['precio'] != quoted_price:
                abort(409, description='El precio cambió. Revisa el artículo antes de comprar.')
            self.debit(owner, wallet, product, session)
            order = {'owner': owner, 'epoch': epoch, 'producto': sku, 'nombre': product['nombre'],
                     'tipo': 'archivo', 'precio': product['precio'], 'creada_en': now()}
            return self.orders.insert_one(order, session=session).inserted_id
        return self.transaction(operation)

    def reserve(self, owner, epoch, sku, quoted_price):
        def operation(session):
            product = self.products.find_one({'_id': sku, 'tipo': 'merch', 'publicado': True}, session=session)
            if not product:
                abort(404, description='Esta edición no está disponible.')
            wallet = self.points.wallets.find_one({'_id': owner}, session=session)
            if wallet.get('economy_epoch', 0) != epoch or product['precio'] != quoted_price:
                abort(409, description='La partida o el precio cambiaron. Recarga la tienda.')
            if self.orders.find_one({'owner': owner, 'epoch': epoch, 'producto': sku}, session=session):
                abort(409, description='Ya tienes esta edición en tu colección.')
            existing = self.holds.find_one({'owner': owner, 'estado': 'temporal'}, session=session)
            if existing:
                if existing['producto'] == sku and existing['epoch'] == epoch:
                    return existing['folio']  # Repetir el POST no amplía el plazo.
                abort(409, description='Ya tienes una reserva activa. Confírmala o cancélala primero.')
            if wallet['balance'] < product['precio']:
                abort(409, description='Necesitas más puntos para apartar esta edición. Puedes conseguirlos jugando o desde el carrito de demostración.')
            reservation_id, folio = ObjectId(), secrets.token_urlsafe(24)
            unit = self.units.find_one_and_update({'producto': sku, 'estado': 'libre'},
                {'$set': {'estado': 'reservada', 'reserva': reservation_id}},
                sort=[('_id', 1)], return_document=ReturnDocument.AFTER, session=session)
            if unit is None:
                abort(409, description='Esta edición no tiene unidades libres. Puede haber unidades apartadas por otra persona.')
            start = now()
            self.holds.insert_one({'_id': reservation_id, 'folio': folio, 'owner': owner, 'epoch': epoch,
                'producto': sku, 'nombre': product['nombre'], 'imagen': product['imagen'],
                'precio': product['precio'], 'unidad': unit['_id'], 'estado': 'temporal',
                'creada_en': start, 'expira_en': start + timedelta(seconds=HOLD_SECONDS)}, session=session)
            return folio
        try:
            return self.transaction(operation)
        except DuplicateKeyError:
            abort(409, description='Se creó otra reserva en tu cuenta. Recarga para consultarla.')

    def confirm(self, owner, epoch, folio):
        def operation(session):
            hold = self.holds.find_one({'folio': folio, 'owner': owner}, session=session)
            if not hold:
                abort(404, description='No se encontró una reserva de tu cuenta.')
            if hold['estado'] == 'confirmada':
                return  # Confirmar dos veces nunca cobra dos veces.
            if hold['estado'] != 'temporal' or hold['expira_en'].replace(tzinfo=timezone.utc) <= now():
                abort(409, description='La reserva ya no está vigente. Vuelve al catálogo.')
            wallet = self.points.wallets.find_one({'_id': owner}, session=session)
            if hold['epoch'] != epoch or wallet.get('economy_epoch', 0) != epoch:
                abort(409, description='La partida se reinició. Esta reserva ya no puede confirmarse.')
            self.debit(owner, wallet, hold, session)
            unit = self.units.update_one({'_id': hold['unidad'], 'reserva': hold['_id'], 'estado': 'reservada'},
                {'$set': {'estado': 'confirmada'}}, session=session)
            if unit.modified_count != 1:
                abort(409, description='La unidad cambió. No se realizó la compra.')
            self.holds.update_one({'_id': hold['_id'], 'estado': 'temporal'},
                {'$set': {'estado': 'confirmada', 'actualizada_en': now()}}, session=session)
            self.orders.insert_one({'owner': owner, 'epoch': epoch, 'producto': hold['producto'],
                'nombre': hold['nombre'], 'tipo': 'merch', 'precio': hold['precio'],
                'reserva': hold['_id'], 'folio': folio, 'creada_en': now()}, session=session)
        self.transaction(operation)


def create_shop_blueprint(database, points):
    bp = Blueprint('tienda', __name__)
    shop = ShopStore(database, points)

    @bp.before_request
    def prepare_request():
        shop.prepare()
        shop.expire()
        if g.get('account'):
            g.shop_wallet = points.sync(g.access_session['owner'])
            for hold in shop.holds.find({'owner': g.access_session['owner'], 'estado': 'temporal',
                                       'epoch': {'$ne': g.shop_wallet.get('economy_epoch', 0)}}):
                shop.release(hold['folio'], 'cancelada', owner=g.access_session['owner'], force=True)

    @bp.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    @bp.errorhandler(HTTPException)
    def shop_error(error):
        return render_template('tienda_error.html', message=error.description), error.code

    def account():
        if not g.get('account'):
            abort(403, description='Inicia sesión con una cuenta para comprar o reservar. Los invitados pueden explorar el catálogo.')
        return g.access_session['owner'], g.shop_wallet.get('economy_epoch', 0)

    def form_check():
        owner, epoch = account()
        if not secrets.compare_digest(request.form.get('csrf', ''), g.access_session['csrf']):
            abort(400, description='El formulario venció. Recarga la tienda.')
        if request.form.get('epoch', type=int) != epoch:
            abort(409, description='Tu partida cambió. Revisa la tienda antes de continuar.')
        return owner, epoch

    def receipt(folio):
        hold = shop.holds.find_one({'folio': folio})
        if not hold:
            abort(404, description='No se encontró este comprobante de reserva.')
        return hold

    def public_url(folio):
        base = (os.environ.get('APP_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL') or request.url_root).rstrip('/')
        return base + url_for('tienda.receipt_page', folio=folio)

    @bp.get('/tienda')
    def catalog():
        wallet = g.get('shop_wallet')
        products = []
        query = {} if g.get('account') and g.account.get('role') == 'admin' else {'publicado': True}
        for doc in shop.products.find(query).sort([('tipo', 1), ('precio', 1)]):
            item = {key: doc.get(key) for key in PUBLIC_FIELDS}
            item['disponibles'] = shop.units.count_documents({'producto': doc['_id'], 'estado': 'libre'})
            item['owned'] = bool(wallet and shop.owned(g.access_session['owner'], wallet.get('economy_epoch', 0), doc['_id']))
            products.append(item)
        active = shop.holds.find_one({'owner': g.access_session['owner'], 'estado': 'temporal'}) if wallet else None
        return render_template('tienda.html', products=products, wallet=wallet, active=active)

    @bp.get('/tienda/articulo/<sku>')
    def detail(sku):
        raw = shop.product(sku, private=bool(g.get('account') and g.account.get('role') == 'admin'))
        product = {key: raw.get(key) for key in PUBLIC_FIELDS}
        wallet = g.get('shop_wallet')
        owned = bool(wallet and shop.owned(g.access_session['owner'], wallet.get('economy_epoch', 0), sku))
        return render_template('tienda_articulo.html', product=product, wallet=wallet, owned=owned,
            available=shop.units.count_documents({'producto': sku, 'estado': 'libre'}))

    @bp.post('/tienda/articulo/<sku>/comprar')
    def buy(sku):
        owner, epoch = form_check()
        if request.form.get('confirm_spoiler') != 'yes':
            abort(400, description='Confirma que quieres revelar este spoiler antes de comprar.')
        shop.buy_file(owner, epoch, sku, request.form.get('precio', type=int))
        return redirect(url_for('tienda.read_file', sku=sku), code=303)

    @bp.post('/tienda/articulo/<sku>/reservar')
    def reserve(sku):
        owner, epoch = form_check()
        folio = shop.reserve(owner, epoch, sku, request.form.get('precio', type=int))
        return redirect(url_for('tienda.receipt_page', folio=folio), code=303)

    @bp.get('/tienda/archivo/<sku>')
    def read_file(sku):
        owner, epoch = account()
        product = shop.product(sku, private=True)
        if product['tipo'] != 'archivo':
            abort(404, description='Este artículo no es un archivo de lectura.')
        if not shop.owned(owner, epoch, sku) and g.account.get('role') != 'admin':
            abort(403, description='Este archivo está sellado. Desbloquéalo desde la tienda para leerlo.')
        return render_template('tienda_lectura.html', product=product,
            preview=not shop.owned(owner, epoch, sku))

    @bp.get('/tienda/coleccion')
    def collection():
        owner, epoch = account()
        orders = list(shop.orders.find({'owner': owner, 'epoch': epoch}).sort('creada_en', -1))
        for order in orders:
            product = shop.products.find_one({'_id': order['producto']})
            order['imagen'] = (product or {}).get('imagen', ART['sobre'])
        holds = list(shop.holds.find({'owner': owner}).sort('creada_en', -1).limit(12))
        return render_template('tienda_coleccion.html', orders=orders, holds=holds)

    @bp.get('/tienda/comprobante/<folio>')
    def receipt_page(folio):
        hold = receipt(folio)
        mine = bool(g.get('account') and hold['owner'] == g.access_session['owner'])
        return render_template('tienda_reserva.html', hold=hold, mine=mine, wallet=g.get('shop_wallet'),
            expires=iso(hold['expira_en']), server_time=iso(now()), public_url=public_url(folio))

    @bp.get('/tienda/comprobante/<folio>/estado')
    def status(folio):
        hold = receipt(folio)
        return jsonify(estado=hold['estado'], expira_en=iso(hold['expira_en']), servidor=iso(now()))

    @bp.post('/tienda/comprobante/<folio>/<action>')
    def update_hold(folio, action):
        owner, epoch = form_check()
        hold = receipt(folio)
        if hold['owner'] != owner:
            abort(403, description='Esta reserva pertenece a otra cuenta.')
        if action == 'cancelar':
            shop.release(folio, 'cancelada', owner=owner)
        elif action == 'confirmar':
            if request.form.get('confirm_compra') != 'yes':
                abort(400, description='Confirma la compra simulada antes de gastar tus puntos.')
            shop.confirm(owner, epoch, folio)
        else:
            abort(404, description='Esa acción no existe.')
        return redirect(url_for('tienda.receipt_page', folio=folio), code=303)

    @bp.get('/tienda/comprobante/<folio>/qr.svg')
    def qr(folio):
        receipt(folio)
        import qrcode
        from qrcode.image.svg import SvgPathImage
        code = qrcode.make(public_url(folio), image_factory=SvgPathImage, border=3)
        output = BytesIO()
        code.save(output)
        output.seek(0)
        response = send_file(output, mimetype='image/svg+xml')
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @bp.route('/tienda/admin/<sku>', methods=['GET', 'POST'])
    def edit(sku):
        owner, epoch = account()
        if g.account.get('role') != 'admin':
            abort(403, description='Solo los administradores pueden editar la tienda.')
        creating = sku == 'nuevo'
        product = {'_id': 'nuevo', 'tipo': 'archivo', 'nombre': '', 'descripcion': '', 'precio': 10,
                   'nivel': '', 'imagen': ART['sobre'], 'contenido': '', 'publicado': False} if creating else shop.product(sku, private=True)
        if request.method == 'POST':
            form_check()
            if creating:
                product['tipo'] = request.form.get('tipo', '')
                if product['tipo'] not in ('archivo', 'merch'):
                    abort(400, description='Selecciona un tipo de artículo válido.')
                sku = 'articulo-' + str(ObjectId())
            name = request.form.get('nombre', '').strip()
            description = request.form.get('descripcion', '').strip()
            content = request.form.get('contenido', '').strip()
            price = request.form.get('precio', type=int)
            addition = request.form.get('unidades', 0, type=int)
            image = request.form.get('imagen', '')
            level = request.form.get('nivel', '').strip()
            if not name or len(name) > 90 or not description or len(description) > 1200 or not price or not 1 <= price <= 10000:
                abort(400, description='Revisa el nombre, la descripción y el precio (1 a 10000 puntos).')
            if image not in ART.values() or len(content) > 12000 or len(level) > 100 or addition is None or not 0 <= addition <= 20:
                abort(400, description='Revisa la portada, el texto y las unidades (0 a 20).')
            if product['tipo'] == 'archivo' and 'publicado' in request.form and not content:
                abort(400, description='Un archivo publicado necesita contenido para ofrecerlo a los jugadores.')
            def operation(session):
                if creating:
                    shop.products.insert_one({'_id': sku, 'tipo': product['tipo']}, session=session)
                shop.products.update_one({'_id': sku}, {'$set': {'nombre': name, 'descripcion': description,
                    'precio': price, 'contenido': content, 'imagen': image, 'nivel': level,
                    'publicado': 'publicado' in request.form}}, session=session)
                if product['tipo'] == 'merch':
                    for _ in range(addition):
                        shop.units.insert_one({'_id': f'{sku}:{ObjectId()}', 'producto': sku, 'estado': 'libre'}, session=session)
            shop.transaction(operation)
            return redirect(url_for('tienda.catalog'), code=303)
        return render_template('tienda_editar.html', product=product, art=ART, wallet=g.shop_wallet, creating=creating)

    return bp, shop
