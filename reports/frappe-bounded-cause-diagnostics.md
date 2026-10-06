# Diagnósticos acotados desde 618c676

Seguimiento conservado desde baad8f9: [auth/request](frappe-auth-request-diagnostics.md)
demuestra las primeras causas y retesta los 16 pendientes (14 PASS/2 ERROR).
No reemplaza esta secuencia ni los completos; API key adicional FAIL/UNKNOWN.

Solo `lab/frappe-baseline`, PR #4 borrador. Offline, mismos pins/oráculo,
sin modificación de upstream, HOME, red, acceso, producción, main o Axelor.
[ExecPlan 103](../tasks/103-frappe-bounded-cause-diagnostics.md).

Los completos anteriores conservan **FAIL**: Frappe 2.326 ejecutados
(2.220 PASS / 9 FAIL / 47 ERROR / 50 SKIP), ERPNext 3.255
(3.251 PASS / 4 ERROR). No se ejecutó otro completo ni se suman resultados
modulares. Criterio 13 **BLOCKED**, seis PATCH **UNRUN**. Restauración cloud
fcf690d externa ya acreditada: no se repitió.

## ERPNext: diferencia 100 demostrada, ERROR conservado

Sitio nuevo `ccm-upstream-erpnext-cause.test`, proceso nuevo, preparación
oficial y mapa Payments correcto. Seis registros Currency Exchange oficiales
intactos antes de imports/bootstrap, BOM cero al cargarlos. Solo
`TestExchangeRateRevaluation.test_05_revaluation_journal_reversal`:
**1 ejecutado / 1 ERROR**. Ningún otro método/módulo de test precedente en ese
proceso; sí preparación nativa de maestros, cuyo estado queda capturado.

[Causa y asiento completo](evidence/frappe-official/erpnext-revaluation-cause.json),
[resultado nativo](evidence/frappe-official/erpnext-test_exchange_rate_revaluation-selected-attempt-1.json),
[observación](evidence/frappe-official/erpnext-test_exchange_rate_revaluation-selected-attempt-1-observations.json),
[fixtures previas](evidence/frappe-official/erpnext-cause-fx-before-bootstrap.json).

Fecha nativa del caso 2026-10-06; `_Test Company`, moneda base INR. La factura
oficial tiene 100 USD a conversión 80: saldo 8.000 INR. El propio decorador del
test desactiva tasas antiguas. El resolvedor busca USD/INR con fecha
≤2026-10-06 y >2026-10-05. Las seis filas de 2016 siguen intactas pero ninguna
satisface el filtro. Proveedor habilitado (`disabled=0`), petición rechazada
por offline, retorno FX nativo cero. La evidencia siguiente demuestra por qué
ese cero produce **exactamente 100**, en lugar de atribuirlo por correlación.

| Fase / fila | Moneda de cuenta | Importe en cuenta | Tasa | Débito INR | Crédito INR |
| --- | --- | --- | --- | --- | --- |
| Construcción, receivable nuevo | USD | Débito 100 | 0 | 0 | 0 |
| Construcción, reversión saldo viejo | USD | Crédito 100 | 80 | 0 | 8.000 |
| Construcción, Exchange Gain/Loss | INR | Débito 8.000 | 1 | 8.000 | 0 |
| Tras resolver tasa del JE, receivable nuevo | USD | Débito 100 | 1 | 100 | 0 |
| Antes de validar submit, totales | INR | — | — | 8.100 | 8.000 |

El resolvedor específico Journal Entry termina con **`exchange_rate or 1`**.
Se captura su retorno 1 tras el cero del resolvedor FX general. La pérdida de
8.000 ya calculada permanece igual al recalcular el primer débito: diferencia
**100×(1−0)=100 INR**. El asiento ya está desequilibrado en borrador; submit
lo rechaza correctamente. `docstatus=1` dentro del intento es estado en memoria
antes de validar; no acredita contabilización exitosa ni GL persistido.

No hay defecto propio de preparación demostrado. Pasar este caso exige una
tasa nativa elegible dentro de su ventana; con estos fixtures y offline no
existe. Cambiar fixtures/fecha, comportamiento upstream/pins o acceso al
proveedor excede el encargo. La línea se detiene con ERROR; no se inyecta tasa,
se cambia aserción/validador ni se repite tras demostrar la causa.

## Frappe: los 26 rechazos eran del mock, no TCP

El terminal literal de los 26 bloques es `Connection refused by Responses -
the call doesn't match any registered mock`, con frames del interceptor
`responses`; no demuestran Errno 111. El clasificador propio confundió ese
texto con un rechazo TCP. Se conserva su diagnóstico inicial y se publica
[revisión v2](evidence/frappe-official/frappe-final-failure-diagnostics-v2.json)
y [tabla de los 26 IDs](evidence/frappe-official/frappe-historical-http-reclassification.json).
La revisión identifica además dos rechazos de Responses antes UNKNOWN:
28 rechazos de mock / 5 rechazos offline terminales / 23 UNKNOWN. No cambia
el resultado completo. El log web antiguo vacío y sin PID/listener impide
establecer retrospectivamente cuánto vivió ese servidor; estas excepciones
sí se originaron antes del transporte de socket.

La primera petición aislada `test_unauthorized_call_v1` pasó: 1/1, respuesta
403 nativa. URL `http://127.0.0.1:8002/api/resource/User`, puerto correcto,
PID 32056/start ticks 2131065, listener propio inode 353996 durante el caso.
Sin salida web aún (log vacío), exit `null` antes del cleanup y -15 después
del SIGTERM explícito del harness. Cero reinicios automáticos.
[Resultado y telemetría](evidence/frappe-official/frappe-test_api-selected-attempt-1.json).

| Intento acotado | Resultado | Evidencia / limitación |
| --- | --- | --- |
| Webhook→API, intento 1 | Bootstrap interrumpido, contador desconocido; cero eventos de test | Bug nuevo de observación: `registered` es método, no iterable. Corregido y controlado; no es un límite upstream. |
| Webhook→API, intento 2 | 23 ejecutados; 13 PASS, 11 ERROR nativos | Diez `setUp` de Webhook vencen timeout por POST oficial simulado rechazado por guard; un ERROR extra de `setUpClass` API por referencia a Webhook eliminado. Errores de fixture no son métodos adicionales. |
| Nueve módulos, guard corregido, sitio/proceso nuevos | 155 ejecutados; 139 PASS / 1 FAIL / 15 ERROR / 0 SKIP | Sin rechazos Responses ni TCP. Cinco módulos completos PASS; fallos nuevos conservados y descritos abajo. |

El intento 2 captura `HTTPAdapter.send` de Responses, POST oficial registrado,
bloqueo propio previo al interceptor y mock activo al entrar API. Server vivo,
listener propio y sitio `ccm-upstream-frappe-cause.test` servido, observado
en `frappe.app.init_request`. Su fallo de fixture impidió ejecutar
TestResourceAPI: no se atribuye a este intento una reproducción nueva de ese
método. Los bloques históricos demuestran el interceptor; su activación
antigua exacta no se reconstruye con telemetría inexistente.

Corrección limitada al guard propio: respetar Responses oficial únicamente
si el adaptador procede del módulo real cargado y no tiene prefijos ni
respuestas passthrough. No instalar mocks ni fabricar respuestas/tasas.
Dejar que el interceptor nativo consuma registros y compruebe aserciones.
Peticiones externas sin mock y passthrough siguen rechazadas antes de transporte;
DNS y sockets externos siguen bloqueados. Controles verifican mock sin socket,
passthrough rechazado y aserción nativa intacta. El observador captura URL sin
userinfo/query/fragmento y no permite que sus propios errores alteren un test.

Sitio corregido `ccm-upstream-frappe-cause-fixed.test`, PID web 32587/start
ticks 2163785, listener propio inode 359463; misma URL/host/puerto nativos.
Antes/durante/final servidor vivo y listener propio; sitio servido correcto,
76 respuestas HTTP observadas. Salida web vacía durante la ejecución, retenida
y hashed; exit `null` antes de cleanup y -15 solo después de SIGTERM del
harness. No caída, endpoint incorrecto o reinicio encubierto demostrados.
[Resultado/telemetría](evidence/frappe-official/frappe-sequence-test_perf-attempt-1.json),
[observación](evidence/frappe-official/frappe-sequence-test_perf-attempt-1-observations.json),
[cobertura revisada](evidence/frappe-official/frappe-sequence-test_perf-attempt-1-coverage-v2.json).

| Módulo oficial corregido | PASS | FAIL | ERROR |
| --- | --- | --- | --- |
| Webhook | 10 | 0 | 0 |
| Workflow | 16 | 0 | 0 |
| API v1 | 26 | 0 | 0 |
| API v2 | 25 | 0 | 0 |
| Auth | 17 | 0 | 0 |
| Client | 11 | 0 | 2 |
| FrappeClient | 1 | 0 | 12 |
| OAuth | 12 | 1 | 0 |
| Performance | 21 | 0 | 1 |
| Total de esta secuencia | 139 | 1 | 15 |

Los 155 IDs coinciden exactamente con los nueve módulos del discovery nativo
fijado conservado: ningún ID sin resultado. No se ejecutó un discovery nuevo
en esa secuencia. El observador del proceso se cargó antes de añadir la captura
de discovery; la cobertura inicial que contenía cero discovery se conserva y
se revisa explícitamente, sin deducir de ella cero casos faltantes. La cobertura
v2 compara con el manifiesto anterior y conserva ese límite de procedencia.

Pendientes independientes: dos errores Client muestran `request=None` al
intentar `no_cache`; doce errores FrappeClient y uno Performance son AuthError
en login nativo; OAuth conserva `AssertionError: None is not true`. Son
**UNKNOWN** respecto a su primera causa: el transporte ya funciona, pero no
se demuestra fallo de credenciales, permisos, servidor o capacidad inevitable.
No se cambian credenciales, acceso, validadores o aserciones para ocultarlos.
No se inicia otra secuencia/completo por esos fallos sin hipótesis demostrada.
La aserción de rendimiento no llegó a medirse al fallar login: tampoco PASS.

## Preservación, Cencomun y cierre

Se preservan todos los sitios previos y los tres sitios nuevos, cada intento,
logs/XML/observaciones privados. Antes/después: 49.823 archivos originales
con hash idéntico, manifest
`7b1788b6d70dcd583969552b5739c272a118c8a7a79f9c552e7010a199b49cd9`;
fuentes originales limpias y en los SHAs fijados, pins/oráculo intactos.
Consulta autenticada Reader: **P001 USD50.00, stock5**, adaptador igual a API
nativa. No se afectó runtime Cencomun: no se repite Core. Sus 34 grupos previos
mantienen alcance separado; 13 PASS/1 BLOCKED, seis PATCH UNRUN.
[Integridad](evidence/frappe-official/cencomun-cause-integrity-after.json),
[lectura autenticada y cierre](evidence/frappe-official/cause-closure.json).

45 controles del harness PASS y guardrails PASS; no cuentan como tests oficiales.
359 de 361 artefactos históricos permanecen byte a byte; dos logs de servicios
crecieron solo por append y sus prefijos originales mantienen el hash.
28 raíces Git inspeccionadas en `/workspace`: un proyecto y 27 dependencias,
caches o archivos de fuentes retenidos. Montajes/marcadores `.git` vacíos se
verificaron como no repositorios; dos depots uv tienen HEAD unborn comprobado.
Ningún checkout de proyecto desconocido se omitió para preparar el borrador.
Los servicios oficiales exclusivos se detuvieron tras finalizar; ningún runner
nativo activo. Los servicios Cencomun conservan datos y responden al probe.

## Reproducción y resolución paso a paso

Desde `/workspace/cencomun-erp-lab`, sin reinstalar ni modificar HOME:

```bash
source scripts/frappe-integral/env.sh
export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
export CCM_OFFICIAL_OFFLINE=1
export PYTHONPATH="$PWD/scripts/official-tests/observer"
```

1. Comprobar `run.active_runners()` y lock. Si hay proceso activo, observar
   PID/start ticks/log privado saneado; no duplicarlo, cancelarlo ni preparar
   sus fixtures. Conservar primero todos los intentos y fuentes generadas.
2. Crear únicamente un sitio oficial nuevo con `prepare.py erpnext --cause
   --official-fx-fixtures` o `prepare.py frappe --cause`. Estos slots ya existen
   aquí: no reinicializarlos para reproducir. Usar un slot nuevo explícito en
   una ejecución futura autorizada. Preparación/base vacía no acredita cloud.
3. Comando exacto ERPNext ya ejecutado:

   ```bash
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py erpnext \
     --site ccm-upstream-erpnext-cause.test \
     --module erpnext.accounts.doctype.exchange_rate_revaluation.test_exchange_rate_revaluation \
     --test test_05_revaluation_journal_reversal --offline --observe
   ```

4. Para su ERROR: cotejar filtros, filas y retornos con las fases JE del JSON.
   No introducir tasas ni desactivar validación. Documentar por separado una
   alternativa de fixture/fecha/pin/upstream/acceso para una decisión futura;
   no está autorizada ni ejecutada aquí. No inventar patch para criterio 13.
5. Para Frappe: distinguir `refused_by_responses` de `os_errno111`; cotejar
   get_url/config con listener, PID/birth, sitio servido y exit previo a cleanup.
   Si hay mock activo, revisar start/stop y petición registrada. No detener
   mocks ni reiniciar web en mitad de un método para hacerlo pasar.
6. La corrección se validó en sitio nuevo `--cause-fixed`, después de archivar
   fuentes de prueba y recrear solo la copia oficial en iguales SHAs, con worker
   exclusivo detenido. Comando de la secuencia corregida:

   ```bash
   "$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe \
     --site ccm-upstream-frappe-cause-fixed.test --offline --observe --sequence \
     frappe.integrations.doctype.webhook.test_webhook \
     frappe.workflow.doctype.workflow.test_workflow \
     frappe.tests.test_api frappe.tests.test_api_v2 frappe.tests.test_auth \
     frappe.tests.test_client frappe.tests.test_frappe_client \
     frappe.tests.test_oauth20 frappe.tests.test_perf
   ```

7. Para los UNKNOWN nuevos: conservar IDs/frames y plantear, antes de repetir,
   observación de estado request en Client, respuesta de login sin cookies/tokens
   en FrappeClient y condición OAuth fallida, en procesos limpios representativos.
   No atribuirlos a credenciales, red o HOME sin prueba; no cambiar esas capacidades.
8. Verificar Cencomun con `integrity.py before/after --label <nuevo>` y lectura
   `scripts/core-test/readiness.py`. Si hay diferencias reales de runtime,
   investigar y repetir regresión autorizada; sin diferencias, conservar prueba
   de hashes y lectura sin restaurar/seedear/migrar ni generar eventos.

Borrador ordinario del entorno: [instrucciones actualizadas](../docs/FRAPPE_ENVIRONMENT_START.md).
Solo repositorio/ref e instrucciones de inicio; configuración restante intacta.
Guardar/Publicar queda a cargo del coordinador y no se acredita anticipadamente
un snapshot del commit nuevo ni otra restauración cloud.
