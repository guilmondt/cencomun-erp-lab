# Suites oficiales Frappe / ERPNext 16.36.1

Se ejecutan runners, fuentes y fixtures oficiales, sin cambiar el oráculo LAB, pins o validadores. Este informe distingue descubrimiento, ejecución real y eventos JUnit. Los cuatro unitarios históricos de utilidades no son estas suites.

| Aplicación | Sitio del último intento registrado | Descubiertas | Ejecutadas (contador nativo) | Estado | Exit | Segundos | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- |
| frappe | ccm-upstream-frappe-final.test | 2326 | 2326 | FAIL | 1 | 966.617 | [frappe-latest.json](evidence/frappe-official/frappe-latest.json) |
| erpnext | ccm-upstream-erpnext-final.test | 3255 | 3255 | FAIL | 1 | 5062.373 | [erpnext-latest.json](evidence/frappe-official/erpnext-latest.json) |

El cierre exclusivo de la última pasada completa desde 9cbfbbd, su clasificación de causas y la conservación del runtime original están en [frappe-official-final-ci.md](frappe-official-final-ci.md). No se suman PASS modulares anteriores a los completos nuevos.

| Aplicación | Eventos PASS | FAIL | ERROR | SKIP | Total JUnit | Métodos descubiertos sin resultado |
| --- | --- | --- | --- | --- | --- | --- |
| frappe | 2220 | 9 | 47 | 50 | — (texto CI) | 0 |
| erpnext | 3251 | 0 | 4 | 0 | — (texto CI) | 0 |

**Los eventos JUnit no son el contador real de pruebas.** setUpClass/tearDownClass y subtests producen registros adicionales; SKIP no aprueba. Los intentos seriales guardan cada ID, excepción y traza redactada. El runner CI no emite JUnit: se usa su resumen `Tests: N`, con totales FAIL/ERROR, eventos verbose por método y cabeceras de fallos (ID/tipo de excepción, sin variables privadas). Un evento FAILED_EVENT no inventa un subtipo. En intentos interrumpidos los resultados no observados son desconocidos; no se convierten en suite aprobada.

## Intentos y repeticiones conservados

| App | Intento | Alcance | Contador nativo | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- |
| erpnext | 1 | CI, todos los módulos (un shard) | 3255 | FAIL | [erpnext-ci-attempt-1.json](evidence/frappe-official/erpnext-ci-attempt-1.json) |
| erpnext | 2 | CI, todos los módulos (un shard) | 3255 | FAIL | [erpnext-ci-attempt-2.json](evidence/frappe-official/erpnext-ci-attempt-2.json) |
| erpnext | 1 | all | desconocido | BLOCKED / evidencia no válida | [erpnext-full-attempt-1.json](evidence/frappe-official/erpnext-full-attempt-1.json) |
| erpnext | 2 | all | desconocido | BLOCKED | [erpnext-full-attempt-2.json](evidence/frappe-official/erpnext-full-attempt-2.json) |
| erpnext | 3 | all | 3255 | FAIL | [erpnext-full-attempt-3.json](evidence/frappe-official/erpnext-full-attempt-3.json) |
| erpnext | 1 | Secuencia CI acotada: erpnext.accounts.doctype.payment_entry.test_payment_entry, erpnext.accounts.doctype.payment_ledger_entry.test_payment_ledger_entry, erpnext.accounts.doctype.payment_order.test_payment_order, erpnext.accounts.doctype.payment_reconciliation.test_payment_reconciliation, erpnext.accounts.doctype.payment_request.test_payment_request | 126 | PASS | [erpnext-sequence-test_payment_request-attempt-1.json](evidence/frappe-official/erpnext-sequence-test_payment_request-attempt-1.json) |
| erpnext | 1 | erpnext.controllers.tests.test_accounts_controller / métodos: test_61_payment_entry_against_journal_for_payable_accounts, test_71_advance_payment_against_purchase_invoice_in_foreign_currency, test_difference_posting_date_in_pi_and_si | 3 | PASS | [erpnext-test_accounts_controller-selected-attempt-1.json](evidence/frappe-official/erpnext-test_accounts_controller-selected-attempt-1.json) |
| erpnext | 1 | erpnext.manufacturing.doctype.bom.test_bom / métodos: test_update_bom_cost_in_all_boms | 1 | FAIL | [erpnext-test_bom-selected-attempt-1.json](evidence/frappe-official/erpnext-test_bom-selected-attempt-1.json) |
| erpnext | 2 | erpnext.manufacturing.doctype.bom.test_bom / métodos: test_update_bom_cost_in_all_boms | 1 | FAIL | [erpnext-test_bom-selected-attempt-2.json](evidence/frappe-official/erpnext-test_bom-selected-attempt-2.json) |
| erpnext | 3 | erpnext.manufacturing.doctype.bom.test_bom / métodos: test_update_bom_cost_in_all_boms | 1 | PASS | [erpnext-test_bom-selected-attempt-3.json](evidence/frappe-official/erpnext-test_bom-selected-attempt-3.json) |
| erpnext | 1 | erpnext.manufacturing.doctype.job_card.test_job_card / métodos: test_completion_qty_capped_by_previous_operation, test_job_card_proccess_qty_and_completed_qty, test_op_cost_calculation, test_operating_cost_with_overproduction, test_process_loss_booked_once_across_partial_entries | 5 | PASS | [erpnext-test_job_card-selected-attempt-1.json](evidence/frappe-official/erpnext-test_job_card-selected-attempt-1.json) |
| erpnext | 1 | erpnext.accounts.doctype.payment_request.test_payment_request | 22 | FAIL | [erpnext-test_payment_request-attempt-1.json](evidence/frappe-official/erpnext-test_payment_request-attempt-1.json) |
| erpnext | 2 | erpnext.accounts.doctype.payment_request.test_payment_request | 22 | FAIL | [erpnext-test_payment_request-attempt-2.json](evidence/frappe-official/erpnext-test_payment_request-attempt-2.json) |
| erpnext | 3 | erpnext.accounts.doctype.payment_request.test_payment_request | 22 | FAIL | [erpnext-test_payment_request-attempt-3.json](evidence/frappe-official/erpnext-test_payment_request-attempt-3.json) |
| erpnext | 4 | erpnext.accounts.doctype.payment_request.test_payment_request | 22 | FAIL | [erpnext-test_payment_request-attempt-4.json](evidence/frappe-official/erpnext-test_payment_request-attempt-4.json) |
| erpnext | 5 | erpnext.accounts.doctype.payment_request.test_payment_request | 22 | PASS | [erpnext-test_payment_request-attempt-5.json](evidence/frappe-official/erpnext-test_payment_request-attempt-5.json) |
| erpnext | 1 | erpnext.manufacturing.doctype.routing.test_routing / métodos: test_sequence_id | 1 | PASS | [erpnext-test_routing-selected-attempt-1.json](evidence/frappe-official/erpnext-test_routing-selected-attempt-1.json) |
| erpnext | 1 | erpnext.stock.doctype.stock_entry.test_stock_entry / métodos: test_work_order_manufacture_with_material_consumption | 1 | FAIL | [erpnext-test_stock_entry-selected-attempt-1.json](evidence/frappe-official/erpnext-test_stock_entry-selected-attempt-1.json) |
| erpnext | 2 | erpnext.stock.doctype.stock_entry.test_stock_entry / métodos: test_work_order_manufacture_with_material_consumption | 1 | PASS | [erpnext-test_stock_entry-selected-attempt-2.json](evidence/frappe-official/erpnext-test_stock_entry-selected-attempt-2.json) |
| erpnext | 1 | erpnext.manufacturing.doctype.work_order.test_work_order / métodos: test_operations_time_planning_calculation | 1 | PASS | [erpnext-test_work_order-selected-attempt-1.json](evidence/frappe-official/erpnext-test_work_order-selected-attempt-1.json) |
| frappe | 1 | CI, todos los módulos (un shard) | 2326 | FAIL | [frappe-ci-attempt-1.json](evidence/frappe-official/frappe-ci-attempt-1.json) |
| frappe | 1 | all | 32 | BLOCKED | [frappe-full-attempt-1.json](evidence/frappe-official/frappe-full-attempt-1.json) |
| frappe | 2 | all | 2275 | FAIL | [frappe-full-attempt-2.json](evidence/frappe-official/frappe-full-attempt-2.json) |
| frappe | 3 | all | 32 | BLOCKED | [frappe-full-attempt-3.json](evidence/frappe-official/frappe-full-attempt-3.json) |
| frappe | 4 | all | 2319 | FAIL | [frappe-full-attempt-4.json](evidence/frappe-official/frappe-full-attempt-4.json) |
| frappe | 1 | integration | 333 | FAIL | [frappe-full-integration-attempt-1.json](evidence/frappe-official/frappe-full-integration-attempt-1.json) |
| frappe | 1 | old-frappe-test-class-category | 0 | BLOCKED | [frappe-full-old-frappe-test-class-category-attempt-1.json](evidence/frappe-official/frappe-full-old-frappe-test-class-category-attempt-1.json) |
| frappe | 1 | Secuencia CI acotada: frappe.tests.test_auth | desconocido | BLOCKED | [frappe-sequence-test_auth-attempt-1.json](evidence/frappe-official/frappe-sequence-test_auth-attempt-1.json) |
| frappe | 2 | Secuencia CI acotada: frappe.tests.test_auth | 17 | PASS | [frappe-sequence-test_auth-attempt-2.json](evidence/frappe-official/frappe-sequence-test_auth-attempt-2.json) |
| frappe | 1 | frappe.tests.test_auth | 1 | BLOCKED | [frappe-test_auth-attempt-1.json](evidence/frappe-official/frappe-test_auth-attempt-1.json) |
| frappe | 1 | frappe.core.doctype.rq_job.test_rq_job | 0 | BLOCKED | [frappe-test_rq_job-attempt-1.json](evidence/frappe-official/frappe-test_rq_job-attempt-1.json) |
| frappe | 2 | frappe.core.doctype.rq_job.test_rq_job | 0 | BLOCKED | [frappe-test_rq_job-attempt-2.json](evidence/frappe-official/frappe-test_rq_job-attempt-2.json) |
| frappe | 3 | frappe.core.doctype.rq_job.test_rq_job | 13 | PASS | [frappe-test_rq_job-attempt-3.json](evidence/frappe-official/frappe-test_rq_job-attempt-3.json) |
| frappe | 1 | frappe.tests.test_timeline | 7 | PASS | [frappe-test_timeline-attempt-1.json](evidence/frappe-official/frappe-test_timeline-attempt-1.json) |

Cada intento conserva su alcance. El módulo timeline ejecutó siete legacy PASS tras recrear copias limpias en los mismos SHAs; no convierte el comando Frappe completo en PASS. La selección directa de su categoría fue rechazada por la CLI (cero tests). La repetición auth antigua completó una unitaria y quedó BLOCKED durante preparación. La reproducción posterior en sitio limpio usa la CI nativa; sus resultados y el diagnóstico de fixtures están en [la investigación acotada](frappe-official-preparation-investigation.md). Ninguna repetición modular convierte estos completos FAIL en PASS.

## Comandos ejecutados

- `/workspace/.local/frappe-integral/bench-tools/bin/bench --site ccm-upstream-frappe-final.test run-parallel-tests --app frappe --total-builds 1 --build-number 1`
- `/workspace/.local/frappe-integral/bench-tools/bin/bench --site ccm-upstream-erpnext-final.test run-parallel-tests --app erpnext --total-builds 1 --build-number 1 --lightmode`

Preparación, repetición por categoría/módulo y diagnóstico paso a paso: [README](../scripts/official-tests/README.md). Discovery ejecuta cero pruebas. El bootstrap ERPNext de CI también ejecuta cero: carga fixtures oficiales; su éxito no es resultado de suite. Frappe usa su hook oficial antes del comando completo. Los servidores HTTP pertenecen a los sitios explícitos, sin cambiar el proxy baseline.

## Colisión Standard Buying

Resuelta usando sitios creados vacíos sin Cencomun y bootstrap oficial ERPNext. [erpnext-preparation.json](evidence/frappe-official/erpnext-preparation.json) comprueba `Standard Buying` en INR (buying=1, selling=0), ausencia de P001/flag LAB y aplicaciones oficiales. No se renombra ni altera la lista del oráculo LAB. El Bench copiado aísla también los tests que cambian configuración global o generan archivos en las fuentes de prueba; el runtime y fuentes originales Cencomun no se modifican.

## Fallos y limitaciones

`pip check` devuelve 1: requests 2.34.2 y oauthlib 4.0.0, ya presentes en el lock inicial, no satisfacen los rangos declarados por Frappe. Se conservan los pins; cualquier corrección de esos pins necesita una propuesta separada. No se atribuye todo fallo de suite a esas incompatibilidades sin demostrar la relación.

### frappe: excepciones observadas

| Excepción | Eventos fallidos |
| --- | --- |
| AssertionError | 7 |
| AttributeError | 1 |
| Error | 1 |
| Exception | 10 |
| IndexError | 1 |
| PermissionError | 1 |
| frappe.exceptions.AuthenticationError | 2 |
| frappe.exceptions.CommandFailedError | 1 |
| frappe.exceptions.ValidationError | 2 |
| requests.exceptions.ConnectionError | 30 |
### erpnext: excepciones observadas

| Excepción | Eventos fallidos |
| --- | --- |
| frappe.exceptions.ValidationError | 4 |

Los intentos anteriores se conservan en [summary.json](evidence/frappe-official/summary.json). El primer ERPNext tuvo una colisión de nombres de evidencia entre procesos concurrentes: ambos se interrumpieron, sus conteos quedaron desconocidos/no válidos y se repitió con reserva exclusiva de nombres. Los tests del harness verifican cero-test, categorías, subtests/fixtures, concurrencia, recuperación incompleta, assets, redacción y conservación de archivos generados; no son tests oficiales. El intento ERPNext 2 se conserva incompleto tras perder acceso al ejecutor; [informe de recuperación](frappe-executor-recovery.md).

Diagnóstico de causas comprobadas, hipótesis pendientes y pasos de repetición: [frappe-official-diagnostics.md](frappe-official-diagnostics.md). Payments solo está en el Bench oficial copiado, con SHA version-16 y siete SDKs fijados; [preparación](evidence/frappe-official/payments-preparation.json). ERPNext CI usa bootstrap previo y lightmode, como su workflow oficial; el runner restablece Administrator antes de cada módulo por su propio código. No se cambian roles ni validadores.

No se ejecutan UI/Cypress, PostgreSQL, SQLite ni migraciones a otra versión. No se modifican validaciones para aprobar. Para cada excepción nativa: localizar ID/traza, identificar causa comprobada, corregir únicamente preparación autorizada, repetir módulo y conservar el fallo anterior; seguir el diagnóstico del README. Un FAIL o UNRUN nunca se convierte automáticamente en PASS por una prueba de otro alcance.

## Core Test, patch y entorno guardado

La regresión Cencomun posterior a preparación se publica separadamente en [frappe-core-test.md](frappe-core-test.md). Las suites oficiales de baseline no cuentan como regresión después de patch. Los tags oficiales de ambos proyectos siguen ofreciendo solo v16.36.0/v16.36.1: criterio 13 BLOCKED, seis escenarios UNRUN. No se cambia minor.

La comprobación del entorno guardado tiene resultado **PASS externo**, aportado por el coordinador desde una tarea cloud distinta; no fue reejecutada por este agente. [Evidencia exacta, atribución y límites](frappe-cloud-restoration.md). [Procedimiento reproducible](../docs/FRAPPE_CLOUD_RESTORE_CHECK.md): snapshot esperado `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`, servicios retenidos y consulta autenticada P001, USD 50.00, stock 5 en almacén HTTP, cotejados con APIs nativas. Esta tarea no repite Guardar/Publicar; otro sitio en esta máquina no acredita restauración cloud.
