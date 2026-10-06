# Diagnóstico acotado de 16 resultados desde baad8f9

Los **16 resultados pendientes** de la secuencia retenida tienen ahora
**14 PASS y 2 ERROR** en reproducciones nuevas acotadas. Los dos Client conservan
ERROR con causa demostrada. Un fallo adicional de API key conserva FAIL/UNKNOWN.
**No se repitió ninguna suite completa** ni se sumaron estos PASS a sus resultados.
Frappe completo permanece FAIL (2.326: 2.220 PASS/9 FAIL/47 ERROR/50 SKIP);
ERPNext completo permanece FAIL (3.255: 3.251 PASS/4 ERROR).
C13 sigue BLOCKED y sus seis PATCH UNRUN. Core conserva sus 34 grupos previos.

Evidencia por los 16 IDs, descubrimiento/selección, resultados de cada intento,
frames y parámetros presentes:
[auth-bounded-results.json](evidence/frappe-official/auth-bounded-results.json).
Los JSON originales de cada intento se conservan; los logs/XML completos y
credenciales permanecen privados. La interpretación acotada no reescribe los
completos ni la secuencia anterior de 155 pruebas.

## Acceso y conservación

Tras el reintento de UI, comandos al ejecutor respondieron correctamente:
HEAD baad8f9, lab/frappe-baseline, checkout inicialmente limpio, 81 logs de
intentos retenidos y cero runners. Los servicios estaban detenidos y se
arrancaron con sus gestores idempotentes, sin reinstalar, recrear o restaurar
datos. La continuidad del filesystem acredita recuperación del trabajo; sin
un identificador anterior de kernel no acredita la misma instancia de proceso.
No se inventa un código del error de UI que no fue facilitado al ejecutor.

[auth-preservation.json](evidence/frappe-official/auth-preservation.json):
443 artefactos anteriores conservados: 441 idénticos y dos logs de servicios
privados con su prefijo original intacto y nuevas líneas al final. Los 38
archivos privados/configuraciones protegidos y ambos common_site_config siguen
idénticos. Los 15 sitios oficiales explícitos mantienen DB legible y los tres
checkouts copiados están limpios en sus SHAs fijados. No quedó ningún runner.
La publicación baad8f9 y restauración externa fcf690d no se repitieron.

## Casos ejecutados y contadores nativos

Cada fila es un intento propio, no una suma de resultados de evaluación.
`-selected` usa selectores nativos de métodos. Las secuencias usan el
ParallelTestRunner nativo, un shard, módulos íntegros y orden explícito.
Los módulos individuales usan `bench run-tests` sin alterar aserciones.

| Archivo nativo (frappe-… .json) | Sitio | Alcance | Ejecutadas | PASS | FAIL | ERROR | SKIP |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| test_frappe_client-selected-attempt-1 | auth-clean | Un login representativo | 1 | 0 | 0 | 1 | 0 |
| test_client-selected-attempt-1 | auth-clean | Dos Client sin Workflow previo | 2 | 2 | 0 | 0 | 0 |
| test_oauth20-selected-attempt-1 | auth-clean | Implicit token limpio | 1 | 1 | 0 | 0 | 0 |
| sequence-test_oauth20-attempt-1 | auth-clean | FrappeClient → OAuth; credencial discrepante preservada | 26 | 13 | 1 | 12 | 0 |
| sequence-test_oauth20-attempt-2 | auth-sequence | Workflow → Client → FrappeClient → OAuth; preparación corregida | 55 | 51 | 1 | 3 | 0 |
| test_perf-attempt-1 | auth-sequence | Performance completo, sin profiling de frames | 22 | 22 | 0 | 0 | 0 |
| test_client-attempt-1 | auth-sequence | Client después de corregir PATH de PDF | 13 | 11 | 0 | 2 | 0 |
| test_client-attempt-2 | auth-sequence | Client; observador del Local nativo corregido | 13 | 11 | 0 | 2 | 0 |

Los sitios completos se llaman `ccm-upstream-frappe-auth-clean.test` y
`ccm-upstream-frappe-auth-sequence.test`. Todos los intentos están offline.
No hay bootstrap de runner interrumpido, fixture fallido, SKIP o caso seleccionado
sin resultado en estas ocho filas. El loader cargó 13 IDs en cada reproducción
seleccionada; los 12/11/12 no seleccionados están fuera de su alcance, sin
contarlos como ejecutados. Las secuencias descubrieron efectivamente 26/55 IDs,
todos con resultado. Performance tiene 22 registros JUnit y contador 22; el
cotejo de IDs usa el discovery fijado retenido, sin profiling del benchmark.

Se conserva además un intento de **preparación**, cero pruebas: se invocó
prepare.py con el Python del sistema; new-site/config/bootstrap nativos
terminaron, pero el preflight Python no pudo importar frappe. Se continuó
únicamente ese preflight con el Python del Bench, sin repetir la instalación.
En la preparación instrumentada, el observador creó su stream antes de una
reserva `open('x')`; esa reserva devolvió FileExistsError, no truncó nada y el
helper nativo terminó correctamente. Ambos son incidentes del harness, no
resultados de tests ni motivo para reiniciar suites.

## Causa de los 12 FrappeClient y Performance

La comparación privada, con SELECT nativo y verificación passlib **sin** llamar
check_password/update_password, demuestra:

| Comparación, solo coincidencia | Sitio anterior y auth-clean | Nuevo auth-sequence |
| --- | --- | --- |
| Conf de sitio frente al hash Administrator | No coincide | Coincide |
| Credencial común retenida frente al hash | Coincide | Coincide |
| Conf de sitio frente a la común retenida | No coincide | Coincide |

El defecto propio era generar/usar una credencial de sitio que el instalador
ignoraba: `installer.install_db:174` usa la conf común cargada antes del argumento
admin_password. Después, prepare.py escribía otra credencial en la conf del
sitio. `TestFrappeClient.PASSWORD` carga esa conf al importar la clase; las trazas
demuestran coincidencia clase/conf y discrepancia conf/hash. IntegrationTestCase
carga ADMIN_PASSWORD mediante get_conf en setUpClass, también discrepante.
La respuesta representativa es **401 / AuthenticationError / Invalid login
credentials**, servida por el sitio correcto. No es endpoint incorrecto ni
caída del servidor. Los hooks nativos no deshabilitaron el login por contraseña.

Corrección acotada: **solo al crear sitios nuevos**, el helper reutiliza la
credencial común ya retenida y respeta la misma prioridad que el instalador.
No cambia common_site_config, passwords de usuarios, claves existentes,
políticas o acceso. Los sitios anteriores discrepantes quedan intactos.
Los slots auth existentes se rechazan si alguien intenta prepararlos otra vez.
No se ejecutó reset de contraseña ni se regeneró una credencial para obtener PASS.

La secuencia corregida aprueba los 12 casos de contraseña de FrappeClient.
Performance aprueba sus 22 casos, incluido el login antes de su benchmark:
1.000 requests en 3,378538 s, 295,986 RPS; umbral nativo intacto **126 RPS**.
Ese intento desactiva profiling/tracing de frames y mantiene guard offline y
observación saneada HTTP. No es una medición comparativa de Core/Axelor.

## Primer HTTP 500 de OAuth

La reproducción FrappeClient → OAuth muestra el primer fallo real del login:
**SecurityException** en `auth.get_login_attempt_tracker:521`. El tracker de IP
loopback tiene 11 fallos frente al máximo nativo 10, durante la ventana de 60 s.
El POST `/api/method/login` devuelve 500 antes de completar autenticación.
No se atribuye ese 500 al algoritmo OAuth ni se cambia el límite de login.

El helper oficial `test_oauth20.login:496–497` ignora el response. Authorize
devuelve 302 hacia `/login`, con query `redirect-to`, y después 200 de login.
No se produce el ConnectionError de la redirección localhost que el test usa
para recuperar el fragmento. En la aserción de línea 390, redirect_destination
está ausente y response_dict tiene **cero nombres de parámetros**: access_token
ausente. Se publican únicamente status/rutas/nombres/presencia; nunca valores
de tokens, cookies, headers o consultas de login.

OAuth aislado pasa y también pasa tras los módulos corregidos: login 200 y
fragmento con access_token/expires_in/scope/token_type presentes. El guard
permanece activo y no permite passthrough de mocks a Internet.

El stream antiguo no capturó la excepción del servidor para su 500 y el SELECT
histórico de Error Log no la recuperó. La causa está **demostrada en la nueva
reproducción controlada**, coincidente con su patrón; no se inventa telemetría
retrospectiva del proceso anterior ni un Error Log inexistente.

## Los dos Client mantienen ERROR

Ambas excepciones tienen frame exacto `website/utils.py:537`, atributo
`no_cache`, request distinto de None, tipo `frappe.types.frappedict._dict`,
truthy, **cache_control None**. El objeto request no fue destruido antes del fallo.

- `test_http_valid_method_access` instala request en test_client.py:54 y agrega
  method en :55. Primero falla execute_cmd → client.save → ToDo.insert,
  antes de las aserciones del caso.
- `test_set_value` falla en **ToDo.insert (:18)** antes de llamar set_value.
  El último request fue instalado por el precedente `test_run_doc_method:105`;
  no hubo destroy/release posterior antes del frame que falla.

Frappe v16 usa su propio Local en `frappe/utils/local.py`, no solamente
werkzeug.local. La primera versión del observador no registró sus asignaciones;
se corrigió esa cobertura y se repitió únicamente Client en proceso nuevo.
El resultado no cambió: 11 PASS/2 ERROR, sin observation_error.

Workflow deja el fixture activo Test ToDo, con send_email_alert=1, que existe
tras el retorno nativo del módulo. Su email se ejecuta sincrónicamente en test
y llama attach_print → get_print → TemplatePage.render → cache_html_decorator.
Los dos Client pasan en sitio limpio sin ese Workflow. Con Workflow precedente
persisten ambos ERROR, incluso con PATH correcto. No es una caché falsa del
harness: el documento nativo activo también existe en DB.

Límite preciso: lograr PASS de esa combinación requeriría cambiar el contrato
request/renderer nativo, el fixture/teardown upstream o el caso oficial.
No se añade un request ficticio por caso ni se elimina/modifica el Workflow para
forzar PASS. No se ensayó cambio de minor, pins, aserciones o validadores.

## Resultados adicionales conservados

El caso oficial de API key crea su fixture nativo por primera vez en cada sitio
nuevo de diagnóstico. No se ejecuta sobre sitios anteriores ni credenciales
Cencomun. Esa creación oficial no se usa como reparación: tras el FAIL no se
vuelve a ejecutar generate_keys ni a regenerar/restablecer el secreto.

1. `test_client_get` tuvo OSError: el ejecutable PDF fijado no estaba en PATH
   de aquella invocación. Se corrigió únicamente el entorno del proceso con
   official-tools/bin y core-tools/usr/bin. wkhtmltopdf continúa 0.12.6.1 con
   patched Qt. El módulo Client repetido confirma que ese caso pasa; conserva
   los dos ERROR obligatorios anteriores. No se cambió HOME ni un permiso.
2. `test_auth_via_api_key_secret` tuvo **FAIL, 401 != 200** en su primera petición
   positiva. La lectura posterior encuentra su secreto nativo no descifrable
   con la clave retenida del sitio. **UNKNOWN**: no se capturó el orden inicial
   de creación/carga/caché de esa clave para atribuir la causa. No se reparó ni
   regeneró ninguna clave y no se repitió el caso para obtener PASS. Queda abierto
   un diagnóstico específico de ese ID; UNKNOWN no significa imposible.

## Reproducción y resolución paso a paso

No repetir completos. No preparar de nuevo slots ya existentes, ni borrar
sitios, logs, reservas o resultados. Los comandos crean intentos exclusivos.

```bash
cd /workspace/cencomun-erp-lab
source scripts/frappe-integral/env.sh
export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
export CCM_OFFICIAL_OFFLINE=1
export PYTHONPATH="$PWD/scripts/official-tests/observer"
PY="$CCM_FRAPPE_ROOT/official-bench/env/bin/python"
"$PY" -c 'import sys; sys.path.insert(0,"scripts/official-tests"); from run import active_runners; assert not active_runners()'
"$PY" scripts/official-tests/auth_probe.py ccm-upstream-frappe-cause-fixed.test ETIQUETA-NUEVA
```

`ETIQUETA-NUEVA` es un basename nuevo alfanumérico/con guiones; nunca reutilizar
uno existente. El probe solo publica coincidencias, no hace login ni rehash.

Si se autoriza otra reproducción del mismo caso, usar el sitio retenido
correspondiente con run.py, --offline --observe --auth-diagnostics y selector
nativo --module/--test. Para benchmark usar --offline --auth-diagnostics **sin
--observe**, conservando el umbral. Iniciar únicamente worker.py/smtp.py cuando
el caso los necesite, después de verificar cero runners. No reiniciar web dentro
del test: cada intento posee su servidor, captura PID/start ticks/listener/sitio,
y lo termina explícitamente después del resultado nativo.

Ante discrepancia de login: conservar respuesta/frames, ejecutar probe, comparar
conf/hash/común y momento de import, verificar host_name/sitio servido. No reset
ni cambio de política. Ante 500: identificar primero exception/tracker nativos;
no atribuirlo a OAuth por un fragmento vacío. Ante Client: revisar la asignación
del Local nativo, cache_control y Workflow activo, sin inyectar request.
Ante PDF: comprobar command -v/version y corregir solo PATH a herramientas
retenidas. Ante API key: conservar FAIL y su key existente; siguiente diagnóstico
deberá observar carga/descifrado por coincidencias y no regenerar credenciales.

## Cierre Cencomun y entrega

[cencomun-auth-integrity-after.json](evidence/frappe-official/cencomun-auth-integrity-after.json)
acredita **49.823 archivos idénticos** antes/después: runtime original, fuentes,
pins, conf y fixtures compartidos. [auth-closure.json](evidence/frappe-official/auth-closure.json)
coteja los 17 archivos del oráculo con fcf690d y el recibo externo intacto.
Readiness y API/adaptador como Reader autenticado: P001 USD50.00, stock5, LAB
activo y métricas desactivadas. Cero mutaciones de negocio; Core no se repitió
porque su runtime no cambió. Alcance conservado: 34 grupos PASS, 13 criterios
PASS/1 BLOCKED; no se convierte C13 en PASS ni se repite restauración cloud.

Los controles del harness/privacidad/guard se ejecutan aparte de los contadores
oficiales: **52 controles PASS**, más verify-repo y diff --check. Solo código,
documentación y JSON saneado se publican en
lab/frappe-baseline; PR #4 permanece borrador. El nuevo borrador ordinario podrá
proponer referencia/instrucciones del commit probado; **Guardar/Publicar queda
a cargo del coordinador**, sin cambios de Internet, secretos, variables,
privacidad ni permisos.
