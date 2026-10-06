# Investigación acotada de preparación oficial

Continuación autorizada desde `8158b6803e4951a3fe66372578667f6cd8cab5a5`,
2026-10-05 America/Los_Angeles. Solo `lab/frappe-baseline`.

**Los completos siguen FAIL:** Frappe 2.319 tests (2.198 PASS, 24 FAIL,
46 ERROR, 51 SKIP); ERPNext CI 3.255 (3.188 PASS, 1 FAIL, 66 ERROR).
No se reejecutaron completos. El intento ERPNext interrumpido sigue incompleto.
**Criterio 13 BLOCKED; seis PATCH UNRUN.** No se inventa patch ni se cambian pins.

## Resultados acotados disponibles en este checkpoint

| Línea | Resultado ejecutado | Evidencia / alcance |
| --- | --- | --- |
| Autenticación limpia, CI nativa | 17 tests, 17 PASS | [auth CI 2](evidence/frappe-official/frappe-sequence-test_auth-attempt-2.json); módulo completo seleccionado, no suite completa |
| Payment Request antes de corrección | 22 ERROR de módulo ausente; después 17 PASS/5 ERROR de FX | [intento 2](evidence/frappe-official/erpnext-test_payment_request-attempt-2.json), [intento 3](evidence/frappe-official/erpnext-test_payment_request-attempt-3.json); transporte externo prohibido |
| Payment Request con fixtures oficiales | 22 tests, 22 PASS | [intento 5](evidence/frappe-official/erpnext-test_payment_request-attempt-5.json), sin consultas externas |
| Payment Entry → Payment Ledger Entry → Payment Order → Payment Reconciliation → Payment Request | 126 tests, 126 PASS | [secuencia CI](evidence/frappe-official/erpnext-sequence-test_payment_request-attempt-1.json); mismos módulos precedentes, proceso nuevo y runner CI nativo |
| BOM 0 frente a 10 | 1 test, FAIL | [BOM 1](evidence/frappe-official/erpnext-test_bom-selected-attempt-1.json); sigue investigándose orden de fixtures antes del bootstrap |
| Valor negativo | 1 test, ERROR en fixture-audit | [stock 1](evidence/frappe-official/erpnext-test_stock_entry-selected-attempt-1.json); conservado, validador intacto |
| Divisiones en fabricación | Pendientes en este checkpoint | No se aprueban por los PASS contables |

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

La investigación restante de BOM/valor negativo debe añadirse antes del cierre.
La hipótesis de cargar FX con el generador antes del bootstrap produjo otro
BOM FAIL: el generador importa el módulo test Currency Exchange y este importa
`ERPNextTestSuite`, que ejecuta `BootStrapTestData()` antes de insertar tasas.
El nuevo slot fixture-order carga directamente los mismos JSON mediante
`frappe.get_doc(record).insert()`, sin omitir validadores. Se comprobará que la
carga no creó aún BOM antes de ejecutar el bootstrap y la regresión afectada.
HOME de solo lectura, patch inexistente y restricciones de red no se sortean.
Otros fallos del completo siguen documentados y no se atribuyen a una causa
general. El PR #4 permanece borrador; no se repite Guardar/Publicar ni la
restauración cloud externa acreditada.
