# The Unknown Files: exposición de 7 minutos

## 0:00–0:45 Presentación
The Unknown Files es una aplicación de historias de misterio. El primer caso sigue a Bryan en un encargo cotidiano que termina complicándose. Nos dirigimos a personas que disfrutan relatos interactivos y acertijos. El taller permite administrar las fichas de los casos desde el navegador.

## 0:45–1:30 Datos y personalización
Los campos son nombre, categoria y estado. Nombre identifica el expediente, categoría organiza el tema y estado permite marcarlo como Disponible o Bloqueado. Los títulos, menú y formularios corresponden al archivo de casos. Estos estados son etiquetas administrativas, distintas del avance del jugador.

| Tema | Nombre | Categoría | Estado | Dos opciones |
| --- | --- | --- | --- | --- |
| Archivo de casos de misterio | Expediente DEMO | Misterio | Disponibilidad del caso | Disponible / Bloqueado |

## 1:30–3:30 CRUD en vivo
1. Abrir Taller de casos y agregar Expediente DEMO, Misterio, Disponible.
2. Consultarlo y recargar para comprobar que persiste.
3. Editar nombre o categoría y cambiar a Bloqueado. Recargar.
4. Eliminar solo el registro ficticio y comprobar que desaparece.

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

No se ha comprobado en esta entrega el enlace público de Render ni una captura del panel de Atlas. Esas evidencias deben obtenerse del servicio y del proyecto reales del equipo.

## 6:30–7:00 Cierre
Una dificultad fue mantener la misma validación entre el formulario y la API. Reutilizamos las reglas de los campos y devolvemos errores controlados. Aprendimos que el navegador muestra la interfaz, Flask valida las solicitudes y MongoDB conserva los datos. El primer caso de Bryan deja espacio para ampliar el archivo con otras historias.

## Reparto y Classroom
Distribuir los seis apartados entre todos los integrantes. Si son menos de seis, una persona puede tomar dos apartados. Ensayar las acciones y explicar con sus propias palabras.

Cada integrante entrega nombres y grupo, enlaces de GitHub y Render, la tabla anterior y cuatro capturas: CRUD personalizado, consulta JSON de API, último commit y base/colección propias en Atlas. Si el repositorio es privado, dar acceso al docente.

## Estado de esta entrega
La apariencia y el motor narrativo vuelven a la base 3ba26c89ea217165e0e4765a6c17459879c43192. Los cambios visuales posteriores quedaron en un respaldo Git stash. Sobre esa base se añadieron la API y los dos estados requeridos. No se modificaron las partidas ni el guion.
