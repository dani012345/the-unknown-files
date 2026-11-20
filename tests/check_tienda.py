from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import patch
from soporte_tienda import project,db,register,post,form

app,shop=project.app,project.shop_store
anonymous=app.test_client()
assert anonymous.get('/tienda').status_code==200
assert db.productos_tienda.count_documents({})==4
a,oa=register('ShopAlice');b,ob=register('ShopBob');admin,od=register('ShopAdmin',admin=True)
poor,op=register('ShopPoor',credit=0)
marker='CONTENIDO_PRIVADO_SPOILER_NO_PUBLICO'
db.productos_tienda.update_one({'_id':'fecha-reverso'},{'$set':{'contenido':marker}})
for path in ['/tienda','/tienda/articulo/fecha-reverso']:
    r=a.get(path);assert r.status_code==200;assert marker not in r.get_data(as_text=True)
assert a.get('/tienda/archivo/fecha-reverso').status_code==403
assert anonymous.post('/tienda/articulo/fecha-reverso/comprar').status_code==403
assert post(poor,'/tienda/articulo/fecha-reverso/comprar',precio=10,confirm_spoiler='yes').status_code==409
assert db.saldos.find_one({'_id':op})['balance']==0
assert post(a,'/tienda/articulo/fecha-reverso/comprar',precio=10).status_code==400
assert post(a,'/tienda/articulo/fecha-reverso/comprar',precio=10,confirm_spoiler='yes').status_code==303
assert db.saldos.find_one({'_id':oa})['balance']==290
assert marker in a.get('/tienda/archivo/fecha-reverso').get_data(as_text=True)
assert b.get('/tienda/archivo/fecha-reverso').status_code==403
assert post(a,'/tienda/articulo/fecha-reverso/comprar',precio=10,confirm_spoiler='yes').status_code==303
assert db.saldos.find_one({'_id':oa})['balance']==290

# Un fallo entre el débito y el pedido revierte la transacción completa.
before=db.saldos.find_one({'_id':oa})
with patch.object(shop.orders,'insert_one',side_effect=RuntimeError('fallo simulado')):
    try:post(a,'/tienda/articulo/hombre-gafete/comprar',precio=20,confirm_spoiler='yes')
    except RuntimeError:pass
    else:raise AssertionError('No se simuló el fallo')
assert db.saldos.find_one({'_id':oa})==before
assert not shop.owned(oa,0,'hombre-gafete')

# Dos usuarios compiten realmente por la única unidad del expediente.
barrier=Barrier(2)
def race(c):
    barrier.wait();return post(c,'/tienda/articulo/expediente-bryan/reservar',precio=60)
with ThreadPoolExecutor(max_workers=2) as pool:
    responses=list(pool.map(race,[a,b]))
assert sorted(r.status_code for r in responses)==[303,409],[r.status_code for r in responses]
hold=db.reservas_tienda.find_one({'estado':'temporal'})
winner,loser=(a,b) if hold['owner']==oa else (b,a)
folio=hold['folio'];path='/tienda/comprobante/'+folio
assert db.unidades_tienda.count_documents({'producto':'expediente-bryan','estado':'reservada'})==1
assert post(winner,'/tienda/articulo/expediente-bryan/reservar',precio=60).status_code==303
assert db.reservas_tienda.find_one({'folio':folio})['expira_en']==hold['expira_en']
assert post(loser,path+'/cancelar').status_code==403
assert anonymous.get(path).status_code==200
assert hold['owner'] not in anonymous.get(path).get_data(as_text=True)
assert marker not in anonymous.get(path).get_data(as_text=True)
assert anonymous.get(path+'/qr.svg').status_code==200
assert b'<svg' in anonymous.get(path+'/qr.svg').data
assert post(winner,path+'/cancelar').status_code==303
assert db.reservas_tienda.find_one({'folio':folio})['estado']=='cancelada'
assert db.unidades_tienda.find_one({'producto':'expediente-bryan'})['estado']=='libre'

# Vencer libera Atlas, aunque el navegador anterior haya cerrado la página.
r=post(winner,'/tienda/articulo/expediente-bryan/reservar',precio=60)
folio=r.location.rsplit('/',1)[-1];path='/tienda/comprobante/'+folio
db.reservas_tienda.update_one({'folio':folio},{'$set':{'expira_en':datetime.now(timezone.utc)-timedelta(seconds=1)}})
assert anonymous.get(path+'/estado').json['estado']=='vencida'
assert post(winner,path+'/confirmar',confirm_compra='yes').status_code==409
assert db.unidades_tienda.find_one({'producto':'expediente-bryan'})['estado']=='libre'

# Confirmar dos veces cobra una vez. El precio reservado se conserva.
r=post(winner,'/tienda/articulo/expediente-bryan/reservar',precio=60)
folio=r.location.rsplit('/',1)[-1];path='/tienda/comprobante/'+folio
hold=db.reservas_tienda.find_one({'folio':folio})
balance=db.saldos.find_one({'_id':hold['owner']})['balance']
db.productos_tienda.update_one({'_id':'expediente-bryan'},{'$set':{'precio':90}})
assert post(winner,path+'/confirmar').status_code==400
assert post(winner,path+'/confirmar',confirm_compra='yes').status_code==303
assert post(winner,path+'/confirmar',confirm_compra='yes').status_code==303
assert db.saldos.find_one({'_id':hold['owner']})['balance']==balance-60
assert db.unidades_tienda.find_one({'producto':'expediente-bryan'})['estado']=='confirmada'
assert db.compras_tienda.count_documents({'reserva':hold['_id']})==1
assert anonymous.get(path+'/estado').json['estado']=='confirmada'
assert winner.get('/tienda/coleccion').status_code==200

# Administración privada, borradores, precios y reposición sin destruir compras.
assert a.get('/tienda/admin/fecha-reverso').status_code==403
assert admin.get('/tienda/admin/fecha-reverso').status_code==200
r=post(admin,'/tienda/admin/nuevo',tipo='archivo',nombre='Nota futura',descripcion='Un borrador privado',precio=12,nivel='En preparación',imagen='img/tienda/sobre-pinceladas-v1.png',contenido='Secreto de prueba')
assert r.status_code==303
new=db.productos_tienda.find_one({'nombre':'Nota futura'})
assert not new['publicado']
assert 'Nota futura' not in anonymous.get('/tienda').get_data(as_text=True)
assert 'Nota futura' in admin.get('/tienda').get_data(as_text=True)
assert post(admin,'/tienda/admin/expediente-bryan',nombre='El expediente de Bryan',descripcion='Edición repuesta',precio=90,nivel='Edición limitada',imagen='img/tienda/expediente-pinceladas-v1.png',unidades=1,publicado='on').status_code==303
assert db.unidades_tienda.count_documents({'producto':'expediente-bryan','estado':'libre'})==1
assert db.unidades_tienda.count_documents({'producto':'expediente-bryan','estado':'confirmada'})==1

# Reinicios: primero conserva acceso; segundo revoca compras y cancela reservas antiguas.
assert a.get('/caso/bryan').status_code==200
for restart in (1,2):
    fields=form(a,'/caso/bryan')
    assert a.post('/caso/bryan',data={**fields,'action':'next'}).status_code==303
    fields=form(a,'/caso/bryan')
    assert a.post('/caso/bryan',data={**fields,'action':'restart','confirm_restart':'yes'}).status_code==303
    assert a.get('/tienda/archivo/fecha-reverso').status_code==(200 if restart==1 else 403)
assert marker not in a.get('/tienda/coleccion').get_data(as_text=True)
assert a.get('/tienda/articulo/no-existe').status_code==404
assert a.get('/tienda/comprobante/no-existe').status_code==404
assert a.post('/tienda/articulo/fecha-reverso/comprar',data={'csrf':'fake','epoch':1}).status_code==400
print('OK REAL MONGODB: compra y rollback, privacidad, dos usuarios/última unidad, cancelar, vencer, confirmar sin doble cobro, QR, editor y reinicios.')
