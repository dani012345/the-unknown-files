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

## Tienda, archivos secretos y reservas

Abre **Tienda** desde el menú superior o desde Mis puntos / Carrito. Los visitantes e invitados pueden explorar; comprar y reservar requiere una cuenta.

- Archivos digitales: 10 y 20 puntos inicialmente. Antes de comprar se muestra el nivel de spoiler y se solicita confirmación. El texto completo solo se envía a propietarios y administradores. Las notas iniciales recogen detalles del caso 001; el significado del triángulo continúa abierto.
- Merch de demostración: ocho productos con stock limitado. No se cobra dinero ni se realizan envíos. El producto tiene apariencia realista y el entorno conserva el acabado con pinceladas.

| Artículo | Puntos | Unidades iniciales |
| --- | ---: | ---: |
| Pollo, jefe de la casa | 30 | 3 |
| El expediente de Bryan | 60 | 1 |
| La llave del archivo | 25 | 5 |
| Notas del investigador | 45 | 4 |
| Turno nocturno | 40 | 4 |
| Bolsa del archivo central | 55 | 3 |
| Identificación de colección | 35 | 3 |
| Entre páginas y pistas | 20 | 6 |

Estos son los valores iniciales. Las ediciones del administrador y las existencias actuales se conservan al actualizar.
- La reserva dura **5 minutos**, usa fechas UTC del servidor y aparta una unidad concreta. Reservar no cobra puntos; confirmar sí. Cada cuenta puede tener una reserva temporal activa y adquirir una copia de cada artículo por periodo.
- Cancelar o vencer cambia el estado y libera la unidad. El contador consulta al servidor cada 5 segundos. Si se cierra el navegador, la próxima consulta o intento de reserva procesa los vencimientos antes de revisar disponibilidad.
- El comprobante público muestra folio, artículo, precio y estado. Su QR se genera localmente con `qrcode` y consulta siempre la misma ficha. No incluye datos de la persona ni contenido privado.
- Mi colección permite volver a leer los archivos comprados desde otra sesión. El primer reinicio conserva el acceso; los siguientes lo revocan al cambiar el periodo de la cuenta. Los comprobantes permanecen como historial y las unidades vendidas no se reponen automáticamente.
- Los administradores pueden editar textos públicos y privados, precios, portada, publicación y añadir existencias desde **Editar artículo**. **Preparar un nuevo artículo** permite crear archivos o merch futuros. Los borradores solo se ven en el catálogo del administrador.
- El catálogo inicial se inserta una sola vez; reiniciar Flask o Render no restaura unidades vendidas ni sobrescribe ediciones.

El carrito anterior continúa ofreciendo paquetes de puntos gratuitos de demostración. Los puntos ganados en la historia también sirven para la tienda.

### Persistencia y compras simultáneas

Colecciones: `productos_tienda`, `unidades_tienda`, `reservas_tienda`, `compras_tienda` y `saldos`. Una reserva puede estar `temporal`, `confirmada`, `cancelada` o `vencida`.

Los cambios de inventario, reservas, compras y saldo se realizan en transacciones de MongoDB, con comprobaciones de saldo y periodo. Confirmar o comprar de nuevo no duplica el cobro. Las operaciones requieren MongoDB Atlas o un replica set local; un servidor MongoDB standalone permite explorar, pero informa del requisito al intentar comprar. Referencia: [transacciones de PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/).

Ejecuta de nuevo `pip install -r requirements.txt` si tu entorno aún no tiene `qrcode`.

### Pruebas de la tienda

`tests/check_tienda.py` comprueba privacidad, compra, rollback ante fallos, dos cuentas compitiendo por la última unidad, cancelación, vencimiento, confirmación repetida, QR, administración y reinicios. Usa exclusivamente un MongoDB de pruebas en loopback, por defecto el replica set `codexShop` del puerto 27129, y crea una base nueva con prefijo `shop_test_` en cada ejecución. Nunca usa `MONGO_URI` ni tu base del juego. Puedes indicar otra URI local de pruebas con `SHOP_TEST_MONGO_URI`.

```powershell
.\.venv\Scripts\python.exe tests/check_tienda.py
```

Antes de entregar, repetir la prueba con dos navegadores en Render, comprobar los documentos en Atlas y escanear el QR desde un celular. Las pruebas locales no sustituyen esas evidencias.

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

## Reinicio de partidas

Cuando hay progreso, la portada muestra **Nueva partida**. También se puede abrir desde el menú del juego. El panel pide confirmación antes de cambiar los datos.

- El primer reinicio conserva puntos, compras simuladas y carrito; la historia vuelve al principio.
- A partir del segundo se borran el saldo (incluidos los puntos comprados) y el carrito. El historial de movimientos conserva un registro del borrado.
- El contador se guarda con la partida de la cuenta y se comparte entre dispositivos. Las partidas existentes comienzan con cero reinicios de esta nueva regla.
- Los premios de antes de un borrado no se recuperan al recargar; las nuevas decisiones pueden obtener puntos una vez por periodo.
- El modo de prueba de administradores sigue separado y no consume estos reinicios ni modifica el saldo.
- Para invitados, la regla dura lo que dure su sesión temporal.

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

- Repetir las pruebas de reserva con dos navegadores en Render y recoger las evidencias de Atlas y del QR en celular.
- Completar nombres, grupo y participación.
- Reunir capturas del CRUD, QR en celular, Atlas, GitHub y Render.
- Documentar las diez pruebas de la consigna, incluida la prueba cruzada en otro equipo.
- Preparar el informe PDF de 5 a 8 páginas y adaptar la exposición de 7 minutos.

Las capturas y resultados deben obtenerse de la versión final publicada.
