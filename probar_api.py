
import json
import os
import sys
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from datetime import datetime

BASE_URL = (
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get("API_BASE_URL", "http://127.0.0.1:5000")
).rstrip("/")
opener = build_opener(HTTPCookieProcessor(CookieJar()))


class FormularioAcceso(HTMLParser):
    csrf = ""

    def handle_starttag(self, tag, attrs):
        campos = dict(attrs)
        if tag == "input" and campos.get("name") == "csrf":
            self.csrf = campos.get("value", "")


def iniciar_sesion():
    usuario = os.environ.get("API_USERNAME", "")
    contrasena = os.environ.get("API_PASSWORD", "")
    if not usuario or not contrasena:
        raise ValueError("Configura API_USERNAME y API_PASSWORD con tu cuenta de administrador.")
    with opener.open(BASE_URL + "/acceso", timeout=15) as respuesta:
        formulario = FormularioAcceso()
        formulario.feed(respuesta.read().decode("utf-8"))
    datos = urlencode({
        "identifier": usuario, "password": contrasena, "csrf": formulario.csrf,
    }).encode("utf-8")
    solicitud = Request(BASE_URL + "/acceso/entrar", data=datos, method="POST")
    with opener.open(solicitud, timeout=15):
        pass


def probar(metodo, ruta, datos=None):
    cuerpo = None if datos is None else json.dumps(datos).encode("utf-8")

    solicitud = Request(
        BASE_URL + ruta,
        data=cuerpo,
        method=metodo,
        headers={"Content-Type": "application/json"}
    )

    try:
        with opener.open(solicitud, timeout=15) as respuesta:
            codigo = respuesta.status
            contenido = respuesta.read().decode("utf-8")
    except HTTPError as error:
        codigo = error.code
        contenido = error.read().decode("utf-8")
    except (URLError, TimeoutError) as error:
        print(f"\nERROR DE CONEXIÓN: {error}")
        raise SystemExit(1)

    print(f"\n--- {metodo} {ruta} | HTTP {codigo} ---")
    try:
        resultado = json.loads(contenido)
    except json.JSONDecodeError as error:
        print(contenido)
        raise ValueError(
            f"El servidor devolvió una respuesta que no es JSON (HTTP {codigo})."
        ) from error
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    return codigo, resultado


id_caso = None
try:
    print("PROBANDO API DE THE UNKNOWN FILES")
    print("Servidor:", BASE_URL)
    iniciar_sesion()

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
    assert respuesta["estado"] == "Completado", "No se guardó el estado"

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
    id_caso = None

    print("\n¡TODAS LAS PRUEBAS TERMINARON CORRECTAMENTE!")

except (AssertionError, KeyError, ValueError, URLError, TimeoutError) as error:
    print(f"\nPRUEBA FALLIDA: {error}")
    raise SystemExit(1)
finally:
    if id_caso:
        print("\nRetirando el registro creado por esta prueba...")
        codigo, respuesta = probar("DELETE", f"/api/casos/{id_caso}")
        if codigo not in (200, 404):
            print(f"No se pudo retirar el registro de prueba {id_caso}.")
            raise SystemExit(1)
