"""Prueba GET, POST, PUT y DELETE con un registro ficticio que se elimina."""
import json,sys,uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
BASE=(sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:5000").rstrip("/")
def llamar(metodo,ruta,datos=None):
    cuerpo=json.dumps(datos).encode() if datos is not None else None
    peticion=Request(BASE+ruta,data=cuerpo,method=metodo,headers={"Content-Type":"application/json"})
    try:
        with urlopen(peticion,timeout=30) as respuesta:
            return respuesta.status,json.load(respuesta)
    except HTTPError as error:
        return error.code,json.loads(error.read().decode())
def mostrar(metodo,ruta,status,datos):
    print(f"{metodo} {ruta} -> HTTP {status}")
    print(json.dumps(datos,ensure_ascii=False,indent=2))
identificador=None
try:
    estado,lista=llamar("GET","/api/casos");assert estado==200 and isinstance(lista,list)
    print(f"GET /api/casos -> HTTP {estado}, {len(lista)} registros")
    datos={"nombre":"DEMO API "+uuid.uuid4().hex[:8],"categoria":"Misterio","estado":"Disponible"}
    estado,nuevo=llamar("POST","/api/casos",datos);assert estado==201
    identificador=nuevo["_id"];ruta="/api/casos/"+identificador;mostrar("POST","/api/casos",estado,nuevo)
    estado,leido=llamar("GET",ruta);assert estado==200 and leido["nombre"]==datos["nombre"];mostrar("GET",ruta,estado,leido)
    datos.update(estado="Bloqueado",categoria="Investigacion")
    estado,editado=llamar("PUT",ruta,datos);assert estado==200 and editado["estado"]=="Bloqueado";mostrar("PUT",ruta,estado,editado)
    estado,error=llamar("POST","/api/casos",{"nombre":"","categoria":"Misterio","estado":"Disponible"});assert estado==400 and "error" in error;mostrar("POST","/api/casos (datos incorrectos)",estado,error)
    estado,error=llamar("GET","/api/casos/id-invalido");assert estado==404 and "error" in error;mostrar("GET","/api/casos/id-invalido",estado,error)
    estado,borrado=llamar("DELETE",ruta);assert estado==200;mostrar("DELETE",ruta,estado,borrado);identificador=None
    print("PRUEBA COMPLETA: cuatro metodos y errores controlados correctos.")
finally:
    if identificador:
        try:llamar("DELETE","/api/casos/"+identificador)
        except Exception:print("Revisar el registro DEMO creado durante esta prueba.",file=sys.stderr)
