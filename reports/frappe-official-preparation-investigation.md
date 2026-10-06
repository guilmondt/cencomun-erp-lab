# Investigación acotada de preparación oficial

Continuación autorizada desde `8158b6803e4951a3fe66372578667f6cd8cab5a5`,
2026-10-05 America/Los_Angeles. Solo `lab/frappe-baseline`.

**Los completos siguen FAIL:** Frappe 2.319 tests (2.198 PASS, 24 FAIL,
46 ERROR, 51 SKIP); ERPNext CI 3.255 (3.188 PASS, 1 FAIL, 66 ERROR).
No se reejecutaron completos. El intento ERPNext interrumpido sigue incompleto.
**Criterio 13 BLOCKED; seis PATCH UNRUN.** No se inventa patch ni se cambian pins.

## Resultados acotados finales

| Línea | Resultado ejecutado | Evidencia / alcance |
| --- | --- | --- |
| Autenticación limpia, CI nativa | 17 tests, 17 PASS | [auth CI 2](evidence/frappe-official/frappe-sequence-test_auth-attempt-2.json); módulo completo seleccionado, no suite completa |
| Payment Request antes de corrección | 22 ERROR de módulo ausente; después 17 PASS/5 ERROR de FX | [intento 2](evidence/frappe-official/erpnext-test_payment_request-attempt-2.json), [intento 3](evidence/frappe-official/erpnext-test_payment_request-attempt-3.json); transporte externo prohibido |
| Payment Request con fixtures oficiales | 22 tests, 22 PASS | [intento 5](evidence/frappe-official/erpnext-test_payment_request-attempt-5.json), sin consultas externas |
| Payment Entry → Payment Ledger Entry → Payment Order → Payment Reconciliation → Payment Request | 126 tests, 126 PASS | [secuencia CI](evidence/frappe-official/erpnext-sequence-test_payment_request-attempt-1.json); mismos módulos precedentes, proceso nuevo y runner CI nativo |
| BOM 0 frente a 10 | Repetición 3: 1 test, PASS | [BOM 3](evidence/frappe-official/erpnext-test_bom-selected-attempt-3.json); intentos 1 y 2 FAIL conservados |
| Valor negativo | Repetición 2: 1 test, PASS | [stock 2](evidence/frappe-official/erpnext-test_stock_entry-selected-attempt-2.json); intento 1 ERROR conservado, validador intacto |
| Accounts Controller, tres divisiones por cero | 3 métodos, 3 PASS | [controller 1](evidence/frappe-official/erpnext-test_accounts_controller-selected-attempt-1.json) |
| Job Card, cinco divisiones por cero | 5 métodos, 5 PASS | [job card 1](evidence/frappe-official/erpnext-test_job_card-selected-attempt-1.json) |
| Routing y Work Order | Un método de cada módulo, ambos PASS | [routing 1](evidence/frappe-official/erpnext-test_routing-selected-attempt-1.json), [work order 1](evidence/frappe-official/erpnext-test_work_order-selected-attempt-1.json) |

Se verificaron de nuevo **los 14 IDs que daban ZeroDivisionError**: cuatro en
Payment Entry dentro de la secuencia contable, tres Accounts Controller, cinco
Job Card, uno Routing y uno Work Order. Todos tienen PASS en ejecuciones nuevas:
[matriz por ID, traza original y reproducción](evidence/frappe-official/zero-division-case-tracking.json).
No se suman módulos/métodos repetidos como si fueran una suite completa.

El [seguimiento de fallos originales](evidence/frappe-official/original-failure-followup.json)
solo acepta reproducciones observadas nuevas; un PASS antiguo de otro completo
no cuenta. De 67 eventos ERPNext originales, 44 tienen PASS nuevo y 23 no se
reprodujeron en esta continuación. De 70 eventos Frappe, ocho tienen PASS nuevo
y 62 no se reprodujeron. Son eventos, no conteos de una suite nueva. Los no
reproducidos no reciben PASS ni se convierten en bloqueos inevitables.

## Tasas: causa demostrada y límites de correlación

[Configuración y Error Log históricos](evidence/frappe-official/fx-historical-payment-request.json)
conserva `disabled=0`, Frankfurter v2 HTTPS, parámetro `date`, clave `rate`,
`allow_stale=1`, `stale_days=1`, pegged deshabilitado y cero registros Currency
Exchange. La captura no llamó al proveedor. El esquema fijado también define
`disabled=0`; no se modificó configuración para forzar un resultado.

En el intervalo UTC del módulo anterior hay **12 Error Log** con método
`Unable to fetch exchange rate`, cuya excepción terminal es `requests.exceptions.ProxyError`:
`Tunnel connection failed: 403 Forbidden` hacia Frankfurter USD/INR. Es rechazo
del túnel del proxy; **no demuestra una respuesta HTTP 403 del proveedor**.
`get_exchange_rate` captura la excepción y devuelve cero. No se atribuye a
configuración deshabilitada. No se cambian red, proxy, TLS, tasas ni validadores.

Los registros antiguos no contienen ID del test y JUnit tiene segundos enteros;
el intervalo demuestra la relación con el módulo, no una asignación inequívoca
de cada registro a un caso. La reproducción observada en proceso limpio conserva
los cinco mismos ERROR y enlaza sus Error Log nativos con el test activo:
[observaciones del intento 3](evidence/frappe-official/erpnext-test_payment_request-attempt-3-observations.json).
Sus excepciones de transporte son **rechazos locales del modo offline**, no
nuevas respuestas de Frankfurter. También registra configuración habilitada,
filas ausentes, llamadas/retornos nativos y ocho Error Log para los cinco ERROR.
Los otros cuatro logs corresponden a dos tests que terminan PASS; un Error Log
no se cuenta automáticamente como fallo del test.

| Caso que originalmente dio ERROR | Log nativo en reproducción offline |
| --- | --- |
| test_conversion_on_foreign_currency_accounts | Un log; USD→INR, tasa ausente |
| test_multiple_payment_entry_against_purchase_invoice | Dos logs; Source Exchange Rate obligatoria |
| test_payment_channels | Un log; USD→INR, tasa ausente |
| test_payment_entry_against_purchase_invoice | Dos logs; Source Exchange Rate obligatoria |
| test_status | Dos logs; Source Exchange Rate obligatoria |

La corrección de preparación carga **los seis registros exactos** de
`erpnext/setup/doctype/currency_exchange/test_records.json`, SHA y datos completos
en [la captura](evidence/frappe-official/fx-official-fixtures-loaded.json).
Se usa `frappe.tests.utils.make_test_records('Currency Exchange', commit=True)`.
Fechas 2016, monedas, importes y banderas Buying/Selling permanecen intactos.
Se conserva `allow_stale=1`, valor nativo ya existente; no se amplía la vigencia.
Los retornos observados en la secuencia son 1, 62.9 y 65.1; cero intentos HTTP
externos. No son tasas LAB ni propuestas de política comercial.

## Payments: colisión del helper demostrada

El archivo propio `scripts/official-tests/payments.py` precedía al paquete
instalado en `sys.path` de los helpers. `frappe.get_module_list('payments')`
resolvía ese archivo y devolvía `[]`, aunque `apps.txt` incluía Payments y el
`modules.txt` oficial contenía `Payments` y `Payment Gateways`. Frappe puede
almacenar ese mapa incompleto en la caché del sitio, que luego lee otro proceso.

[Prueba reproducible](evidence/frappe-official/payments-shadow-proof.json)
recrea únicamente el helper exacto de 8158 en un directorio temporal privado:
antes devuelve `[]`; tras renombrarlo `prepare_payments.py`, importa el paquete
oficial y devuelve los dos módulos. **No inicializa sitio, DB o caché ni hace
consultas externas.** Se comprueba el origen de cada app antes de aceptar el
mapa; una lista vacía deja de ser una preparación válida.

El [preflight inicial](evidence/frappe-official/payments-preflight-diagnostic.json)
comparó incorrectamente la lista vacía y emitió una afirmación insuficiente.
Se conserva la entrada y se enmienda como preparación inválida; no cuenta como
PASS. El [preflight posterior](evidence/frappe-official/payments-preflight-after-rename.json)
resuelve el paquete oficial. El helper puede reconstruir **solo**
`db_name|app_modules` si detecta diferencia; no purga Redis completo ni modifica
permisos. La secuencia CI conserva `payments` en cada snapshot antes/después de
los módulos y sus 126 resultados pasan. No se cambia el resolvedor upstream.

La comprobación final también detectó ese mapa incompleto en el sitio original
`ccm-upstream-erpnext-fresh.test`: faltaban únicamente Payments y Payment
Gateways. Se reconstruyó su clave nativa y el resolvedor verificó ambas entradas
([antes/después](evidence/frappe-official/payments-final-fresh.json)). En los tres
sitios diagnostic/fixture-audit/fixture-order el mapa ya era correcto y no se
aplicó reparación. Esta comprobación de preparación no reejecuta ni aprueba el
completo anterior, ni recalcula sus fixtures históricos.

## Autenticación: separar preparación de HTTP

El sitio `ccm-upstream-frappe-diagnostic.test` nació vacío; se ejecutó
`frappe.utils.install.before_tests` y después el `ParallelTestRunner` nativo,
incluidos su setup, hooks, decoradores, carga y resultado. No se omiten fixtures.
El servidor propio usa el sitio explícito y SMTP ficticio local sin relay.

Los 17 tests del módulo pasan. Las
[observaciones HTTP](evidence/frappe-official/frappe-sequence-test_auth-attempt-2-observations.json)
registran status/path, nunca cookies, contraseñas, cabeceras o query tokens.
Las respuestas 401/403/429 son parte de expectativas negativas que pasaron;
no se detectó `Domain forbidden`, y las sesiones observadas no usaron proxy.
No se cambió NO_PROXY. El antiguo `request=None` ocurrió preparando un sitio
usado con workflow residual; no ocurrió en el setup CI del sitio limpio.
La causa específica de los 403 del completo anterior **sigue desconocida**;
el PASS limpio no demuestra por sí solo una causa del fallo antiguo.

Un primer intento offline rechazó antes del runner la resolución del literal
de bind nativo `0.0.0.0`: cero tests, BLOCKED, conservado. El guard ahora permite
solo resolver ese literal local; mantiene prohibidos DNS/conexiones externos.
Werkzeug intenta identificar su interfaz mediante un UDP externo, que el guard
rechaza y Werkzeug maneja con su fallback nativo loopback. No se envía tráfico.

## BOM, valor negativo y divisiones por cero: orden demostrado

El sitio diagnostic creado con bootstrap antes de FX conserva BOM USD con
`conversion_rate=0` y `base_rate=0` aunque su valoración de Item 2 sea 100.
El test aislado sigue rechazando 0 frente a 10. Cargar FX después no recalcula
automáticamente una BOM ya persistida. Se preservó el FAIL, sin retocar la BOM.

El primer sitio fixture-audit también falló pese a solicitar FX antes del
bootstrap. La cadena fijada lo explica: `make_test_records` → import del test
Currency Exchange → import `ERPNextTestSuite` → `BootStrapTestData()` en el
módulo utils. Este efecto ejecuta los maestros antes de generar las tasas.

La preparación corregida crea `ccm-upstream-erpnext-fixture-order.test` vacío,
instala las mismas apps/SHAs, inserta los seis JSON oficiales con la API nativa
de documentos y luego ejecuta el bootstrap oficial. La
[captura previa](evidence/frappe-official/erpnext-fixture-order-fx-before-bootstrap.json)
demuestra **cero BOM antes y después de cargar FX**, seis tasas oficiales y
ningún proveedor consultado. El bootstrap posterior calcula sus campos nativos.
No se editan fixtures, estados, costos, tasas, fechas, validadores o expectativas.

Antes del test BOM 3, Item 2 tiene valoración 100 y base_rate 100; la aserción
nativa del incremento de 10 pasa. En stock 1, el observador conservó Basic Rate
**−100** de `_Test FG Item`, fila 3, rechazado por NonNegativeError. Con los
fixtures preparados en el orden correcto, el mismo método stock 2 pasa todas
sus aserciones, incluido costo FG = materias primas − secundario, sin desactivar
el validador. Sus
[observaciones](evidence/frappe-official/erpnext-test_stock_entry-selected-attempt-2-observations.json)
conservan filas y valores permitidos; no se publican documentos privados.

Las trazas originales de las 14 divisiones se conservan en la matriz. Siete
afectaban denominadores de cambio en pagos/Accounts Controller; otras siete
pasaban por `BOM.get_routing` y su división por `self.conversion_rate`.
Las reproducciones pasan con preparación corregida y tasas oficiales.
**Cero no demuestra por sí solo por qué get_exchange_rate devolvió cero durante
cada caso original.** La matriz deja ese motivo original no capturado; la causa
del túnel 403 solo se afirma donde existe su Error Log, en payment_request.

## Preparación, reproducción y conservación

1. Verificar rama/pins, servicios y ausencia de runners; no duplicar un proceso
   cuyo registro de herramienta se haya perdido. Usar lock y PID/birth.
2. Conservar sitios primario/fresh/diagnostic; crear el slot oficial necesario
   sin drop, reset, dump o restauración. Esto no prueba restauración cloud.
3. Renombrar el helper, ejecutar `module_preflight.py` y comprobar origen,
   apps.txt, módulos y resolvedor. Reparar únicamente la clave del sitio si la
   comparación demuestra un mapa incompleto; nunca ignorar la excepción.
4. Para FX, capturar primero configuración/Error Log. Cargar solo fixtures
   oficiales exactos, sin modificar fechas, tasas ni `allow_stale`; repetir
   módulos con `--offline --observe`. El guard no fabrica respuestas/tasas.
5. Para BOM persistida en cero, conservar el intento y probar el orden de
   fixtures en un sitio nuevo. Un fallo requiere evidencia adicional, no una
   aserción menor o un diagnóstico de bloqueo inevitable.
6. Conservar logs/XML/observaciones crudas exclusivamente fuera de Git.
   Publicar JSON de campos permitidos, IDs, hashes y conteos nativos mediante
   `publish_observations.py` y `publish.py`. No publicar trazas CI con locales.

El [registro de errores de preparación](evidence/frappe-official/diagnostic-preparation-failed-attempts.json)
conserva la carga impedida por el helper ocultando Payments y una inserción
inicial del hook FX antes de instalar ERPNext (DocType ausente). Ese hook se
movió después de instalación y antes de bootstrap; el sitio marcado vacío se
conserva y se continúa, sin borrarlo. Ninguno fue una suite aprobada.

## Lo pendiente y siguientes pasos concretos

1. Estas líneas acotadas terminaron al pasar; no se repiten completos. Los
   originales completos siguen FAIL y los métodos no reejecutados conservan su
   falta de resultado nuevo. Para un siguiente encargo, seleccionar un ID de
   `original-failure-followup.json`, conservar su traza y formular una hipótesis
   concreta antes de repetirlo en proceso/sitio oficial aislado. No atribuir
   todo a requests/oauthlib ni a un bloqueo inevitable.
2. Para HTTP 403/Domain forbidden originales que no se reproduzcan, conservar
   sitio/configuración/URL efectiva y observar respuesta HTTP sin secretos en
   un proceso limpio; no modificar proxy ni declarar causa sin esa evidencia.
3. HOME sigue de solo lectura: los tests de backup necesitan un ejecutor con
   HOME realmente escribible y los mismos pins. Permiso adicional no corrige
   un montaje de solo lectura. No cambiar HOME ni sus aserciones en este ejecutor.
4. Un FX sin registro oficial válido y que necesite un proveedor permanece sin
   evidencia de éxito real del proveedor. Este encargo prohíbe nuevas consultas
   y expansión de red; conservar esa limitación y el caso específico. No
   inventar cotizaciones ni afirmar que cualquier caso no reproducido está
   necesariamente bloqueado por red.
5. Criterio 13 requiere patch compatible real. Sin él, conservar BLOCKED y seis
   UNRUN. Una minor distinta exige plan separado de pins/SHAs, compatibilidad,
   backup, migración, regresión y rollback y aprobación previa; no se ensaya ahora.

Todas las correcciones quedaron en scripts de preparación, copia oficial y
sitios oficiales. No cambiaron venv/apps/configuración ni código de Cencomun;
sus fuentes upstream originales siguen limpias, pins y fixtures compartidos
idénticos, incluida la evidencia cloud externa exacta. La consulta autenticada
de precio/stock Cencomun pasó en este ejecutor; no es una restauración cloud.
No se repite su Core Test completo porque su runtime no cambió. La matriz Core
conserva 13 PASS y criterio 13 BLOCKED, distinta de estos completos oficiales FAIL.

Veinticinco controles del harness pasan, incluyendo red sin transporte externo,
colisión de paquete, conservación de intentos y rechazo de promover un subset a
completo. No son pruebas oficiales. Checkpoint inicial `5219094`, push solo lab;
el cierre añade las reproducciones finales y mantiene el PR #4 borrador.
HOME de solo lectura, patch inexistente y restricciones de red no se sortean.
Otros fallos del completo siguen documentados y no se atribuyen a una causa
general. El PR #4 permanece borrador; no se repite Guardar/Publicar ni la
restauración cloud externa acreditada.
