# Suites oficiales de servidor: Frappe / ERPNext 16.36.1

Este harness llama los runners y fixtures oficiales sin modificar fuentes ni
validaciones. Los resultados detallados, cantidades y fallos están en
`reports/frappe-official-suites.md` y `reports/evidence/frappe-official/`.
Las pruebas UI/Cypress, PostgreSQL, SQLite y migraciones entre versiones no
forman parte de esta ejecución de servidor sobre MariaDB fijada.

## Última pasada completa autorizada desde 9cbfbbd

El usuario autorizó una sola nueva pasada completa por aplicación tras las
correcciones demostradas. Plan: `tasks/102-frappe-official-final-ci.md`;
resultados exclusivos: `reports/frappe-official-final-ci.md`. Los anteriores
FAIL/incompletos se conservan, sin sumar PASS modulares. Criterio 13 BLOCKED.

1. Comprobar lock/runners, registrar integridad original con `integrity.py before`
   y conservar/copiar fuentes oficiales limpias con
   `isolate_bench.py --refresh-test-sources`, con el worker oficial detenido.
   No tocar el Bench original. Los sitios `*-final.test` son nuevos sitios
   oficiales locales; no acreditan restauración cloud.
2. Usar `set -e`, el env/PATH indicado abajo y el guard offline en preparación,
   discovery y servidores/worker. Preparar Frappe con `prepare.py frappe --final`;
   verificar `inspect_site.py frappe --final` y
   `discover.py frappe --final`. Este discovery registra IDs pero ejecuta cero.
3. Arrancar SMTP y worker exclusivos. Ejecutar **una vez** Frappe completo:
   `run.py frappe --site ccm-upstream-frappe-final.test --ci-parallel --offline --observe`.
   Esperar al resultado antes de la siguiente aplicación. El workflow Frappe
   fijado también utiliza run-parallel-tests, sin lightmode, con sus hooks.
4. Detener el worker, conservar cualquier archivo generado y recrear fuentes
   copiadas limpias en los mismos SHAs. Preparar ERPNext:
   `prepare.py erpnext --final --official-fx-fixtures`. Las seis tasas exactas se
   insertan por Document API antes de importar tests/bootstrap; comprobar BOM
   cero antes/después y mapa nativo. Inspección/discovery `erpnext --final`.
5. Reiniciar exclusivamente el worker oficial y ejecutar **una vez** ERPNext:
   `run.py erpnext --site ccm-upstream-erpnext-final.test --ci-parallel --offline --observe`.
   El lightmode posterior al bootstrap es nativo de su CI. Un shard incluye
   todos los módulos en ambos casos; no añadir filtros de casos fallidos.
6. Publicar conteos nativos/IDs/skips/ausencias y diagnóstico permitido, no los
   logs/variables crudos. Si falta resumen, el total queda desconocido. Conservar
   cada interrupción de preparación/bootstrap y todos los intentos históricos.
7. Detener servicios exclusivos, ejecutar `integrity.py after` y la lectura
   autenticada `scripts/core-test/readiness.py`. Si el runtime original cambia,
   investigar y repetir Core; si no, conservar el alcance de los 34 grupos
   previos, sin llamarlos una nueva regresión. HOME/red/patch no se sortean.

Para registrar el cierre en **este mismo ejecutor**, después de comprobar cero
runners activos:

```bash
"$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/integrity.py after
"$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/core-test/readiness.py
"$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/closure.py
```

`closure.py` consulta los diez sitios oficiales por APIs nativas y acredita que
sus directorios/DB siguen disponibles; compara los 48 archivos históricos con
el manifest privado previo y los 32 logs privados que conservan un SHA en su
resultado nativo. No publica esos logs. Compara los 17 archivos compartidos con fcf690d y pins/
recibo cloud con sus hashes conservados. Consulta como lector autenticado P001,
precio USD 50.00 y stock 5 por adaptador y API nativa. No cambia datos ni ejecuta
los 34 grupos otra vez. Publica solo `final-closure.json`, con creación exclusiva.
Necesita los manifests/credenciales privados retenidos y un Bench activo; no es
un procedimiento para acreditar otra restauración cloud.

Publicar cada inventario/diagnóstico una vez cuando exista su resultado final:
`final_inventory.py erpnext` y la función `final_diagnostics.publish` con el JSON
del intento correspondiente. Esos archivos usan creación exclusiva para
conservar derivaciones anteriores; no borrar un resultado para repetirlo. Usar
`publish_observations.py` y `publish.py` solo al concluir ambos completos, y
verificar después que los 48 hashes históricos permanezcan idénticos. Si un
runner termina sin resumen, no sustituir su contador por discovery/eventos.

El cierre usa el cwd nativo `sites/`: Frappe resuelve las rutas de logger de
sitio desde ahí. Ante `FileNotFoundError` en `<site>/logs/database.log`, conservar
el intento, comprobar cwd/path y comparar con `inspect_site.py`; no crear un
árbol alternativo. `sites_workdir` restaura el cwd al terminar y un control con
el handler nativo cubre la regresión. No afecta ni obliga a repetir las suites.

Una interpretación diagnóstica nueva conserva la anterior: por ejemplo,
`final_diagnostics.publish(OUT / 'erpnext-ci-attempt-2.json', revision=2)` crea
un JSON v2 exclusivo y señala que no repitió la ejecución. La clasificación
de tasa faltante exige evidencia nativa ligada a ese par/PID; un rechazo de
red en otro momento no basta para atribuir un fallo contable.

`set-config -- admin_password VALUE` mantiene como argumento una credencial
local que empiece por guion. No imprimirla ni regenerarla para sortear el parser;
conservar el log del fallo de preparación y continuarlo con el separador nativo.

## Investigación acotada desde 8158

Los completos conservados siguen FAIL y el criterio 13 BLOCKED. Véase
`reports/frappe-official-preparation-investigation.md`. No repetir completos
sin corrección o hipótesis concreta, ni repetir restauración cloud.

1. El helper Payments ahora se llama **prepare_payments.py**: el nombre antiguo
   ocultaba al paquete oficial al importar Frappe desde otros helpers. Ejecutar
   `prove_payments_shadow.py` una vez conserva la prueba sin sitio/DB/caché/red;
   si su evidencia ya existe, conservarla. `module_preflight.py` comprueba el
   origen del paquete y listas no vacías; solo reconstruye `db_name|app_modules`
   ante diferencias demostradas. Nunca purgar Redis completo.
2. Usar un sitio nuevo marcado sin borrar el anterior. Para autenticación:
   `prepare.py frappe --diagnostic`. Para aislar el orden de fixtures ERPNext:
   `prepare.py erpnext --fixture-order --official-fx-fixtures`. Estos slots son
   sitios locales de diagnóstico, no comprobaciones de restauración cloud.
   No reejecutar su preparación si la evidencia FX con ese nombre existe:
   conservar el sitio y comprobar el estado antes de continuar.
3. Prohibir transportes externos durante preparación y reproducción:

   ```bash
   cd /workspace/cencomun-erp-lab
   source scripts/frappe-integral/env.sh
   export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
   export CCM_OFFICIAL_OFFLINE=1
   export PYTHONPATH="$PWD/scripts/official-tests/observer"
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/prepare.py erpnext --fixture-order --official-fx-fixtures
   ```

   El guard permite loopback y resolver el literal de bind nativo. Rechaza
   DNS/conexiones externas y HTTP externo antes del adapter; no devuelve una
   respuesta ni tasa ficticia. No cambia permisos de red, TLS o proxy. Un
   rechazo offline observado se distingue del ProxyError histórico real.
4. Las tasas se leen de los seis registros JSON oficiales exactos, sin cambiar
   fechas/monedas/valores/banderas. Antes del bootstrap se usa
   `frappe.get_doc(record).insert()` con validación nativa: el generador de
   test records importa `ERPNextTestSuite` y dispara demasiado pronto los
   fixtures maestros. Conservar conteos BOM antes/después de cargar FX. No
   modificar `allow_stale` ni agregar tasas LAB o cotizaciones externas.
5. Ejecutar el módulo o métodos requeridos, con procesos nuevos y mismo lock:

   ```bash
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe \
     --site ccm-upstream-frappe-diagnostic.test --sequence frappe.tests.test_auth --offline --observe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py erpnext \
     --site ccm-upstream-erpnext-fixture-order.test \
     --module erpnext.manufacturing.doctype.bom.test_bom \
     --test test_update_bom_cost_in_all_boms --offline --observe
   ```

   `--sequence` utiliza el ParallelTestRunner nativo para módulos seleccionados
   en un proceso; conserva sus hooks, reset de usuario y TestResult. No es una
   suite completa. `--test` usa el selector nativo y se etiqueta como métodos
   seleccionados; no acredita el módulo entero. El observador no reemplaza
   funciones de negocio/validadores/fixtures ni cambia sus resultados.
6. Publicar solo JSON permitidos con `publish_observations.py`, luego
   `publish.py`; ambos distinguen streams observacionales de resultados
   nativos. Cada intento reserva archivos exclusivos. Preparación tampoco
   sobrescribe logs de etapas anteriores. Ante fallo, conservar el intento y
   repetir únicamente después de corregir o formular una hipótesis verificable.
7. Verificar controles del harness con el venv oficial:
   `python -m unittest discover -s scripts/official-tests -p 'test_*.py'`.
   No contarlos como tests Frappe/ERPNext o como criterio 13.

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
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/prepare_payments.py
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/prepare.py erpnext --fresh
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/inspect_site.py frappe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/inspect_site.py erpnext --fresh
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/discover.py frappe
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/discover.py erpnext
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/infrastructure.py
   export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$PATH"
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/smtp.py start
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/worker.py start
   ```

   Sitios nuevos marcados: `ccm-upstream-frappe.test` (solo Frappe),
   `ccm-upstream-erpnext-fresh.test` (Frappe+Payments+ERPNext), DBs `ccm_upstream_frappe` y
   `ccm_upstream_erpnext_fresh`. El intento anterior sin Payments permanece
   conservado en `ccm-upstream-erpnext.test`. `prepare.py` rechaza sitios/Bench preexistentes sin
   marcador y nunca los elimina/restaura. El bootstrap oficial ERPNext usa
   `run-tests --lightmode --module erpnext.tests.bootstrap_test_data`, igual al
   workflow fijado; sus cero tests **solo preparan fixtures**. Frappe ejecuta
   su hook oficial `frappe.utils.install.before_tests` antes de categorías.

   ERPNext CI instala Payments. Su `develop` ahora exige Frappe 17 y no es
   compatible: se usa únicamente el commit oficial version-16
   `cca07d9f9392e2ea0e521c5975151db9e4b6c321`, Frappe >=16,<17, Python >=3.14.
   Los siete SDKs están fijados con hashes en `official-payments.lock.txt`;
   `prepare_payments.py` rechaza un runner/worker activo y comprueba que ninguna versión
   previamente instalada cambió. Solo modifica el venv del Bench oficial
   copiado; Payments no se instala en sitios ni venv Cencomun. Los sources
   originales y `versions.lock` siguen intactos. No se usa `bench get-app`
   sobre una rama flotante ni se configuran gateways o credenciales reales.

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
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py erpnext --site ccm-upstream-erpnext-fresh.test --ci-parallel
   ```

   Cada llamada inicia y termina su propio servidor oficial `bench --site
   <sitio> serve --port <8002|8005> --noreload` en modo CI. El sitio está fijado
   explícitamente, sin modificar el proxy baseline. Comando central:
   `bench --site <sitio> run-tests --app <app> --junit-xml-output <archivo privado>`.
   No ejecutar dos suites simultáneas sobre este Bench: comparten fixtures.
   Un lock exclusivo y la revisión de runners nativos activos rechazan una
   segunda llamada, incluso si solicita otra aplicación o puerto. Se guardan
   metadatos privados de driver/runner antes de esperar su finalización.

   La repetición ERPNext usa el runner **nativo de su CI**:
   `bench --site ccm-upstream-erpnext-fresh.test run-parallel-tests --app erpnext
   --total-builds 1 --build-number 1 --lightmode`. Un único shard incluye todos
   los módulos. El bootstrap oficial se ejecuta previamente; no se debilitan
   validaciones. Ese runner restablece Administrator antes de cada módulo
   (`frappe/parallel_test_runner.py`), mientras que el runner serial previo
   deja pasar estado entre módulos y no prepara `unspecified-category`.
   Esto es comportamiento upstream; no se añaden roles ni bypasses.
   Sus resultados se publican como texto nativo con contador `Tests: N`, no
   como JUnit: conserva estados por método y totales FAIL/ERROR del resumen.
   Un evento marcado `FAILED_EVENT` no inventa un subtipo ni causa; trazas y
   variables locales quedan privadas. Sin resumen final, cantidad desconocida.
   El intento serial anterior sigue FAIL con su JUnit; no se suman ambos
   conteos como una ejecución ni se atribuyen todos sus errores a una sola causa.

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
   Para un intento CI interrumpido, pasar su basename real (por ejemplo
   `erpnext-ci-attempt-1`) solo si ya no hay runner y falta su JSON final.
   Recupera su comando/sitio y eventos verbose observados sin fabricar un
   conteo completo. En XML truncado conserva documentos completos anteriores
   y el hash del archivo crudo; no elimina ni sobrescribe el fragmento privado.
   Si `write_stdin` devuelve Unknown process id pero el driver/runner y su lock
   siguen vivos, no ejecutar recover ni otra suite: el registro de la sesión
   de herramienta puede haberse perdido. Observar log y JSON final por archivos.
   Para observar sin imprimir logs, variables ni credenciales:
   `python scripts/official-tests/progress.py erpnext-ci-attempt-1`.
   Sustituir el basename por el intento real. Mientras falta su JSON final,
   distingue eventos observados de contador nativo final y no aprueba la suite.
   Si `/proc/<pid>/cwd` devuelve PermissionError, el detector rechaza por
   precaución un comando nativo vivo; nunca interpreta esa denegación como
   proceso detenido. No solicitar otro sitio para sustituir el proceso activo.
5. Ejecutar los dieciocho tests del harness y regenerar el informe saneado:

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

**Fixtures generados por tests contaminan el descubrimiento siguiente:**

1. Consultar `git status --short` en `official-bench/apps/<app>` y distinguir
   archivos generados por tests de las fuentes originales, que deben seguir
   limpias. Por ejemplo, los tests de DocType exportan archivos de
   `VirtualDoctypeTest` y luego borran su registro; el bootstrap legacy puede
   intentar cargar ese archivo residual aunque el DocType ya no exista.
2. Esperar a que termine el runner activo. Detener solo el worker oficial;
   conservar logs, JUnit y resultados. No limpiar el Bench Cencomun ni modificar
   validaciones o fixtures compartidos.
3. Ejecutar `isolate_bench.py --refresh-test-sources`. Archiva íntegramente las
   copias de apps y archivos generados en el directorio privado `source-history`,
   y recrea únicamente esas copias desde los SHAs originales fijados. Rechaza
   runners/worker activos; no resetea sitios ni cambia versiones.
4. Repreparar el sitio con el hook/fixtures oficiales, revisar apps/Standard
   Buying, regenerar discovery y arrancar el worker oficial. Ejecutar el intento
   nuevo. Si la ejecución completa vuelve a producir el residuo antes de la
   categoría legacy, conservar el fallo del comando completo; repetir el
   módulo que contiene sus siete tests con copia limpia en otro proceso:
   `run.py frappe --site ccm-upstream-frappe-fresh.test --module frappe.tests.test_timeline`.
   La CLI upstream 16.36.1 solo admite categorías unit/integration/all; no
   admite seleccionar directamente el nombre interno de la categoría legacy.
   El intento de selección rechazado se conserva BLOCKED, cero tests, y no
   acredita fallo de esas siete pruebas.
5. Una categoría repetida no convierte en PASS una ejecución completa anterior
   ni suma sus conteos como si fueran una sola suite.

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
## Diagnósticos acotados posteriores al cierre completo

Desde 618c676 no se repiten suites completas. Véase
`reports/frappe-bounded-cause-diagnostics.md` y task 103 para comandos exactos,
sitios conservados, Journal Entry 0→1 y los 26 rechazos de Responses que el
clasificador había confundido con TCP. Los resultados completos siguen FAIL.

El guard respeta un interceptor oficial Responses sin passthrough; no instala
mocks, construye respuestas ni consulta proveedores. Toda petición externa sin
ese interceptor o con passthrough queda bloqueada, igual que DNS/sockets.
La telemetría conserva PID/start ticks, listener propio, sitio nativo servido,
URL sin userinfo/query/fragmento y exit antes/después de cleanup. No reinicia web
durante pruebas. Las aserciones de los mocks permanecen nativas.

`--cause` y `--cause-fixed` son slots ya usados, no instrucciones para borrar
sitios. `bounded_evidence.py` publica análisis derivado exclusivo y versiones de
corrección sin reescribir intentos; el discovery reutilizado se identifica como
tal. `integrity.py --label cause` y `closure.py --label cause` conservan el cierre
anterior. Para inicio reteniendo datos, usar `docs/FRAPPE_ENVIRONMENT_START.md`,
sin install/migrate/seed/restore ni suites automáticas.
# Auth/request: seguimiento acotado desde baad8f9

Leer `reports/frappe-auth-request-diagnostics.md` y task104 antes de reproducir.
Sin suites completas. Cero runners antes de cualquier preparación; conservar
sitios, claves, streams, reservas y resultados. Slots nuevos --auth-clean y
--auth-sequence aplican before_tests y configuración CI nativos. Solo en sitios
nuevos se reutiliza la credencial común retenida, respetando la prioridad de
install_db; no reset de usuario ni reconfiguración de un slot auth existente.
No repetir prepare sobre sitios históricos para reparar sus discrepancias.

Usar Python del Bench y PATH con official-tools/bin + core-tools/usr/bin.
run.py --offline --observe --auth-diagnostics registra configuración/contexto
del Local nativo, hash-match solo booleano, excepción de login y redirecciones
por status/ruta/nombres/presencia. Sin tokens/cookies/queries/valores sensibles.
Los resultados XML de estos intentos publican frames, no traceback crudo.
Para Performance --offline --auth-diagnostics, sin --observe: conservar guard,
HTTP saneado y umbral nativo, sin profiling/tracing del benchmark.

auth_probe.py SITE ETIQUETA hace solo SELECT/verificación passlib, sin llamar
check_password (puede rehash/limpiar trackers), reset, login o generate_keys.
auth_evidence.py deriva ocho intentos conservados/16 IDs y preserva todos los
JSON originales. auth_preservation.py comprueba los manifests privados previos,
prefijos de logs append-only, confs, fuentes y DBs; creación exclusiva de evidencia.
integrity.py after --label auth y closure.py --label auth realizan cierre sin
repetir Core/restauración. Los nuevos helpers también requieren guard offline
por env y PYTHONPATH observer al invocarlos directamente en un nuevo proceso.

## Cierre residual desde 678c5ef (sin completos)

Plan tasks/105 y reports/frappe-residual-failure-closure.md. Matriz exacta de56
fallos originales +2 Client adicionales: residual-final-matrix.json. Estados
completos FAIL inmutables; UNRUN posterior nunca aprueba un fallo original.

Nuevo slot único `prepare.py frappe --residual`, nativo CI, credencial común
retenida, sin reset de sitios anteriores. `run.py --module MODULO --test METODO`
selecciona solo métodos autorizados; comandos y cantidad real en cada resultado.
Nunca ejecutar test_set_password, test_existing_db_username o API-key para buscar
PASS: cambian credenciales. API-key solo lectura de lo ya retenido.

CCM_OFFICIAL_RESIDUAL_DIAG=1 junto a --observe permite capturar errno/frame/HOME
boolean del handler nativo backup y estado de recepción de email, sin mensajes,
valores secretos ni mail/dumps. En CPU/memoria omitir --observe; guard offline
siempre activo. El guard ya no importa requests anticipadamente en workers, pero
protege DNS/sockets desde startup e instala el mismo wrapper antes de terminar
el primer import requests. Los controles verifican primer import, mocks nativos
sin passthrough y rechazo externo previo al adapter.

`residual_schema.py` reproduce solo el subcaso original Automation Trigger Queue
con assertQueryCount(0), sin modificar el método aleatorio oficial ni contarlo
como una nueva ejecución completa de ese método. Conserva FAIL y dos ALTER.
HOME no se remapea. TCP sin db_socket rechazó acceso1130 antes del runner; la
config del sitio diagnóstico fue restaurada, no se alteran grants ni credenciales.

`residual_evidence.py`, `residual_preservation.py` y `closure.py --label residual`
son derivados/comprobaciones de solo lectura con creación exclusiva, sin tests
ni restauración. No borrar salidas existentes para repetirlos; nueva revisión
requiere otro nombre/versión y una hipótesis. Inicio de datos retenidos en
../../docs/FRAPPE_ENVIRONMENT_START.md; Guardar/Publicar queda con el coordinador.
