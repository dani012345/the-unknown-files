from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from datetime import datetime
import os
from bryan_game import create_game_blueprint


app = Flask(__name__)

mongo_uri = os.environ.get("MONGO_URI")

if not mongo_uri:
    if os.environ.get("RENDER"):
        raise RuntimeError("Configura MONGO_URI en Render.")
    mongo_uri = "mongodb://127.0.0.1:27017/"

cliente = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)

base_datos = cliente["the_unknown_files"]
alumnos = base_datos["casos"]
escenas = base_datos["escenas"]

bryan_blueprint, jugar_bryan = create_game_blueprint(base_datos)
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
    if estado not in ["Disponible", "Bloqueado", "Completado"]:
        abort(400, description="Selecciona un estado válido.")
    return {
        "nombre": nombre,
        "categoria": categoria,
        "estado": estado}

def buscar_alumno(id):
    if not ObjectId.is_valid(id):
        abort(404, description="La clave del caso no es válida.")
    alumno = alumnos.find_one({"_id": ObjectId(id)})
    if alumno is None:
        abort(404, description="Este alumno ya no existe.")
    return alumno

# ---------- API REST: CASOS ----------

ESTADOS_VALIDOS = ["Disponible", "Bloqueado", "Completado"]


def caso_a_json(caso):
    return {
        "id": str(caso["_id"]),
        "nombre": caso["nombre"],
        "categoria": caso["categoria"],
        "estado": caso["estado"]
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
        "estado": estado
    }, None


@app.route("/api/casos", methods=["GET"])
def api_listar_casos():
    lista = casos.find().sort("nombre", 1)
    return jsonify([caso_a_json(caso) for caso in lista]), 200


@app.route("/api/casos", methods=["POST"])
def api_crear_caso():
    datos, error = validar_json_api()
    if error:
        return error

    resultado = casos.insert_one(datos)
    nuevo_caso = casos.find_one({"_id": resultado.inserted_id})

    return jsonify(caso_a_json(nuevo_caso)), 201


@app.route("/api/casos/<id>", methods=["GET", "PUT", "DELETE"])
def api_detalle_caso(id):
    if not ObjectId.is_valid(id):
        return jsonify(error="El ID del caso no es válido."), 404

    object_id = ObjectId(id)
    caso = casos.find_one({"_id": object_id})

    if caso is None:
        return jsonify(error="No se encontró el caso solicitado."), 404

    if request.method == "GET":
        return jsonify(caso_a_json(caso)), 200

    if request.method == "PUT":
        datos, error = validar_json_api()
        if error:
            return error

        casos.update_one({"_id": object_id}, {"$set": datos})
        actualizado = casos.find_one({"_id": object_id})

        return jsonify(caso_a_json(actualizado)), 200

    casos.delete_one({"_id": object_id})
    return jsonify(mensaje="Caso eliminado correctamente.", id=id), 200

@app.route("/")
def portada():
    return render_template("portada.html")

@app.route("/inicio")
def inicio():
    return render_template("inicio.html")

@app.route("/taller")
def taller():
    lista = list(alumnos.find().sort("nombre", 1))
    return render_template("taller.html", alumnos=lista)

@app.route("/caso/bryan", methods=["GET", "POST"])
def juego_bryan():
    return jugar_bryan()

@app.route("/agregar", methods=["POST"])
def agregar():
    datos = leer_formulario()
    alumnos.insert_one(datos)
    return redirect(url_for("taller", _anchor="lista"))

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    alumno = buscar_alumno(id)
    if request.method == "POST":
        datos = leer_formulario()
        alumnos.update_one({"_id": alumno["_id"]}, {"$set": datos})
        return redirect(url_for("taller", _anchor="lista"))
    return render_template("editar.html", alumno=alumno)

@app.route("/eliminar/<id>", methods=["POST"])
def eliminar(id):
    alumno = buscar_alumno(id)
    alumnos.delete_one({"_id": alumno["_id"]})
    return redirect(url_for("taller", _anchor="lista"))
    
@app.errorhandler(PyMongoError)
def error_mongo(error):
    app.logger.exception("Error al consultar MongoDB")
    return render_template("error.html", mensaje="No fue posible conectar con la base de datos. Revisa la configuración y vuelve a intentar."), 503

@app.errorhandler(400)
@app.errorhandler(404)
def error_peticion(error):
    return render_template("error.html", mensaje=error.description), error.code

@app.route("/ayuda")
def ayuda():
    fecha = datetime.now().strftime("%d/%m/%Y")
    return render_template("ayuda.html", fecha=fecha)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
    