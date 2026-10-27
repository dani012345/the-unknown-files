from flask import Flask, jsonify, render_template, request, redirect, url_for, abort
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
casos = base_datos["casos"]
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
    if estado not in ["Disponible", "Bloqueado"]:
        abort(400, description="Selecciona un estado válido.")
    return {
        "nombre": nombre,
        "categoria": categoria,
        "estado": estado}

def buscar_caso(id):
    if not ObjectId.is_valid(id):
        abort(404, description="La clave del caso no es válida.")
    caso = casos.find_one({"_id": ObjectId(id)})
    if caso is None:
        abort(404, description="Este caso ya no existe.")
    return caso

@app.route("/")
def portada():
    return render_template("portada.html")

@app.route("/inicio")
def inicio():
    return render_template("inicio.html")

@app.route("/taller")
def taller():
    lista = list(casos.find().sort("nombre", 1))
    return render_template("taller.html", casos=lista)

@app.route("/caso/bryan", methods=["GET", "POST"])
def juego_bryan():
    return jugar_bryan()

@app.route("/agregar", methods=["POST"])
def agregar():
    datos = leer_formulario()
    casos.insert_one(datos)
    return redirect(url_for("taller", _anchor="lista"))

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    caso = buscar_caso(id)
    if request.method == "POST":
        datos = leer_formulario()
        casos.update_one({"_id": caso["_id"]}, {"$set": datos})
        return redirect(url_for("taller", _anchor="lista"))
    return render_template("editar.html", caso=caso)

@app.route("/eliminar/<id>", methods=["POST"])
def eliminar(id):
    caso = buscar_caso(id)
    casos.delete_one({"_id": caso["_id"]})
    return redirect(url_for("taller", _anchor="lista"))
    
@app.errorhandler(PyMongoError)
def error_mongo(error):
    app.logger.exception("Error al consultar MongoDB")
    if request.path.startswith("/api/"):
        return jsonify({"error": "No fue posible conectar con la base de datos."}), 503
    return render_template("error.html", mensaje="No fue posible conectar con la base de datos. Revisa la configuración y vuelve a intentar."), 503

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(415)
def error_peticion(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": error.description}), error.code
    return render_template("error.html", mensaje=error.description), error.code

@app.route("/ayuda")
def ayuda():
    fecha = datetime.now().strftime("%d/%m/%Y")
    return render_template("ayuda.html", fecha=fecha)


def caso_json(caso):
    return {"_id": str(caso["_id"]), "nombre": caso.get("nombre", ""),
            "categoria": caso.get("categoria", ""), "estado": caso.get("estado", "")}

def datos_api():
    if not request.is_json:
        abort(415, description="Envía Content-Type: application/json.")
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        abort(400, description="El cuerpo debe ser un objeto JSON válido.")
    return leer_formulario(datos)

@app.route("/api/casos", methods=["GET", "POST"])
def api_casos():
    if request.method == "GET":
        return jsonify([caso_json(caso) for caso in casos.find().sort("nombre", 1)])
    datos = datos_api()
    identificador = casos.insert_one(datos).inserted_id
    respuesta = jsonify(caso_json({**datos, "_id": identificador}))
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for("api_caso", id=str(identificador))
    return respuesta

@app.route("/api/casos/<id>", methods=["GET", "PUT", "DELETE"])
def api_caso(id):
    caso = buscar_caso(id)
    if request.method == "GET":
        return jsonify(caso_json(caso))
    if request.method == "PUT":
        datos = datos_api()
        casos.update_one({"_id": caso["_id"]}, {"$set": datos})
        return jsonify(caso_json({**datos, "_id": caso["_id"]}))
    casos.delete_one({"_id": caso["_id"]})
    return jsonify({"mensaje": "Caso eliminado", "id": str(caso["_id"])})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
    