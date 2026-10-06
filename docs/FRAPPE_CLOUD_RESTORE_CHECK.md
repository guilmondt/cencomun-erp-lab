# Verificar el entorno Frappe guardado en una tarea cloud nueva

**Estado: ejecución separada terminada según el coordinador; resultado y evidencia
pendientes de incorporación.** No se vuelve a ejecutar desde esta tarea. Este
procedimiento se conserva para futuras verificaciones reproducibles. Los
ensayos de sitios aislados y el replay de 18 grupos en esta máquina no acreditan
restauración cloud. El usuario
confirmó que el catálogo ya conserva `ccm-erp-lab-frappe` apuntando a
`fcf690dbc58b2b2dcf8d045c49976e3613e804cf`. Esta preparación no vuelve a
Guardar/Publicar ese entorno.

## Identidades que deben conservarse

| Elemento | Valor esperado |
| --- | --- |
| Entorno guardado | `ccm-erp-lab-frappe` |
| Repositorio | `guilmondt/cencomun-erp-lab` |
| Rama | `lab/frappe-baseline` |
| Commit del snapshot guardado | `fcf690dbc58b2b2dcf8d045c49976e3613e804cf` |
| Frappe 16.36.1 | `97a5dd93ca5883bcc9c4ef9834120c5cba397b67` |
| ERPNext 16.36.1 | `fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba` |
| SHA256 de versions.lock | `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816` |
| Sitio / base | `ccm-core.test` / `ccm_core_lab` |
| Empresa / almacén consultados | `CCM-LAB-001` / `WH-LAB-001-HTTP - CLAB` |
| Producto / precio / existencia | `P001` / USD `50.00` / `5` unidades |

El commit de **preparación** publicado posteriormente contiene este procedimiento
y el verificador. No es el commit del snapshot guardado. Registrar ambos SHAs
en la evidencia: primero se verifica el checkout retenido `fcf690d`; después se
lee el verificador del commit de preparación sin cambiar el checkout.

## Procedimiento reproducible

1. Abrir **otra tarea cloud**, seleccionar el entorno guardado y el repositorio
   indicados. Solicitar el checkout esperado `fcf690d` en `lab/frappe-baseline`.
   Anotar la URL/ID real de la nueva tarea. No reutilizar esta sesión, crear
   otro sitio, ni considerar un reinicio de procesos como una nueva tarea.
2. Antes de instalar o modificar nada, verificar la identidad inicial:

   ```bash
   cd /workspace/cencomun-erp-lab
   git branch --show-current
   git rev-parse HEAD
   git status --porcelain
   test "$(git rev-parse HEAD)" = fcf690dbc58b2b2dcf8d045c49976e3613e804cf
   test "$(git branch --show-current)" = lab/frappe-baseline
   test -z "$(git status --porcelain --untracked-files=all)"
   test -f /workspace/.local/frappe-integral/core-site-created
   test -f /workspace/.local/frappe-integral/core-private.json
   test -f /workspace/.local/frappe-integral/bench/sites/ccm-core.test/site_config.json
   ```

   Si falla la identidad o faltan archivos, registrar FAIL de restauración y
   conservar el estado para diagnóstico. No hacer checkout, install, new-site,
   restore, migrate, seed ni `run.sh` para hacer pasar esta comprobación.
3. Copiar el SHA completo del commit de preparación desde el PR #4 revisado,
   fijarlo en `CCM_VERIFIER_COMMIT` y leer exclusivamente su verificador. Esa
   lectura añade objetos Git y un archivo temporal; conserva HEAD y los datos
   del snapshot. Sustituir las dos entradas siguientes por valores reales:

   ```bash
   CCM_VERIFIER_COMMIT='<SHA completo del commit de preparación revisado>'
   CCM_NEW_TASK_REFERENCE='<URL o ID real de esta tarea cloud nueva>'
   git fetch --no-tags origin "$CCM_VERIFIER_COMMIT"
   git show "${CCM_VERIFIER_COMMIT}:scripts/core-test/verify_cloud_snapshot.py" > /tmp/ccm-verify-cloud-snapshot.py
   test "$(git rev-parse HEAD)" = fcf690dbc58b2b2dcf8d045c49976e3613e804cf
   ```

4. Arrancar **los servicios retenidos**, usando los scripts existentes en el
   snapshot. Los procesos pueden no sobrevivir al cambio de tarea; arrancarlos
   no reconstruye el sitio ni sus datos:

   ```bash
   source scripts/frappe-integral/env.sh
   export PATH="$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
   python scripts/frappe-integral/services.py start
   python scripts/core-test/http_services.py start
   python scripts/frappe-integral/services.py status
   "$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/core-test/readiness.py
   ```

   Deben estar activos MariaDB `127.0.0.1:3307`, Redis cache `13000` y queue
   `11000`, web `8000`, worker, Socket.IO local, Nginx `8080`, adaptador `8090`
   y consumidor ficticio `8091`. Esperar su arranque y repetir el probe de
   lectura si aún inicializan; no regenerar credenciales ni datos.
5. Ejecutar el verificador y conservar su JSON sin secretos:

   ```bash
   "$CCM_FRAPPE_ROOT/bench/env/bin/python" /tmp/ccm-verify-cloud-snapshot.py \
     --expected-commit fcf690dbc58b2b2dcf8d045c49976e3613e804cf \
     --task-reference "$CCM_NEW_TASK_REFERENCE" > /tmp/ccm-cloud-restoration.json
   cat /tmp/ccm-cloud-restoration.json
   ```

   Un resultado PASS exige checkout limpio, pins/SHAs y hashes del manifiesto
   iguales; flag LAB activo y medición desactivada; autenticación con el Reader
   **retenido**; precio USD `50.00` y stock `5` coincidentes por adaptador y API
   nativa. Comprueba también `/api/method/ping` del proxy baseline y el puerto
   del consumidor. Ninguna llamada crea pedidos o eventos. El verificador
   nunca imprime tokens, contraseñas, headers ni traceback.
6. Adjuntar el JSON, URL/ID de esa tarea, SHA del verificador y estado de servicios
   al informe de restauración. Cambiar UNRUN a PASS solo con esa evidencia de
   una tarea realmente nueva. Una prueba local con `LOCAL-REHEARSAL` únicamente
   valida el instrumento. Esta comprobación no aprueba el criterio 13 ni ejecuta
   sus escenarios de patch.

## Diagnóstico paso a paso

**Checkout inesperado o faltan runtime/sitio/credenciales:**

1. Registrar HEAD, rama, URL/ID de tarea y exactamente qué archivo faltó; no
   publicar contenido de archivos privados.
2. Comprobar en la tarea la selección del entorno guardado y commit esperado;
   contrastarlos con los datos del catálogo que ya verificó el usuario.
3. Marcar la comprobación FAIL; investigar la retención/configuración cloud
   antes de reconstruir. Reconstruir el sitio sería otra prueba de instalación.
4. Cualquier corrección del entorno guardado requiere una tarea posterior
   autorizada; esta tarea no repite Guardar/Publicar.

**Servicio detenido, puerto ocupado o respuesta HTTP fallida:**

1. Ejecutar `services.py status` e identificar el servicio afectado.
2. Revisar su log privado con `scripts/core-test/log_tail.py`, que redacta las
   credenciales. No usar `cat` sobre logs/config privados.
3. Si está detenido, repetir únicamente `services.py start <servicio>` o
   `http_services.py start <adapter|consumer>`. Si hay puerto ocupado, identificar
   el proceso; no eliminar un proceso ajeno ni borrar PID/sockets para forzar.
4. Repetir readiness y el verificador. Conservar el fallo inicial y el intento
   posterior; declarar FAIL/BLOCKED si no se recupera con datos retenidos.

**401/403, precio/stock distinto o hash/flag incorrecto:**

1. Conservar el error y comparar compañía/almacén con la tabla anterior.
2. Verificar por nombre de campo, sin mostrar valores secretos, que existe el
   Reader en `core-private.json`; usar el web `8000` con `Host: ccm-core.test`.
3. Contrastar precio/existencia mediante la API nativa, sin escrituras ni SQL
   correctivo. No reutilizar el almacén de las ventas CO/TAX: aquí se consulta
   el almacén HTTP, cuya existencia esperada es `5`.
4. Registrar FAIL si difiere el snapshot retenido. No resembrar, editar flags,
   regenerar claves ni restaurar un dump para sustituir la evidencia original.
