# The Unknown Files · guion de exposición en preparación

Este guion cubre el CRUD, la API y el QR implementados. La demostración final deberá incorporar la reserva temporal cuando el equipo defina el recurso y complete su implementación.

## 0:00–0:45 Presentación
The Unknown Files es una aplicación de historias de misterio. El primer caso sigue a Bryan en un encargo cotidiano que termina complicándose. Nos dirigimos a personas que disfrutan relatos interactivos y acertijos. El taller permite administrar las fichas de los casos desde el navegador.

## 0:45–1:30 Datos y personalización
Los campos son nombre, categoria y estado. Nombre identifica el expediente, categoría organiza el tema y estado permite marcarlo como Disponible, Bloqueado o Completado. Los títulos, menú y formularios corresponden al archivo de casos. El avance del jugador se guarda en su partida.

| Tema                         | Nombre          | Categoría| Estado                  | Opciones           |
| ---                          | ---             | ---      | ---                     | ---                    |
| Archivo de casos de misterio | Expediente DEMO | Misterio | Estado administrativo | Disponible / Bloqueado / Completado |

## 1:30–3:30 CRUD en vivo
1. Abrir Taller de casos y agregar Expediente DEMO, Misterio, Disponible.
2. Consultarlo y recargar para comprobar que persiste.
3. Editar nombre o categoría y cambiar a Bloqueado. Recargar.
4. Escanear el QR del expediente y comprobar que la ficha muestra los datos actualizados.
5. Eliminar solo el registro ficticio y comprobar que desaparece.

Frase de apoyo: el formulario envía la solicitud a Flask, el servidor valida los campos y MongoDB guarda el cambio.

## 3:30–5:30 API
Con Flask iniciado, ejecutar:

    python probar_api.py

Para probar el servicio publicado, usar su URL real como argumento:

    python probar_api.py https://URL-REAL-DEL-SERVICIO

GET consulta datos, POST crea un caso, PUT actualiza sus campos y DELETE lo elimina. JSON representa el registro con claves y valores. El identificador _id distingue cada caso. La prueba muestra HTTP 201 al crear, 200 al consultar o actualizar, 400 cuando faltan datos y 404 con un identificador inválido. El script crea un registro DEMO propio y lo elimina al terminar.

Rutas implementadas: GET/POST /api/casos y GET/PUT/DELETE /api/casos/<id>.

## 5:30–6:30 Publicación e independencia
Repositorio: https://github.com/dani012345/the-unknown-files

Mostrar el último commit, el sitio público en Render y la base propia en Atlas. El código usa la base the_unknown_files y la colección casos. El relato usa además escenas y partidas. Mostrar nombres de base y colección sin enseñar contraseña ni cadena de conexión.

Flujo: editar y probar en la computadora, crear commit, hacer push a main y comprobar el despliegue de Render. Si el servicio tiene Auto-Deploy On Commit, el push dispara el despliegue. Verificar el commit que aparece como publicado. Referencias: https://render.com/docs/deploys y https://render.com/docs/deploy-flask.

Repetir las pruebas desde la versión final publicada y obtener capturas de Render, Atlas y del escaneo del QR.

## 6:30–7:00 Cierre
Explicar una dificultad real del equipo y cómo se resolvió. El navegador muestra la interfaz, Flask valida las solicitudes y MongoDB conserva los datos. El primer caso de Bryan deja espacio para ampliar el archivo con otras historias.

## Reparto y Classroom
Distribuir los seis apartados entre todos los integrantes. Si son menos de seis, una persona puede tomar dos apartados. Ensayar las acciones y explicar con sus propias palabras.

Para la entrega final de reserva temporal y QR, un integrante entrega por equipo los nombres completos y participación, enlaces de GitHub y Render, el QR y el informe PDF de 5 a 8 páginas con evidencias y los diez casos de prueba. El repositorio debe contener README y al menos cuatro commits del proceso.

## Preparación de la demostración final

El código incluye las ilustraciones iniciales de Bryan incorporadas en el commit 774ea02 y la ficha pública con QR.

Cuando esté implementada la reserva, ajustar la exposición al recorrido final de siete minutos.

1. Un minuto para presentar el proyecto y el recurso elegido.
2. Tres minutos para reservar, comprobar el bloqueo del segundo visitante, cancelar o dejar vencer y confirmar.
3. Un minuto para escanear el QR y mostrar la ficha actual.
4. Un minuto para mostrar Atlas, GitHub y Render.
5. Un minuto para explicar participación, dificultad y aprendizaje.
