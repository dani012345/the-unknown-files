from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, g, send_file
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from bson import ObjectId
from datetime import datetime
from pathlib import Path
from io import BytesIO
from werkzeug.security import safe_join
from urllib.parse import quote
import os
import secrets
from bryan_game import create_game_blueprint, STORY_VERSION
from puntos import create_points_blueprint
from cuentas import create_accounts_blueprint
from catalogo import BRYAN_ID, CASOS_INICIALES, validar_portada
from tienda import create_shop_blueprint


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

@app.url_defaults
def version_static_asset(endpoint, values):
    if endpoint != "static" or not values.get("filename"):
        return
    path = safe_join(app.static_folder, values["filename"])
    if path is None:
        return
    try:
        info = Path(path).stat()
    except OSError:
        return
    values["v"] = f"{info.st_mtime_ns:x}-{info.st_size:x}"


ESTADOS_VALIDOS = ("Disponible", "Bloqueado", "Completado")

mongo_uri = os.environ.get("MONGO_URI")

if not mongo_uri:
    if os.environ.get("RENDER"):
        raise RuntimeError("Configura MONGO_URI en Render.")
    mongo_uri = "mongodb://127.0.0.1:27017/"

cliente = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)

base_datos = cliente["the_unknown_files"]
casos = base_datos["casos"]
escenas = base_datos["escenas"]
catalogo_revisado = False


def asegurar_catalogo():
    global catalogo_revisado
    if catalogo_revisado:
        return
    for caso in CASOS_INICIALES:
        try:
            casos.update_one({"_id": caso["_id"]}, {"$setOnInsert": caso}, upsert=True)
        except DuplicateKeyError:
            if casos.find_one({"_id": caso["_id"]}) is None:
                raise
    catalogo_revisado = True


def detalles_caso(datos):
    if "descripcion" not in datos:
        return {}
    descripcion = datos["descripcion"]
    if not isinstance(descripcion, str) or len(descripcion) > 2000:
        abort(400, description="La descripción admite hasta 2000 caracteres de texto.")
    return {"descripcion": descripcion.strip()}

app.register_blueprint(create_accounts_blueprint(base_datos))


@app.before_request
def require_player():
    admin_action = (
        request.endpoint in ("agregar", "editar", "eliminar")
        or request.endpoint in ("api_crear_caso", "api_detalle_caso")
        and request.method in ("POST", "PUT", "DELETE")
    )
    if admin_action:
        if not g.account or g.account.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify(error="Esta acción requiere una cuenta de administrador."), 403
            abort(403, description="Esta acción requiere una cuenta de administrador.")
        if request.method == "POST" and not request.path.startswith("/api/"):
            if not secrets.compare_digest(request.form.get("access_csrf", ""), g.access_session["csrf"]):
                abort(400, description="El formulario venció. Recarga la página.")
    if request.endpoint in ("inicio", "juego_bryan", "bryan.history", "puntos.cart"):
        access = g.get("access_session")
        if not access or not (g.account or access["guest"]):
            return redirect(url_for("cuentas.entry"))
        if request.endpoint == "puntos.cart" and request.method == "POST" and not g.account:
            abort(403, description="Regístrate para utilizar las compras.")

puntos_blueprint, mostrar_inicio, points_store = create_points_blueprint(base_datos)
app.register_blueprint(puntos_blueprint)
tienda_blueprint, shop_store = create_shop_blueprint(base_datos, points_store)
app.register_blueprint(tienda_blueprint)

bryan_blueprint, jugar_bryan = create_game_blueprint(base_datos, points_store)
app.register_blueprint(bryan_blueprint)

def leer_formulario(datos=None):
    if datos is None:
        datos = request.form
    campos = ("nombre", "categoria", "estado")
    if any(not isinstance(datos.get(c, ""), str) for c in campos):
        abort(400, description="Los campos deben contener texto.")
    nombre = datos.get("nombre", "").strip()
    categoria = datos.get("categoria", "").strip()
    estado = datos.get("estado", "").strip()
    if not nombre or not categoria or not estado:
        abort(400, description="Completa nombre, categoría y estado.")
    if len(nombre) > 80 or len(categoria) > 20:
        abort(400, description="Máximo: nombre 80 y categoría 20.")
    if estado not in ESTADOS_VALIDOS:
        abort(400, description="Selecciona un estado válido.")
    return {
        "nombre": nombre,
        "categoria": categoria,
        "estado": estado,
        **detalles_caso(datos)}

def buscar_caso(id):
    if not ObjectId.is_valid(id):
        abort(404, description="La clave del caso no es válida.")
    asegurar_catalogo()
    caso = casos.find_one({"_id": ObjectId(id), "oculto": {"$ne": True}})
    if caso is None:
        abort(404, description="Este expediente ya no existe.")
    return caso

# ---------- API REST: CASOS ----------

def caso_a_json(caso):
    return {
        "id": str(caso["_id"]),
        "nombre": caso["nombre"],
        "categoria": caso["categoria"],
        "estado": caso["estado"],
        "descripcion": caso.get("descripcion", "Una historia que todavía espera ser abierta."),
        "jugable": caso.get("juego") == "bryan",
        "portada_url": (
            url_for("imagen_caso", id=str(caso["_id"]), v=caso["portada_hash"])
            if caso.get("portada_hash")
            else url_for("static", filename=caso.get("portada_archivo", "img/biblioteca-archivo-v1.png"))
        ),
    }


def validar_json_api():
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return None, (jsonify(error="Envía un objeto JSON válido."), 400)

    campos = ("nombre", "categoria", "estado")

    if any(not isinstance(datos.get(campo), str) for campo in campos):
        return None, (jsonify(error="Los campos deben contener texto."), 400)

    nombre = datos["nombre"].strip()
    categoria = datos["categoria"].strip()
    estado = datos["estado"].strip()

    if not nombre or not categoria or not estado:
        return None, (jsonify(error="Todos los campos son obligatorios."), 400)

    if len(nombre) > 80 or len(categoria) > 20:
        return None, (jsonify(error="Máximo: nombre 80 y categoría 20 caracteres."), 400)

    if estado not in ESTADOS_VALIDOS:
        return None, (jsonify(error="Estado inválido."), 400)

    return {
        "nombre": nombre,
        "categoria": categoria,
        "estado": estado,
        **detalles_caso(datos),
    }, None


@app.route("/api/casos", methods=["GET"])
def api_listar_casos():
    asegurar_catalogo()
    lista = casos.find({"oculto": {"$ne": True}}, {"portada_datos": 0}).sort("nombre", 1)
    return jsonify([caso_a_json(caso) for caso in lista]), 200


@app.route("/api/casos", methods=["POST"])
def api_crear_caso():
    datos, error = validar_json_api()
    if error:
        return error

    resultado = casos.insert_one(datos)
    nuevo_caso = {"_id": resultado.inserted_id, **datos}

    return jsonify(caso_a_json(nuevo_caso)), 201


@app.route("/api/casos/<id>", methods=["GET", "PUT", "DELETE"])
def api_detalle_caso(id):
    if not ObjectId.is_valid(id):
        return jsonify(error="El ID del caso no es válido."), 404

    object_id = ObjectId(id)
    asegurar_catalogo()
    caso = casos.find_one({"_id": object_id, "oculto": {"$ne": True}})

    if caso is None:
        return jsonify(error="No se encontró el caso solicitado."), 404

    if request.method == "GET":
        return jsonify(caso_a_json(caso)), 200

    if request.method == "PUT":
        datos, error = validar_json_api()
        if error:
            return error

        actualizado = casos.find_one_and_update(
            {"_id": object_id, "oculto": {"$ne": True}}, {"$set": datos}, return_document=ReturnDocument.AFTER
        )
        if actualizado is None:
            return jsonify(error="Este expediente ya no existe."), 404

        return jsonify(caso_a_json(actualizado)), 200

    if object_id == BRYAN_ID:
        return jsonify(error="El caso de Bryan se conserva como juego principal. Puedes editar su ficha."), 400
    if any(caso["_id"] == object_id for caso in CASOS_INICIALES):
        casos.update_one({"_id": object_id}, {"$set": {"oculto": True}})
    else:
        casos.delete_one({"_id": object_id})
    return jsonify(mensaje="Caso eliminado correctamente.", id=id), 200

@app.route("/")
def portada():
    access = g.get("access_session")
    has_progress = False
    if access and (g.account or access["guest"]):
        part = base_datos["partidas"].find_one({
            "owner_hash": access["owner"], "case_id": "bryan", "story_version": STORY_VERSION,
        }, sort=[('created_at', -1), ('_id', -1)])
        has_progress = bool(part and (len(part.get('history', [])) > 1 or part.get('decisions')))
    return render_template("portada.html", has_progress=has_progress)

@app.route("/inicio")
def inicio():
    return mostrar_inicio()


@app.get("/configuracion")
def configuracion():
    return render_template("configuracion.html")

@app.route("/taller")
def taller():
    asegurar_catalogo()
    base_publica = (
        os.environ.get("APP_BASE_URL", "").strip()
        or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
        or request.host_url
    ).rstrip("/")
    expedientes = []
    for documento in casos.find({"oculto": {"$ne": True}}, {"portada_datos": 0}).sort("nombre", 1):
        caso = caso_a_json(documento)
        caso["enlace_ficha"] = base_publica + url_for("ficha_caso", id=caso["id"])
        caso["enlace_qr"] = (
            "https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=12&data="
            + quote(caso["enlace_ficha"], safe="")
        )
        expedientes.append(caso)
    expedientes.sort(key=lambda caso: not caso["jugable"])
    return render_template("taller.html", casos=expedientes, estados=ESTADOS_VALIDOS)


@app.get("/expediente/<id>")
def ficha_caso(id):
    caso = caso_a_json(buscar_caso(id))
    return render_template("ficha_caso.html", caso=caso), {"Cache-Control": "no-store"}


@app.get("/portada-caso/<id>")
def imagen_caso(id):
    caso = buscar_caso(id)
    if not caso.get("portada_datos"):
        return redirect(url_for("static", filename=caso.get("portada_archivo", "img/biblioteca-archivo-v1.png")))
    response = send_file(
        BytesIO(caso["portada_datos"]), mimetype=caso["portada_tipo"],
        etag=caso["portada_hash"], conditional=True, max_age=0,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.route("/caso/bryan", methods=["GET", "POST"])
def juego_bryan():
    return jugar_bryan()

@app.route("/agregar", methods=["POST"])
def agregar():
    datos = leer_formulario()
    datos.update(validar_portada(request.files.get("portada")))
    casos.insert_one(datos)
    return redirect(url_for("taller", _anchor="lista"))

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    caso = buscar_caso(id)
    if request.method == "POST":
        datos = leer_formulario()
        datos.update(validar_portada(request.files.get("portada")))
        resultado = casos.update_one({"_id": caso["_id"]}, {"$set": datos})
        if not resultado.matched_count:
            abort(404, description="Este expediente ya no existe.")
        return redirect(url_for("taller", _anchor="lista"))
    return render_template("editar.html", caso=caso, portada_url=caso_a_json(caso)["portada_url"], estados=ESTADOS_VALIDOS)

@app.route("/eliminar/<id>", methods=["POST"])
def eliminar(id):
    caso = buscar_caso(id)
    if caso["_id"] == BRYAN_ID:
        abort(400, description="El caso de Bryan se conserva como juego principal. Puedes editar su ficha.")
    if any(inicial["_id"] == caso["_id"] for inicial in CASOS_INICIALES):
        casos.update_one({"_id": caso["_id"]}, {"$set": {"oculto": True}})
    else:
        casos.delete_one({"_id": caso["_id"]})
    return redirect(url_for("taller", _anchor="lista"))
    
@app.errorhandler(PyMongoError)
def error_mongo(error):
    app.logger.exception("Error al consultar MongoDB")
    mensaje = "No fue posible conectar con la base de datos. Revisa la configuración y vuelve a intentar."
    if request.path.startswith("/api/"):
        return jsonify(error=mensaje), 503
    return render_template("error.html", mensaje=mensaje), 503

@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(413)
@app.errorhandler(404)
def error_peticion(error):
    mensaje = "La portada admite hasta 5 MB. Elige una imagen más pequeña." if error.code == 413 else error.description
    if request.path.startswith("/api/"):
        return jsonify(error=mensaje), error.code
    return render_template("error.html", mensaje=mensaje), error.code

@app.route("/ayuda")
def ayuda():
    fecha = datetime.now().strftime("%d/%m/%Y")
    return render_template("ayuda.html", fecha=fecha)

if __name__ == "__main__":
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=True)
    
