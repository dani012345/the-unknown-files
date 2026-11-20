# The Unknown Files

Aplicación de historias interactivas de misterio. El jugador sigue el caso de Bryan, toma decisiones, resuelve acertijos y conserva su progreso. El Taller permite administrar los expedientes y compartir su ficha mediante un código QR.

## Equipo

Pendiente completar los nombres, grupo y participación de todos los integrantes.

## Enlaces del proyecto

- [Aplicación en Render](https://the-unknown-files.onrender.com)
- [Repositorio en GitHub](https://github.com/dani012345/the-unknown-files)

## Funciones actuales

- Taller con creación, consulta, edición y eliminación de casos.
- Estados Disponible, Bloqueado y Completado en formularios y API.
- Ficha pública por identificador y QR que consulta la información actual.
- Historia de Bryan con decisiones, acertijos, inventario e historial.
- Partidas y saldo asociados a una cuenta o a una sesión temporal de invitado.
- Recompensas por decisiones y carrito de puntos con compra simulada.
- Registro con usuario, correo y descripción opcional, e inicio de sesión con usuario o correo.
- Partidas y puntos vinculados a la cuenta para continuar desde otro dispositivo.
- Invitados con progreso temporal y compras bloqueadas.

## Acceso y administración

La portada muestra Abrir o Continuar según la partida de la sesión. Abrir permite registrarse, iniciar sesión o entrar como invitado. Salir cierra la sesión después de confirmar.

Las contraseñas se guardan como hashes. Los datos del perfil son privados para la cuenta iniciada. El correo queda registrado para la futura recuperación de contraseña, cuyo servicio de envío está pendiente.

Los nuevos registros tienen rol de jugador. Para identificar a los administradores del equipo, configura en Render la variable `ADMIN_USERNAMES` con sus nombres de usuario separados por comas. Registra primero las cuentas del equipo y escribe sus nombres exactos en esa variable. Las cuentas autorizadas pueden administrar casos y utilizar las operaciones de escritura de la API.

La biblioteca está en `/taller`. Los jugadores pueden consultar las fichas y jugar Bryan, y los demás registros aparecen como En proceso.

Las cuentas conservan sus datos al salir. Los invitados usan una sesión de navegador con duración máxima de un día. Sus datos temporales tienen fecha de caducidad y MongoDB los elimina mediante índices TTL. Al salir se pierde el acceso a esa sesión. La selección de iconos y las reglas nuevas de reinicio quedan para los siguientes pasos.

## Estado de la reserva y las compras

La reserva temporal está pendiente de definir con el equipo. Falta elegir el recurso, su duración entre 3 y 5 minutos y el efecto de confirmarlo. Después se implementarán el bloqueo entre visitantes, el vencimiento y la cancelación.

El carrito actual añade puntos mediante una compra simulada gratuita. El uso de esos puntos para adquirir o desbloquear contenido está pendiente de definir.

Los estados del Taller son etiquetas administrativas del expediente. El progreso del jugador se conserva en su partida.

## Requisitos

Python 3.12, dependencias de `requirements.txt` y MongoDB. Para publicar se utiliza MongoDB Atlas.

## Ejecución en Windows con PowerShell

Abre la terminal en la carpeta que contiene `app.py`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MONGO_URI = 'PEGA_AQUI_TU_CADENA_DE_ATLAS'
.\.venv\Scripts\python.exe app.py
```

Sustituye el texto del ejemplo por la conexión de Atlas. Conserva las credenciales en la terminal o en las variables de entorno del servicio.

Abre `http://127.0.0.1:5000`. Si omites `MONGO_URI` al ejecutar localmente, la aplicación intenta usar MongoDB en `127.0.0.1:27017`.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `MONGO_URI` | Conexión de MongoDB, obligatoria en Render. |
| `APP_BASE_URL` | URL pública opcional para los enlaces del QR. |
| `RENDER_EXTERNAL_URL` | URL que proporciona Render y que la aplicación usa automáticamente. |
| `API_BASE_URL` | URL opcional utilizada por `probar_api.py`. |
| `ADMIN_USERNAMES` | Usuarios administradores, separados por comas. |
| `API_USERNAME` y `API_PASSWORD` | Credenciales de una cuenta administradora para ejecutar la prueba de API. |

La aplicación lee las variables del proceso. La configuración local anterior utiliza PowerShell.

## Datos

La base es `the_unknown_files` y contiene las colecciones `casos`, `escenas`, `partidas`, `saldos`, `usuarios` y `sesiones`.

El motor inserta las escenas iniciales que faltan al abrir el juego. El progreso y saldo de una cuenta se recuperan al iniciar sesión. Las antiguas partidas asociadas a `uf_player` pueden abrirse al entrar como invitado desde su navegador original.

## Modo de prueba de administradores

Inicia sesión con una cuenta cuyo `role` sea `admin`. En Inicio aparece **Modo de prueba**; también está en el menú del juego.

- Puedes comenzar desde dormitorio, cocina o patio. Los pasos previos se preparan usando las reglas del motor; en patio se llega con Pollo alimentado.
- Cada punto reemplaza la prueba actual de esa sesión. Puedes repetirlo sin límite o continuar la prueba que dejaste abierta.
- La prueba usa `partidas_prueba`, separada de `partidas` y `saldos`, y no genera premios. Se elimina al vencer su sesión mediante un índice TTL de MongoDB.
- El menú del juego permite cambiar de punto o salir de prueba para continuar la partida real. Los jugadores e invitados no tienen acceso, incluso usando la URL directamente.
- Si cambia el guion y ya no permite preparar un punto, se informa del problema sin reemplazar la prueba anterior.

## Render

Configura la rama que vayas a publicar, Python 3, instalación `pip install -r requirements.txt` e inicio `gunicorn app:app --bind 0.0.0.0:$PORT`.

Agrega `MONGO_URI` en Environment y autoriza en Atlas los rangos de salida del servicio. Después del despliegue comprueba el commit publicado, el Taller, la edición, el juego y el QR desde el celular.

## Pruebas del CRUD y QR

1. Inicia sesión con una cuenta de administrador y crea un expediente de demostración en el Taller.
2. Abre su ficha y escanea su QR desde el sitio de Render.
3. Edita su nombre y cambia el estado a Completado.
4. Recarga y escanea el mismo QR. Comprueba los datos actualizados.
5. Abre un identificador inexistente y comprueba el mensaje de error.
6. Elimina el expediente de demostración.

Con el servidor iniciado y una cuenta de administrador, puedes probar la API. Configura API_USERNAME y API_PASSWORD en las variables de la terminal antes de ejecutar el script.

```powershell
.\.venv\Scripts\python.exe probar_api.py
.\.venv\Scripts\python.exe probar_api.py https://the-unknown-files.onrender.com
```

El script crea un registro propio de prueba, consulta y actualiza sus datos, comprueba errores y elimina ese registro. Devuelve un código de salida de error si alguna comprobación falla.

## Entrega final pendiente

- Definir e implementar la reserva temporal y completar sus pruebas con dos navegadores.
- Completar nombres, grupo y participación.
- Reunir capturas del CRUD, QR en celular, Atlas, GitHub y Render.
- Documentar las diez pruebas de la consigna, incluida la prueba cruzada en otro equipo.
- Preparar el informe PDF de 5 a 8 páginas y adaptar la exposición de 7 minutos.

Las capturas y resultados deben obtenerse de la versión final publicada.
