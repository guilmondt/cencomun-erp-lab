# Suites oficiales de servidor: Frappe / ERPNext 16.36.1

Este harness llama los runners y fixtures oficiales sin modificar fuentes ni
validaciones. Los resultados detallados, cantidades y fallos están en
`reports/frappe-official-suites.md` y `reports/evidence/frappe-official/`.
Las pruebas UI/Cypress, PostgreSQL, SQLite y migraciones entre versiones no
forman parte de esta ejecución de servidor sobre MariaDB fijada.

## Preparación y ejecución

1. Conservar `versions.lock` y el manifiesto compartido; comprobar rama
   `lab/frappe-baseline` y las fuentes upstream limpias. No utilizar sitios LAB
   para fixtures oficiales.
2. Arrancar únicamente los servicios locales retenidos e instalar los extras
   de tests fijados con constraints del runtime. El resolver no puede cambiar
   las versiones existentes:

   ```bash
   cd /workspace/cencomun-erp-lab
   source scripts/frappe-integral/env.sh
   export PATH="$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
   python scripts/frappe-integral/services.py start
   uv pip install --python "$CCM_FRAPPE_ROOT/bench/env/bin/python" \
     --constraint labs/frappe/integral/python-runtime.lock \
     --constraint labs/frappe/integral/core-test-dependencies.lock \
     --requirement labs/frappe/integral/official-test-dependencies.lock
   "$CCM_FRAPPE_ROOT/bench/env/bin/python" -m pip check
   ```

   `pip check` detecta dos incompatibilidades **preexistentes** del lock:
   requests 2.34.2 frente a `~=2.33.0`, y oauthlib 4.0.0 frente a `~=3.3.1`.
   No se corrigen cambiando pins en esta tarea. Los cinco extras añadidos no
   sustituyen esos paquetes. Un fallo de `pip check` se publica como limitación,
   no se convierte en PASS.
3. Crear un Bench privado de pruebas desde los SHAs fijados. Clona las fuentes
   oficiales localmente y copia el venv; solo cambia `.pth` en la copia para
   importar las fuentes copiadas. Copia también `public/dist` y sus manifests
   de los builds retenidos: Git no incluye esos archivos ignorados, que los
   tests de PDF necesitan. Repetir `isolate_bench.py` solo refresca estos assets
   en el Bench ya marcado; no resetea sitios ni fuentes. Cencomun no está en sus
   aplicaciones.

   ```bash
   "$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/official-tests/isolate_bench.py
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/prepare.py frappe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/prepare.py erpnext
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/inspect_site.py frappe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/inspect_site.py erpnext
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/discover.py frappe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/discover.py erpnext
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/infrastructure.py
   export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$PATH"
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/smtp.py start
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/worker.py start
   ```

   Sitios nuevos marcados: `ccm-upstream-frappe.test` (solo Frappe),
   `ccm-upstream-erpnext.test` (Frappe+ERPNext), DBs `ccm_upstream_frappe` y
   `ccm_upstream_erpnext`. `prepare.py` rechaza sitios/Bench preexistentes sin
   marcador y nunca los elimina/restaura. El bootstrap oficial ERPNext usa
   `run-tests --lightmode --module erpnext.tests.bootstrap_test_data`, igual al
   workflow fijado; sus cero tests **solo preparan fixtures**. Frappe ejecuta
   su hook oficial `frappe.utils.install.before_tests` antes de categorías.

   Los tests de comandos necesitan crear sitios temporales y pueden cambiar
   configuración global; las credenciales de bootstrap quedan solo en
   `official-bench/sites/common_site_config.json`. `allow_tests` y
   `server_script_enabled` se activan solo en estos sitios oficiales, conforme
   a la preparación CI oficial. Los sitios Cencomun y baseline no cambian.

   El worker de Cencomun no consume las colas de este Bench: el nombre de cola
   incluye la ruta del Bench. `worker.py start` debe ejecutarse **antes** de las
   suites. Si faltó, conservar el intento fallido y repetir los módulos RQ
   afectados con el worker activo; una repetición modular no convierte el
   comando completo anterior en PASS. Al terminar: `worker.py stop`.

   `infrastructure.py` verifica SHA256 antes de extraer wkhtmltopdf con Qt
   parcheado, libjpeg compatible y SMTP4dev, todos fijados en
   `official-system.lock.json`. Se instalan en userspace, sin cambiar los pins
   del runtime. `smtp.py` escucha solo en loopback, captura correo ficticio y
   no configura relay. `official-tools/bin` debe estar en PATH tanto para el
   runner como para el worker. Al terminar: `smtp.py stop`.
4. Ejecutar las aplicaciones completas, sin failfast, filtros de métodos,
   `--skip-test-records` ni sustituciones de validadores:

   ```bash
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py erpnext
   ```

   Cada llamada inicia y termina su propio servidor oficial `bench --site
   <sitio> serve --port <8002|8005> --noreload` en modo CI. El sitio está fijado
   explícitamente, sin modificar el proxy baseline. Comando central:
   `bench --site <sitio> run-tests --app <app> --junit-xml-output <archivo privado>`.
   No ejecutar dos suites simultáneas sobre este Bench: comparten fixtures.
   Un lock exclusivo y la revisión de runners nativos activos rechazan una
   segunda llamada, incluso si solicita otra aplicación o puerto. Se guardan
   metadatos privados de driver/runner antes de esperar su finalización.

   Una categoría o módulo independiente puede repetirse así, conservando el
   intento completo anterior:

   ```bash
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe --category integration
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe --module frappe.tests.test_utils
   ```

5. Revisar los JSON por intento. `actual_tests_run` procede de **Ran N tests**
   del runner; `discovered_test_count` no es un resultado. `junit_records` y
   sus contadores describen eventos: incluyen errores setUpClass/tearDownClass
   y subtests y por eso pueden superar N. Un exit 0 sin tests queda BLOCKED.
   SKIP no es PASS. Un fallo de preparación posterior a una categoría mantiene
   BLOCKED aunque esa categoría haya aprobado. Los intentos anteriores no se
   suman a la suite final ni sustituyen pruebas que quedaron sin ejecutar.

   Logs y JUnit completos quedan privados en
   `/workspace/.local/frappe-integral/official-tests`; solo se publican IDs,
   resultados, trazas redactadas y hashes. Antes de publicar, verificar que las
   credenciales generadas por tests de comandos también estén redactadas.
6. Repetir `bash scripts/core-test/run.sh` después de la preparación que añadió
   extras al venv compartido. Esta es la regresión Cencomun; no modifica su
   oráculo. Regenerar ambos informes, ejecutar `scripts/verify-repo.sh` y
   comprobar fuentes/pins/fixtures contra el commit de partida.

## Recuperación después de perder acceso al ejecutor

1. Recuperar **la misma tarea**, conservar `/workspace` y comprobar rama, HEAD
   y cambios antes de arrancar servicios. No hacer reset, limpieza ni crear
   otro sitio para sustituir el estado perdido.
2. Conservar copias privadas de cambios, logs, XML y estado; verificar hashes.
   Si MariaDB está detenido, se pueden conservar sus archivos retenidos, pero
   esa copia no acredita un backup lógico ni restauración validada. No subir
   credenciales, dumps, archivos privados o logs crudos a Git.
3. Revisar procesos activos y metadatos `*-running.json`. Si sigue activo un
   runner, observarlo; no repetir el comando. No inferir actividad por un PID
   antiguo ni por el archivo `.reserved`.
4. Si ya no hay runner y falta el JSON final, registrar la interrupción sin
   ejecutar pruebas. Para el intento ERPNext preservado en esta tarea:

   ```bash
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/recover.py erpnext erpnext-full-attempt-2
   ```

   Ejecutar solo una vez: rechaza sobrescribir un resultado existente y
   rechaza runners activos. Conserva `actual_tests_run=null`, BLOCKED, y los
   resúmenes de categorías terminadas por separado. Resultados no observados
   durante la interrupción son desconocidos; no se convierten en PASS/UNRUN
   mediante conteo de puntos, E o F.
5. Ejecutar los diez tests del harness y regenerar el informe saneado:

   ```bash
   python scripts/official-tests/test_results.py
   "$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/official-tests/publish.py
   ```

6. Después de guardar el checkpoint autorizado, arrancar preparación retenida
   según los pasos anteriores y repetir las suites pendientes con un **intento
   nuevo**, reservado exclusivamente. Nunca sobrescribir el intento
   interrumpido. Mantener la regresión Cencomun separada y evitar contender
   recursos durante su benchmark.

La recuperación observada, hashes y comandos están en
`reports/frappe-executor-recovery.md`. No volver a ejecutar la comprobación
cloud separada que el coordinador ya dio por terminada. Su JSON exacto,
atribución y límites se incorporaron en `reports/frappe-cloud-restoration.md`;
su PASS externo no modifica estas suites ni el criterio 13.

## Problemas y resolución

**DuplicateEntryError Standard Buying:**

1. Identificar el sitio del comando fallido y si contiene listas LAB/USD.
2. Conservar el intento; no borrar listas ni cambiar moneda/importes del LAB.
3. Usar el sitio upstream nuevo marcado, sin Cencomun; ejecutar el bootstrap
   oficial antes de la suite. Verificar `Standard Buying`: INR, buying 1,
   selling 0. `--skip-before-tests` no evita el bootstrap por importación.
4. Repetir la suite y registrar las cantidades reales. Cuatro unitarios o un
   bootstrap de cero tests no acreditan esa regresión.

**request=None durante setup wizard entre categorías:**

1. Conservar la traza del intento. En 16.36.1 se observó `auth.py`,
   `validate_ip_address`, al ejecutar el hook después de los unitarios.
2. Preparar el setup con el hook **oficial** antes del comando completo, como
   hace `prepare.py`; no modificar `auth.py`, simular login ni quitar validaciones.
3. Ejecutar el comando completo. Si una categoría sigue bloqueada, ejecutarla
   aparte en otro proceso y distinguir su alcance del comando completo.

**mariadb-dump ausente o creación de sitios pide credenciales:**

1. Confirmar `core-tools/usr/bin` en PATH y la versión del cliente 11.8.6
   previamente verificada. No sustituirlo por un cliente flotante.
2. Confirmar que se ejecuta desde `official-bench`, con bootstrap privado y
   db_host/port del servicio 3307. No imprimir passwords ni editar config global
   del Bench Cencomun.
3. Repetir la suite afectada; conservar fallos anteriores. Si pruebas requieren
   otra infraestructura o filesystem, documentar requisito y alcance bloqueado.

**Fallo nativo, dependencia incompatible o infraestructura CI ausente:**

1. Localizar el ID exacto y la excepción redactada en el JSON.
2. Separar causa comprobada de hipótesis; consultar el fixture y código del SHA
   fijado sin editarlo. No cambiar expectativas, validadores, permisos ni pins.
3. Ejecutar pruebas independientes o el módulo afectado después de una corrección
   de preparación autorizada. Registrar resultados anteriores y posteriores.
4. Para cambios de versiones, preparar un plan separado con SHAs, compatibilidad,
   backup, migración, regresión y rollback; esperar aprobación. Estas suites de
   baseline nunca se cuentan como las regresiones posteriores al patch.

**Backups oficiales fuera de workspace: filesystem HOME de solo lectura:**

1. Conservar el intento y comprobar la traza. Dos tests nativos usan
   `os.path.expanduser("~")` y escriben en `backups`, `db_path`, `files_path`,
   `private_path` y `conf_path` dentro de ese directorio.
2. En este ejecutor, preparar `/home/agent/backups` falló con
   `OSError: [Errno 30] Read-only file system`, incluso después de conceder
   acceso de escritura acotado a las cinco rutas. Ver
   `reports/evidence/frappe-official/home-backup-paths-preparation.json`.
   No cambiar HOME, expectativas ni fuentes upstream para ocultarlo.
3. Para resolverlo, ejecutar el módulo afectado en un ejecutor con esas rutas
   escribibles, mismas versiones fijadas, sitios vacíos y fixtures oficiales.
   Antes de lanzar pruebas, crear los cinco directorios con modo 0700 y
   verificar escritura de un archivo ficticio temporal y su eliminación.
   No copiar credenciales/dumps a Git ni sobrescribir archivos existentes.
4. Usar `run.py frappe --module frappe.commands.test_commands`, conservar el
   resultado anterior y distinguir la regresión modular de una suite completa.
   Los fallos nativos observados siguen siendo FAIL; la preparación bloqueada
   explica su límite, pero no aprueba los casos.

La verificación del entorno guardado se hace exclusivamente en **otra tarea
cloud** según `docs/FRAPPE_CLOUD_RESTORE_CHECK.md`; estos sitios/Bench privados
son preparación local y no restauración cloud.
