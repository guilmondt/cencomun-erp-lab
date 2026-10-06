# Última pasada completa de CI oficial

Corrección posterior de causalidad: los 26 mensajes etiquetados abajo como
rechazos TCP son rechazos del mock oficial Responses. El resultado completo
permanece FAIL. Véase [diagnóstico acotado](frappe-bounded-cause-diagnostics.md)
para la revisión preservada, corrección del guard propio y regresión de módulos.

Autorizada desde `9cbfbbd5ccd99aaa0b90cabdc8447aea173fb25c`. No suma PASS de
reproducciones modulares. Los resultados completos anteriores se conservan.
Una pasada Frappe seguida de una ERPNext, un shard nativo por aplicación,
modo offline; criterio 13 BLOCKED y seis PATCH UNRUN.

## Resultado final de esta nueva ejecución

**CERRADO_CON_FAIL_Y_LIMITACIONES.** Una ejecución completa nueva por aplicación,
en serie, con resumen nativo completo y exit 1 en ambas. Cero IDs descubiertos
sin resultado. Los anteriores FAIL/incompletos siguen conservados; no se suman
sus PASS ni los de reproducciones modulares a esta tabla.

| Aplicación / intento exclusivo | Discovery | Contador nativo | PASS | FAIL | ERROR | SKIP | Estado | Segundos |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Frappe / CI 1, sitio final | 2.326 | 2.326 | 2.220 | 9 | 47 | 50 | FAIL | 966,617 |
| ERPNext / CI 2, sitio final | 3.255 | 3.255 | 3.251 | 0 | 4 | 0 | FAIL | 5.062,373 |

CI 2 identifica el siguiente archivo después del CI 1 histórico ERPNext; es
**la única** ejecución completa ERPNext de este encargo. Frappe terminó a las
06:23:23 UTC; ERPNext a las 07:52:14 UTC del 2026-10-06. PID ERPNext 28107 y
driver 28065 finalizaron; última escritura nativa del log 07:52:13 UTC. Worker
oficial y SMTP local detenidos después; cero runners oficiales activos.

Frappe: 2.286 IDs distintos y 40 ejecuciones repetidas nativas (39 PASS y un
SKIP adicionales). ERPNext: 3.255 IDs distintos, sin repeticiones. SKIP no cuenta
como PASS; el verbose nativo no imprimió sus motivos, que no se inventan. Los
contadores nativos incluyen skips y no se sustituyen por IDs distintos.

- [Inventario Frappe](evidence/frappe-official/frappe-final-case-inventory.json) y
  [ERPNext](evidence/frappe-official/erpnext-final-case-inventory.json): todos los
  resultados por ID, repeticiones y listas vacías de casos sin resultado.
- [Intento Frappe](evidence/frappe-official/frappe-ci-attempt-1.json) y
  [ERPNext](evidence/frappe-official/erpnext-ci-attempt-2.json): comandos, exit,
  resumen, hashes de logs privados y cabeceras de fallos sin variables.
- Frappe conserva 56 eventos fallidos: cinco rechazos offline terminales,
  26 rechazos TCP locales de causa desconocida y otros 25 UNKNOWN.
  [Clasificación](evidence/frappe-official/frappe-final-failure-diagnostics.json).
- ERPNext conserva cuatro ERROR. La clasificación inicial conservadora
  [v1](evidence/frappe-official/erpnext-final-failure-diagnostics.json) se conserva;
  [v2](evidence/frappe-official/erpnext-final-failure-diagnostics-v2.json) incorpora
  la correlación nativa, sin ejecutar casos otra vez. Tres son falta de tasa
  aplicable después de rechazo offline demostrado; uno mantiene causa UNKNOWN.

| ID ERPNext (prefijo nativo completo en los JSON) | Condición del validador / evidencia | Clasificación final |
| --- | --- | --- |
| TestExchangeRateRevaluation.test_05_revaluation_journal_reversal | Débito y crédito difieren en 100. Se observan retornos FX cero y rechazos offline, pero no se demostró que expliquen por sí solos el desequilibrio. | UNKNOWN; ERROR |
| TestQuotation.test_make_quotation_qar_to_inr | QAR → INR, for_selling, fecha 2026-01-01: consulta nativa sin filas elegibles; rechazo HTTP offline, Error Log nativo y retorno cero. La configuración tiene disabled=0. No existe ese par en las seis tasas oficiales. | Límite offline demostrado; ERROR |
| TestSerialNo.test_inter_company_transfer_fallback_on_cancel | INR → USD: for_buying devuelve 0,0167 de su fila oficial; for_selling no tiene fila elegible, registra rechazo offline y devuelve cero. La fila oficial tiene for_selling=0. Validador exige tasa. | Límite offline demostrado; ERROR |
| TestSerialNo.test_inter_company_transfer_intermediate_cancellation | Mismo contraste de for_buying/for_selling, con Error Logs y retornos propios de este ID. | Límite offline demostrado; ERROR |

[48 observaciones exactas de esos cuatro IDs](evidence/frappe-official/erpnext-final-failed-fx-observations.json):
configuración y filas antes/después, filtros/retornos, rechazos, Error Logs
nativos saneados y hashes/frames. La asociación exige mismo PID, par monetario
del validador, retorno cero sin filas elegibles y Error Log offline desde el
retorno anterior. No atribuye ceros a configuración deshabilitada ni a una
respuesta del proveedor; no se hizo una nueva consulta a proveedores.

El bootstrap ERPNext previo terminó exit 0/cero tests. La preparación inicial
Frappe se interrumpió antes del bootstrap (Click, cero tests), se conservó y
se corrigió. Ninguna de estas dos nuevas ejecuciones completas fue interrumpida.
El intento ERPNext serial 2 histórico sigue incompleto, con contador desconocido;
no se convierte en PASS ni se añade a los conteos nuevos.

## Conservación de Cencomun y verificación final

La [integridad posterior](evidence/frappe-official/cencomun-final-integrity-after.json)
compara 49.823 archivos con la captura previa: **cero cambios**, mismo manifest
SHA256 y fuentes originales Frappe/ERPNext limpias en los pins. Incluye env,
apps Frappe/ERPNext/Cencomun, configuración de sitios, manifiestos de assets,
versions.lock y oráculo; excluye cachés Python, Git, logs y datos DB mutables.

[Cierre de conservación](evidence/frappe-official/final-closure.json): diez sitios
oficiales conservan directorio y DB legible; 48 evidencias anteriores mantienen
sus hashes y 32 logs privados coinciden con su SHA registrado; 17 archivos
compartidos son idénticos byte a byte a fcf690d; pins y recibo cloud intactos.
La consulta autenticada como reader compara adaptador y registros nativos:
**P001 USD 50.00, stock 5**. LAB activo y medición de queries desactivada.

No cambió el runtime cubierto de Cencomun, por lo que no se repitieron sus 34
grupos. Se conserva la ejecución 20261006T042836Z: 34 PASS obligatorios,
13 criterios PASS y criterio 13 BLOCKED, seis PATCH UNRUN. Esta lectura no
es una nueva regresión ni una restauración cloud. No acredita 14/14 ni un ERP
integralmente aprobado.

El helper adicional de cierre tuvo dos intentos FAIL por cwd de logger nativo;
se conservan [los tres intentos](evidence/frappe-official/final-closure-preparation-attempts.json).
La causa demostrada fue resolver `<site>/logs/database.log` desde Bench en lugar
de `sites/`. Se adoptó el cwd de los helpers nativos existentes, sin crear otra
jerarquía ni tocar HOME/permisos. Su tercer intento PASS y la regresión con
RotatingFileHandler nativo verifican la ruta real y restitución del cwd.
**38 controles del harness PASS**, guardrails/diff check PASS; no son suites
oficiales ni se suman a sus contadores. El criterio 13 continúa BLOCKED.

## Pendientes y decisiones adicionales

- Para los tres errores FX: conservar ERROR; localizar sus filtros/fechas y
  Error Logs en el anexo; verificar primero si existe un fixture oficial apto
  en el SHA fijado. No invertir una tasa, agregar QAR/INR, cambiar for_selling,
  fechas o settings para aprobar. Si requieren transporte externo, documentar
  destino/alcance y obtener una autorización separada antes de usar esa capacidad.
  Esta pasada offline concluye sin sortear esa limitación.
- Para el desequilibrio 100: conservar UNKNOWN/ERROR; en un encargo acotado futuro
  capturar cuentas, débitos/créditos, fecha y filtros FX nativos en un sitio nuevo,
  con las mismas fuentes/fixtures; comparar el documento antes del submit y
  el orden de módulos. Probar una hipótesis concreta sin nuevas tasas ni tocar
  validador/aserción. No es un bloqueo inevitable ni un defecto upstream probado.
- Para Frappe: seguir los pasos detallados al final de este informe. Rechazos
  TCP locales y otros UNKNOWN requieren diagnóstico acotado. El HOME readonly
  histórico y pip check requests/oauthlib siguen documentados; no se sortean
  ni se atribuyen automáticamente a estos fallos nuevos.
- Para criterio 13: seis escenarios UNRUN por falta de patch posterior compatible.
  Otra minor requiere plan separado y aprobación antes de cualquier ensayo.
- Sin más completos en este encargo. Solo checkpoints/cierre saneados en
  lab/frappe-baseline, PR #4 borrador; sin main, producción, Axelor o upstream.

## Preparación y estado del checkpoint inicial

- Original Cencomun: 49.823 archivos de env/apps/configuración/oráculo capturados
  por hash, fuentes originales limpias en sus SHAs fijados. Comparación posterior
  pendiente: [integridad previa](evidence/frappe-official/cencomun-final-integrity-before.json).
- Fuentes copiadas conservadas y recreadas en Frappe
  `97a5dd93ca5883bcc9c4ef9834120c5cba397b67`, ERPNext
  `fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba`, Payments
  `cca07d9f9392e2ea0e521c5975151db9e4b6c321`; tres checkouts limpios antes del runner.
- Sitio Frappe nuevo `ccm-upstream-frappe-final.test`, solo Frappe, hook oficial
  before_tests completado y mapa nativo verificado sin reparación. Worker del
  Bench oficial y SMTP ficticio local, sin relay. Cencomun no se instala aquí.
- Preparación inicial interrumpida antes de bootstrap: `set-config` interpretó
  una contraseña local con guion inicial como opción (exit 2). Credencial
  conservada; se usó el separador Click `--` y se completó el hook. Ningún test
  fue ejecutado en ese fallo. La inspección inicial acreditaba solo aislamiento,
  no preparación completa. [Registro saneado](evidence/frappe-official/frappe-final-preparation-interrupted.json).
- Discovery Frappe: 2.326 métodos, cero ejecutados; mismo código/pins.
  [Manifest por ID/categoría](evidence/frappe-official/frappe-discovery-final.json).
- 26 controles del harness PASS; guardrails PASS. No son tests oficiales.
- 48 archivos anteriores de intentos/observaciones registrados por hash para
  comprobar su conservación; sitios anteriores intactos. Ningún runner activo
  antes de iniciar. Primer y único completo nuevo Frappe CI iniciado; resultado
  todavía pendiente. ERPNext nuevo completo aún UNRUN.

## Runners completos autorizados

Los workflows fijados usan `run-parallel-tests`: Frappe
`.github/workflows/_base-server-tests.yml:112`, ERPNext
`.github/workflows/server-tests-mariadb.yml:192`. Un único shard incluye todos
sus módulos nativos, sin selecciones de módulos/métodos o exclusiones añadidas.
ERPNext usa bootstrap oficial y lightmode; Frappe no usa lightmode. Sus hooks,
fixtures, reinicio de usuario, decoradores y validaciones nativas se conservan.

```bash
set -e
cd /workspace/cencomun-erp-lab
source scripts/frappe-integral/env.sh
export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
"$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe \
  --site ccm-upstream-frappe-final.test --ci-parallel --offline --observe
# Esperar y conservar el resultado Frappe antes de preparar/iniciar ERPNext.
"$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py erpnext \
  --site ccm-upstream-erpnext-final.test --ci-parallel --offline --observe
```

Cada completo reserva un intento exclusivo. Logs/XML/streams crudos y secretos
permanecen privados. Si falta resumen nativo, el contador es desconocido;
discovery/eventos observados no lo sustituyen. No excluir un caso que falle por
HOME/red/capacidad ausente, ni volver a ejecutar completos sin nueva corrección
demostrada. No modificar HOME, pins, upstream, permisos/aserciones, oráculo,
producción, main, Axelor ni repetir restauración cloud/Guardar/Publicar.

## Checkpoint posterior a Frappe, ERPNext en ejecución

Frappe CI completo terminó **FAIL**: contador nativo 2.326; eventos 2.220 PASS,
9 FAIL, 47 ERROR y 50 SKIP. Todos los IDs del discovery tienen resultado en
esta pasada. Hay 2.286 IDs distintos y 40 ejecuciones repetidas de IDs por la
carga nativa; los IDs distintos no sustituyen el contador 2.326.

- [Intento completo nuevo](evidence/frappe-official/frappe-ci-attempt-1.json).
- [Inventario por ID, repeticiones y ausencias](evidence/frappe-official/frappe-final-case-inventory.json).
- [Observaciones permitidas](evidence/frappe-official/frappe-ci-attempt-1-observations.json).
- [Clasificación de los 56 eventos fallidos](evidence/frappe-official/frappe-final-failure-diagnostics.json):
  cinco rechazos offline terminales demostrados; 26 rechazos TCP locales con
  causa de disponibilidad desconocida; otros 25 con causa desconocida. El
  rechazo TCP no se declara un bloqueo inevitable ni una respuesta 403 remota.
  HOME sigue siendo una limitación demostrada histórica; no se atribuyen estos
  dos nuevos FAIL de backup a HOME sin su propia evidencia causal.

Dos correcciones del lector conservaron los resultados nativos: una excepción
impresa no puede reemplazar una clase declarada en el discovery; la salida de
progreso sin salto de línea no puede ocultar el símbolo final de un resultado.
Se completaron nueve eventos inicialmente no leídos (ocho PASS y un fallo),
sin ejecutar tests otra vez. Los JSON derivados iniciales se conservan privados;
log/contador/ejecución no cambiaron. Los controles regresan estos casos.

ERPNext se preparó vacío después de terminar Frappe y recrear fuentes limpias
en los mismos SHAs. Las seis tasas oficiales se insertaron con validadores por
Document API; **BOM cero antes/después**, sin consultas a proveedor. Bootstrap
nativo exit 0 (cero tests), mapa Payments verificado sin reparación. Discovery:
3.255. Primer y único completo ERPNext CI iniciado; su resultado está pendiente.

[FX previo al bootstrap](evidence/frappe-official/erpnext-final-fx-before-bootstrap.json),
[mapa](evidence/frappe-official/erpnext-final-module-preflight-preparation.json),
[aislamiento](evidence/frappe-official/erpnext-preparation-final.json),
[discovery](evidence/frappe-official/erpnext-discovery-final.json).

35 controles del harness PASS tras las correcciones del lector y clasificación;
no se suman a los tests oficiales. La comparación de integridad original y la
lectura autenticada final permanecen pendientes hasta terminar ERPNext.

## Cómo continuar con los problemas documentados

Estos pasos son diagnósticos pendientes, no correcciones ya demostradas ni una
autorización para repetir completos durante esta pasada.

1. **Rechazo offline terminal demostrado:** localizar los cinco IDs Frappe en
   el JSON de clasificación y sus frames nativos. Revisar si el caso consume
   un fixture local oficial o requiere realmente transporte externo. Mantener
   el FAIL actual. Si requiere capacidad externa, describir destino, motivo y
   alcance antes de solicitar una decisión; aquí no se consulta al proveedor
   ni se inventa una respuesta. Una observación de rechazo aislada no demuestra
   que sea la causa de otro fallo.
2. **Rechazo TCP local, disponibilidad desconocida:** localizar ID, URL/host/
   puerto y traza en el log privado. El web log Frappe está vacío; esta versión
   del harness verificó `ping` inicialmente pero no conservó PID/identidad de
   listener ni el exit del servidor durante la suite. No permite atribuir la
   caída a un test o a upstream. En un diagnóstico acotado futuro, registrar
   PID/start ticks, listener y sitio servido al inicio y durante el módulo,
   comprobar que el endpoint pertenece al Bench/sitio esperado y capturar
   salida/exit del servidor. Corregir únicamente la preparación cuya causa
   se demuestre; repetir el módulo afectado antes de proponer otro completo.
3. **Otros fallos con causa UNKNOWN:** agrupar los IDs por excepción/módulo,
   conservar entrada/fixture y estado anterior de esa pasada, y formular una
   hipótesis verificable por grupo. Comparar con un sitio oficial vacío y
   preparación nativa sin cambiar aserciones/validadores. Si la prueba exige
   cambiar pins, upstream, red o filesystem, detener esa línea y documentar
   qué capacidad falta; no convertir UNKNOWN en bloqueo inevitable.
4. **Backup y HOME:** consultar los dos IDs nuevos de backup, que terminaron
   con AssertionError sin Errno 30/13 causal capturado. No asignarles el límite
   histórico de HOME por aparecer una ruta HOME en la traza. Para una prueba
   futura capturar el subcomando, exit y ruta nativa fallida, sin credenciales.
   Si demuestra HOME de solo lectura, conservar el fallo y pedir una decisión
   sobre un entorno compatible; no mover/redefinir HOME ni sortear permisos.
5. **Incompatibilidades declaradas de dependencias:** conservar el `pip check`
   que ya detectaba requests/oauthlib fuera de los rangos del framework.
   Relacionar una incompatibilidad con un ID fallido antes de atribuirle causa.
   Cualquier cambio de pins requiere una propuesta separada; aquí no se hace.
6. **Criterio 13:** conservar BLOCKED y seis PATCH UNRUN. La evidencia existente
   registra únicamente v16.36.0/v16.36.1 compatibles; esta pasada no consulta
   nuevos proveedores ni ensaya otra minor. Ante un futuro tag oficial apto,
   fijar versiones/SHAs y compatibilidad, backup, copia/migración, regresión y
   rollback antes de ejecutar un cambio autorizado. El baseline no lo aprueba.

Los comandos reproducibles de preparación y ejecución están en
[README oficial](../scripts/official-tests/README.md). Las credenciales, trazas
con variables y dumps no se publican. La restauración cloud externa acreditada
se conserva y no se repite; crear estos sitios locales no equivale a restaurarla.
