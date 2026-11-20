"""Datos iniciales del catálogo y validación de portadas."""
from hashlib import sha256
from io import BytesIO

from bson import ObjectId
from flask import abort
from PIL import Image, ImageOps, UnidentifiedImageError

BRYAN_ID = ObjectId("000000000000000000000001")
CASOS_INICIALES = (
    {
        "_id": BRYAN_ID, "nombre": "Un favor", "categoria": "Misterio",
        "estado": "Disponible", "juego": "bryan",
        "descripcion": "Sigue a Bryan en un encargo que termina complicándose.",
        "portada_archivo": "img/escenas/BG01_bryan_con_celular.png",
    },
    *(
        {
            "_id": ObjectId(f"{number:024x}"), "nombre": name,
            "categoria": "Misterio", "estado": "Bloqueado",
            "descripcion": "Un próximo expediente del archivo.",
            "portada_archivo": "img/biblioteca-archivo-v1.png",
        }
        for number, name in enumerate(
            ("El último turno", "La señal", "La habitación cerrada"), start=2
        )
    ),
)


def validar_portada(archivo):
    if archivo is None or not archivo.filename:
        return {}
    data = archivo.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        abort(400, description="La portada admite hasta 5 MB.")
    try:
        with Image.open(BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError("Imagen demasiado grande")
            image.verify()
        with Image.open(BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            output = BytesIO()
            image.save(output, format="WEBP", quality=88)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        abort(400, description="Elige una imagen PNG, JPG o WebP válida de hasta 20 megapíxeles.")
    content = output.getvalue()
    return {
        "portada_datos": content, "portada_tipo": "image/webp",
        "portada_hash": sha256(content).hexdigest(),
    }
