# Suites oficiales Frappe / ERPNext 16.36.1

Se ejecutan runners, fuentes y fixtures oficiales, sin cambiar el oráculo LAB, pins o validadores. Este informe distingue descubrimiento, ejecución real y eventos JUnit. Los cuatro unitarios históricos de utilidades no son estas suites.

| Aplicación | Sitio del último intento registrado | Descubiertas | Ejecutadas (Ran N) | Estado | Exit | Segundos | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- |
| frappe | ccm-upstream-frappe.test | 2326 | 2275 | FAIL | 1 | 856.902 | [frappe-latest.json](evidence/frappe-official/frappe-latest.json) |
| erpnext | ccm-upstream-erpnext.test | 3255 | desconocidas | BLOCKED | — | — | [erpnext-latest.json](evidence/frappe-official/erpnext-latest.json) |

| Aplicación | Eventos PASS | FAIL | ERROR | SKIP | Total JUnit | Métodos descubiertos sin resultado |
| --- | --- | --- | --- | --- | --- | --- |
| frappe | 2006 | 10 | 212 | 51 | 2279 | 51 |
| erpnext | 0 | 0 | 0 | 0 | 0 | 3255 |

**Los eventos JUnit no son el contador real de pruebas.** setUpClass/tearDownClass y subtests producen registros adicionales; SKIP no aprueba. Los JSON guardan cada ID, excepción y traza redactada; en intentos interrumpidos los resultados no observados son desconocidos. Un comando interrumpido no se convierte en suite aprobada.

## Comandos ejecutados

- `bench --site ccm-upstream-frappe.test run-tests --app frappe --junit-xml-output /workspace/.local/frappe-integral/official-tests/frappe-full-attempt-2.xml`
- `bench --site ccm-upstream-erpnext.test run-tests --app erpnext --junit-xml-output /workspace/.local/frappe-integral/official-tests/erpnext-full-attempt-2.xml`

**erpnext: intento interrumpido, BLOCKED.** No existe resumen final. Los resúmenes de categorías completadas son [2]; no son el conteo completo. Se conserva log/XML privados y no se inventan resultados.


Preparación, repetición por categoría/módulo y diagnóstico paso a paso: [README](../scripts/official-tests/README.md). Discovery ejecuta cero pruebas. El bootstrap ERPNext de CI también ejecuta cero: carga fixtures oficiales; su éxito no es resultado de suite. Frappe usa su hook oficial antes del comando completo. Los servidores HTTP pertenecen a los sitios explícitos, sin cambiar el proxy baseline.

## Colisión Standard Buying

Resuelta usando sitios creados vacíos sin Cencomun y bootstrap oficial ERPNext. [erpnext-preparation.json](evidence/frappe-official/erpnext-preparation.json) comprueba `Standard Buying` en INR (buying=1, selling=0), ausencia de P001/flag LAB y aplicaciones oficiales. No se renombra ni altera la lista del oráculo LAB. El Bench copiado aísla también los tests que cambian configuración global o generan archivos en las fuentes de prueba; el runtime y fuentes originales Cencomun no se modifican.

## Fallos y limitaciones

`pip check` devuelve 1: requests 2.34.2 y oauthlib 4.0.0, ya presentes en el lock inicial, no satisfacen los rangos declarados por Frappe. Se conservan los pins; cualquier corrección de esos pins necesita una propuesta separada. No se atribuye todo fallo de suite a esas incompatibilidades sin demostrar la relación.

### frappe: excepciones observadas

| Excepción | Eventos fallidos |
| --- | --- |
| AssertionError | 10 |
| AttributeError | 5 |
| ConnectionError | 2 |
| DuplicateEntryError | 3 |
| Exception | 15 |
| FileNotFoundError | 2 |
| IndexError | 1 |
| LinkValidationError | 1 |
| OSError | 180 |
| TypeError | 1 |
| ValidationError | 2 |
### erpnext: excepciones observadas

| Excepción | Eventos fallidos |
| --- | --- |

Los intentos anteriores se conservan en [summary.json](evidence/frappe-official/summary.json). El primer ERPNext tuvo una colisión de nombres de evidencia entre procesos concurrentes: ambos se interrumpieron, sus conteos quedaron desconocidos/no válidos y se repitió con reserva exclusiva de nombres. Diez tests del harness verifican cero-test, categorías, subtests/fixtures, concurrencia, recuperación incompleta, assets y redacción; no son tests oficiales. El intento ERPNext 2 se conserva incompleto tras perder acceso al ejecutor; [informe de recuperación](frappe-executor-recovery.md).

No se ejecutan UI/Cypress, PostgreSQL, SQLite ni migraciones a otra versión. No se modifican validaciones para aprobar. Para cada excepción nativa: localizar ID/traza, identificar causa comprobada, corregir únicamente preparación autorizada, repetir módulo y conservar el fallo anterior; seguir el diagnóstico del README. Un FAIL o UNRUN nunca se convierte automáticamente en PASS por una prueba de otro alcance.

## Core Test, patch y entorno guardado

La regresión Cencomun posterior a preparación se publica separadamente en [frappe-core-test.md](frappe-core-test.md). Las suites oficiales de baseline no cuentan como regresión después de patch. Los tags oficiales de ambos proyectos siguen ofreciendo solo v16.36.0/v16.36.1: criterio 13 BLOCKED, seis escenarios UNRUN. No se cambia minor.

La comprobación del entorno guardado tiene resultado **PASS externo**, aportado por el coordinador desde una tarea cloud distinta; no fue reejecutada por este agente. [Evidencia exacta, atribución y límites](frappe-cloud-restoration.md). [Procedimiento reproducible](../docs/FRAPPE_CLOUD_RESTORE_CHECK.md): snapshot esperado `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`, servicios retenidos y consulta autenticada P001, USD 50.00, stock 5 en almacén HTTP, cotejados con APIs nativas. Esta tarea no repite Guardar/Publicar; otro sitio en esta máquina no acredita restauración cloud.
