# Diagnóstico de suites oficiales fijadas

Este registro conserva causas comprobadas y pasos de repetición. Los resultados
actualizados, comandos y conteos están en [el informe de suites](frappe-official-suites.md).
No modifica pins, validadores, permisos, negocio, Axelor o producción.

La continuación desde 8158 y sus resultados acotados, configuración/Error Log,
colisión del helper Payments, autenticación limpia y orden de fixtures están en
[la investigación de preparación](frappe-official-preparation-investigation.md).
Las causas nuevas no convierten los completos históricos FAIL en PASS.

| Problema | Evidencia y alcance | Causa comprobada / límite |
| --- | --- | --- |
| Standard Buying | Sitios oficiales primario y fresh; inspecciones JSON | Colisión LAB resuelta con sitios vacíos y bootstrap oficial, lista INR. No se cambia la lista/oráculo LAB. |
| ERPNext serial: 520 PermissionError | Intento completo 3; 3.255 tests, FAIL | La traza demuestra rechazo nativo al crear documentos. El runner serial no prepara unspecified-category ni restablece usuario por módulo; el runner CI sí lo hace. La repetición CI determinará cuánto resuelve; no se atribuyen todos los errores a esa sola diferencia. |
| Payment Gateway ausente | 22 ProgrammingError en ERPNext 3 | Faltaba Payments, instalado por la CI upstream. Se añadió solo el SHA version-16 compatible y sus SDKs fijados a la copia oficial. Develop exige v17 y no se usa. |
| DocType VirtualDoctypeTest ausente en bootstrap legacy | Frappe completo 4, siete métodos sin resultado | Integration exportó archivos y eliminó su registro. Archivar/reclonar copias en los mismos SHAs permitió ejecutar los siete tests de timeline: PASS modular, sin aprobar el completo. |
| request=None al preparar un sitio usado | Frappe completo 3 y módulo auth 1: BLOCKED | Un workflow residual de User imprime un documento al recrear fixtures; router accede a request.environ con request=None. No se desactiva el workflow ni se cambia router. El módulo auth solo completó una unitaria antes del bloqueo. |
| Backups bajo HOME | Dos tests backup FAIL; probe Errno 30 | `/home/agent` es filesystem de solo lectura. Conceder permiso acotado no cambia el montaje. No se cambia HOME ni la expectativa upstream. |
| HTTP 403, AuthError y Domain forbidden | Frappe completo 4 | Observados; causa final no establecida. Ping en el sitio oficial respondió 200 con requests heredando el proxy y también directo; eso no demuestra que el proxy causó los fallos de autenticación. |
| Otros fallos nativos | IDs, excepciones y trazas saneadas en JSON de cada intento | Incluyen assertions, fixtures Milestone Tracker, email, contexto request y restauración SQL. Siguen FAIL/ERROR; no se inventa una causa general ni se atribuyen sin prueba a requests/oauthlib. |

Resultado final de la repetición ERPNext CI: **3.255 tests, FAIL**, 3.188
eventos PASS, 1 FAIL y 66 ERROR, sin SKIP; duración 2.507,481 segundos. No
persistieron los PermissionError ni el SQL de Payment Gateway ausente.
Se conservaron 67 cabeceras de fallo con ID y tipo, sin variables privadas:

| Excepción | Cantidad | Observación comprobada |
| --- | --- | --- |
| ValidationError | 26 | 19 mensajes de tasas USD/INR, INR/USD o QAR/INR obligatorias; cinco Received Amount; un desbalance de débito/crédito de 100 y una fila sin débito/crédito. |
| DoesNotExistError | 22 | `Module Payments not found` al importar Payment Gateway en el setUp de solicitudes de pago, pese a app instalada y tabla presente. |
| ZeroDivisionError | 14 | Divisiones por cero en las trazas; no se rellenan tasas ni valores para eludirlas. |
| ReportingCurrencyExchangeNotFoundError | 3 | Tasa USD→INR no encontrada para 2026-10-06. |
| NonNegativeError | 1 | Basic Rate negativo en Stock Entry Detail, fila 3; se conserva el rechazo nativo. |
| AssertionError | 1 | `TestBOM.test_update_bom_cost_in_all_boms`: 0.0 frente a 10.0 esperado. |

Una lectura posterior en otro proceso confirmó que Payments está instalado,
su módulo se resuelve a `payments` y Payment Gateway declara `Payments`:
[diagnóstico](evidence/frappe-official/payments-module-diagnostic.json).
La repetición íntegra de `erpnext.accounts.doctype.payment_request.test_payment_request`
ejecutó **22 tests: 17 PASS, 5 ERROR por tasas obligatorias**. Ninguno volvió a
fallar por módulo ausente. Esto demuestra que el error de resolución no persiste
en ese proceso nuevo; no identifica por sí solo quién alteró el contexto del
runner completo ni aprueba sus 22 resultados originales. Se conserva el FAIL
completo y el FAIL modular; no se introducen tasas inventadas o bypasses.

Para continuar con estos fallos:

1. Reproducir el módulo afectado en el sitio oficial, con iguales pins/fixtures
   y sin otra suite activa; usar el comando exacto de su JSON.
2. Para Payments, cotejar apps instaladas, `sites/apps.txt`, modules.txt y el
   resolvedor nativo antes/después de los módulos precedentes. Si se identifica
   preparación/caché incorrecta, corregir solo ese aspecto y repetir; no cambiar
   get_module_app ni ignorar la excepción.
3. Para tasas, revisar los fixtures oficiales y el proveedor/configuración
   esperado por esos tests; conservar fecha, moneda, mensaje y respuesta
   saneada. No reutilizar las tasas sintéticas del Core Test en la suite
   oficial ni declarar aprobados los casos sin una entrada oficial válida.
4. Para BOM y valores negativos, comparar el fixture y documentos nativos
   usados por el test, aislando contaminación entre módulos. Mantener la
   aserción 10.0 y el validador no negativo.
5. Si la solución requiere cambiar dependencias/framework, preparar un plan
   aparte y obtener la aprobación exigida antes de cambiar pins. Los resultados
   actuales continúan FAIL hasta ejecutarse la cobertura correspondiente.

Para resolver o repetir un fallo:

1. Abrir el JSON del intento y localizar el ID, comando, sitio, exit y excepción.
   Conservar el archivo; nunca sobrescribir logs, XML o resultados previos.
2. Consultar código y fixtures de los SHAs fijados. Distinguir una causa
   demostrada de una hipótesis; no cambiar aserciones, permisos o datos esperados.
3. Comprobar que no hay runner activo. Detener solo el worker oficial antes de
   refrescar fuentes/dependencias. El lock del harness rechaza concurrencia;
   no forzarlo ni iniciar otra suite sobre los mismos fixtures.
4. Si hay archivos generados, usar `isolate_bench.py --refresh-test-sources`:
   conserva las copias anteriores fuera de Git y recrea fuentes en iguales SHAs.
   Para un sitio contaminado, conservarlo y preparar un sitio oficial vacío y
   aislado con los fixtures oficiales; no borrar workflows ni alterar el LAB.
5. Repetir el módulo indicado con `run.py --module <módulo oficial>`, registrar
   cantidad real y resultados. Un bootstrap de cero tests y una ejecución
   interrumpida no aprueban métodos. Una repetición modular no aprueba el completo.
6. Para backups con rutas HOME, usar un ejecutor con las cinco rutas escribibles,
   preparadas a modo 0700, y repetir `frappe.commands.test_commands` con iguales
   versiones. Los pasos y nombres de rutas están en el [README](../scripts/official-tests/README.md).
   No publicar dumps, credenciales, logs privados ni claves.
7. Repetir Cencomun tras cambios de preparación que afecten su runtime. Publicar
   su matriz separada: ni un FAIL oficial, ni restauración cloud, ni cuatro
   unitarios se cuentan como regresión después de un patch inexistente.

La [restauración externa](frappe-cloud-restoration.md) conserva su JSON exacto,
atribución y límites. El criterio 13 sigue BLOCKED y sus seis escenarios UNRUN.
