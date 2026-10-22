from flask import Flask, render_template, request, redirect, url_for, abort
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from datetime import datetime
import os


app = Flask(__name__)

mongo_uri = os.environ.get("MONGO_URI")

if not mongo_uri:
    if os.environ.get("RENDER"):
        raise RuntimeError("Configura MONGO_URI en Render.")
    mongo_uri = "mongodb://127.0.0.1:27017/"

cliente = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)

base_datos = cliente["the_unknown_files"]
alumnos = base_datos["casos"]

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

ESCENAS_JUEGO = {
    "bryan_inicio": {
        "case_code": "CASO 001",
        "case_name": "BRYAN",
        "archive_label": "ARCHIVO 001",
        "title": "BRYAN",
        "description": "La historia está a punto de comenzar...",
        "character": "BRYAN",
        "dialogue": (
            "Bueno... ¿vas a quedarte ahí mirando "
            "o piensas ayudarme?"
        ),
        "choice_title": "¿QUÉ HACES?",
        "choices": [
            {
                "text": "Preguntarle qué pasó.",
                "next_scene": "bryan_pregunta"
            },
            {
                "text": "Revisar lo que hay alrededor.",
                "next_scene": "bryan_investigar"
            },
            {
                "text": "Dejar que Bryan siga hablando solo.",
                "next_scene": "bryan_ignorar"
            }
        ]
    },

    "bryan_pregunta": {
        "case_code": "CASO 001",
        "case_name": "BRYAN",
        "archive_label": "ARCHIVO 001-A",
        "title": "UNA EXPLICACIÓN",
        "description": "Escena provisional",
        "character": "BRYAN",
        "dialogue": "Te dije que algo no estaba bien...",
        "choice_title": "¿CÓMO RESPONDES?",
        "choices": [
            {
                "text": "Pedirle más detalles.",
                "next_scene": "bryan_inicio"
            },
            {
                "text": "Volver a observar el lugar.",
                "next_scene": "bryan_investigar"
            }
        ]
    },

    "bryan_investigar": {
        "case_code": "CASO 001",
        "case_name": "BRYAN",
        "archive_label": "EVIDENCIA 001-B",
        "title": "ALGO FUERA DE LUGAR",
        "description": "Escena provisional",
        "character": "SISTEMA",
        "dialogue": "No parece haber nada extraño a simple vista.",
        "choice_title": "¿QUÉ HACES?",
        "choices": [
            {
                "text": "Regresar con Bryan.",
                "next_scene": "bryan_inicio"
            },
            {
                "text": "Preguntarle por la evidencia.",
                "next_scene": "bryan_pregunta"
            }
        ]
    },

    "bryan_ignorar": {
        "case_code": "CASO 001",
        "case_name": "BRYAN",
        "archive_label": "REGISTRO 001-C",
        "title": "SILENCIO",
        "description": "Escena provisional",
        "character": "BRYAN",
        "dialogue": "¿En serio? Está bien. Como quieras...",
        "choice_title": "¿QUÉ HACES AHORA?",
        "choices": [
            {
                "text": "Hablar con Bryan.",
                "next_scene": "bryan_pregunta"
            },
            {
                "text": "Investigar el lugar.",
                "next_scene": "bryan_investigar"
            }
        ]
    }
}

@app.route("/")
@app.route("/portada")
def portada():
    return render_template("portada.html")

@app.route("/inicio")
def inicio():
    return render_template("index.html")

@app.route("/taller")
def taller():
    lista = list(alumnos.find().sort("nombre", 1))
    return render_template("taller.html", alumnos=lista)

@app.route("/caso/bryan", methods=["GET", "POST"])
def juego_bryan():
    if request.method == "POST":
        escena_id = request.form.get("scene_id", "bryan_inicio")
    else:
        escena_id = "bryan_inicio"
    escena = ESCENAS_JUEGO.get(escena_id)
    if escena is None:
        escena = ESCENAS_JUEGO["bryan_inicio"]
    return render_template("juego.html", scene=escena)

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
    