"""Saldo y carrito de demostración; MongoDB valida cada movimiento."""
from datetime import datetime, timezone
from hashlib import sha256
import secrets
import os
from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for
from bryan_game import COOKIE, re_token

PACKAGES = {
    'archivo': {'name': 'Sobre de puntos', 'points': 50},
    'investigador': {'name': 'Kit del investigador', 'points': 150},
    'expediente': {'name': 'Reserva del archivo', 'points': 300},
}


class PointsStore:
    def __init__(self, database):
        self.wallets = database['saldos']
        self.saves = database['partidas']

    def get(self, owner):
        self.wallets.update_one({'_id': owner}, {'$setOnInsert': {
            'balance': 0, 'cart': {}, 'revision': 0,
            'csrf': secrets.token_urlsafe(32), 'events': [], 'transactions': [],
            'created_at': datetime.now(timezone.utc),
        }}, upsert=True)
        return self.wallets.find_one({'_id': owner})

    def award(self, owner, key, amount, label):
        # El saldo y el identificador del premio cambian juntos: recargar o
        # reiniciar la historia no permite cobrar dos veces la misma decisión.
        for _ in range(12):
            wallet = self.get(owner)
            if key in wallet['events']:
                return
            delta = max(0, wallet['balance'] + amount) - wallet['balance']
            result = self.wallets.update_one(
                {'_id': owner, 'balance': wallet['balance'], 'events': {'$ne': key}},
                {'$inc': {'balance': delta}, '$push': {
                    'events': key, 'transactions': {
                        'label': label, 'amount': delta,
                        'at': datetime.now(timezone.utc),
                    }}})
            if result.modified_count:
                return
        abort(409, description='El saldo cambió. Recarga para sincronizarlo.')

    def sync(self, owner):
        # Reconcilia decisiones ya guardadas, incluso partidas anteriores.
        # Las reglas se mantienen en el servidor y no dependen del formulario.
        rules = {
            ('bryan_s03_pata', 'revisar'): 10,
            ('bryan_s05', 'recoger'): 10,
            ('bryan_s09_luces', 'ayudar'): 10,
        }
        for part in self.saves.find({'owner_hash': owner, 'case_id': 'bryan'}):
            for decision in part.get('decisions', []):
                pair = (decision['scene_id'], decision['id'])
                if pair in rules:
                    self.award(owner, 'bryan:' + ':'.join(pair), rules[pair],
                               'Bryan · ' + decision.get('text', decision['id']))
        return self.get(owner)


def create_points_blueprint(database):
    bp = Blueprint('puntos', __name__)
    store = PointsStore(database)

    def identity():
        token = request.cookies.get(COOKIE, '')
        if not re_token(token):
            token = secrets.token_urlsafe(32)
        return sha256(token.encode()).hexdigest(), token

    def respond(response, token):
        response.set_cookie(COOKIE, token, max_age=60*60*24*30, httponly=True,
                            secure=request.is_secure or bool(os.environ.get('RENDER')),
                            samesite='Lax')
        response.headers['Cache-Control'] = 'no-store'
        return response

    def home():
        owner, token = identity()
        wallet = store.sync(owner)
        return respond(make_response(render_template('inicio.html', wallet=wallet,
                       cart_count=sum(wallet['cart'].values()))), token)

    @bp.route('/carrito', methods=['GET', 'POST'])
    def cart():
        owner, token = identity()
        wallet = store.sync(owner)
        if request.method == 'POST':
            if not secrets.compare_digest(request.form.get('csrf', ''), wallet['csrf']):
                abort(400, description='Formulario vencido. Recarga el carrito.')
            revision = request.form.get('revision', type=int)
            if revision != wallet['revision']:
                return respond(redirect(url_for('puntos.cart', notice='stale'), code=303), token)
            action = request.form.get('action')
            cart = dict(wallet['cart'])
            update = {'$inc': {'revision': 1}}
            notice = ''
            if action in ('add', 'remove'):
                package = request.form.get('package')
                if package not in PACKAGES:
                    abort(400, description='Paquete inválido.')
                if action == 'add':
                    if sum(cart.values()) >= 10:
                        abort(400, description='El carrito admite hasta 10 paquetes.')
                    cart[package] = cart.get(package, 0) + 1
                else:
                    cart.pop(package, None)
                update['$set'] = {'cart': cart}
            elif action == 'clear':
                update['$set'] = {'cart': {}}
            elif action == 'checkout':
                if not cart:
                    abort(400, description='Agrega un paquete antes de confirmar.')
                total = sum(PACKAGES[key]['points'] * quantity for key, quantity in cart.items())
                update['$inc']['balance'] = total
                update['$set'] = {'cart': {}}
                update['$push'] = {'transactions': {
                    'label': 'Compra simulada · ' + str(sum(cart.values())) + ' paquete(s)',
                    'amount': total, 'at': datetime.now(timezone.utc),
                }}
                notice = 'purchased'
            else:
                abort(400, description='Acción inválida.')
            result = store.wallets.update_one({'_id': owner, 'revision': revision}, update)
            if not result.modified_count:
                notice = 'stale'
            return respond(redirect(url_for('puntos.cart', notice=notice), code=303), token)
        rows = [dict(PACKAGES[key], id=key, quantity=quantity,
                     total=PACKAGES[key]['points'] * quantity)
                for key, quantity in wallet['cart'].items()]
        return respond(make_response(render_template('carrito.html', wallet=wallet,
            packages=PACKAGES, rows=rows, total=sum(row['total'] for row in rows),
            movements=list(reversed(wallet['transactions'][-20:])),
            notice=request.args.get('notice'))), token)

    return bp, home, store
