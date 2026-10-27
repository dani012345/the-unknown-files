
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:5000")


def probar(metodo, ruta, datos=None):
    cuerpo = None if datos is None else json.dumps(datos).encode("utf-8")

    solicitud = Request(
        BASE_URL + ruta,
        data=cuerpo,
        method=metodo,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urlopen(solicitud, timeout=15) as respuesta:
            codigo = respuesta.status
            contenido = respuesta.read().decode("utf-8")
    except HTTPError as error:
        codigo = error.code
        contenido = error.read().decode("utf-8")
    except URLError as error:
        print(f"\nERROR DE CONEXIÓN: {error.reason}")
        raise SystemExit(1)

    print(f"\n--- {metodo} {ruta} | HTTP {codigo} ---")
    try:
        print(json.dumps(json.loads(contenido), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(contenido)

    return codigo, json.loads(contenido)


try:
    print("PROBANDO API DE THE UNKNOWN FILES")
    print("Servidor:", BASE_URL)

    # GET: consultar los casos
    codigo, respuesta = probar("GET", "/api/casos")
    assert codigo == 200, "Falló GET"

    # POST: crear un caso de prueba
    datos = {
        "nombre": "PRUEBA API " + datetime.now().strftime("%H%M%S"),
        "categoria": "Prueba",
        "estado": "Disponible"
    }

    codigo, respuesta = probar("POST", "/api/casos", datos)
    assert codigo == 201, "Falló POST"
    id_caso = respuesta["id"]

    # GET: consultar el caso creado
    codigo, respuesta = probar("GET", f"/api/casos/{id_caso}")
    assert codigo == 200, "Falló GET individual"

    # PUT: modificar el caso
    datos["nombre"] += " EDITADO"
    datos["estado"] = "Completado"

    codigo, respuesta = probar("PUT", f"/api/casos/{id_caso}", datos)
    assert codigo == 200, "Falló PUT"

    # Error controlado: ID inválido
    codigo, respuesta = probar("GET", "/api/casos/id-invalido")
    assert codigo == 404, "No se controló el ID inválido"

    # Error controlado: estado no permitido
    datos_invalidos = {
        "nombre": "Prueba inválida",
        "categoria": "Prueba",
        "estado": "Desconocido"
    }

    codigo, respuesta = probar("POST", "/api/casos", datos_invalidos)
    assert codigo == 400, "No se controló el estado inválido"

    # DELETE: borrar únicamente el caso creado por esta prueba
    codigo, respuesta = probar("DELETE", f"/api/casos/{id_caso}")
    assert codigo == 200, "Falló DELETE"

    print("\n¡TODAS LAS PRUEBAS TERMINARON CORRECTAMENTE!")

except (AssertionError, KeyError, ValueError) as error:
    print(f"\nPRUEBA FALLIDA: {error}")
