# Diagnóstico de suites oficiales fijadas

Este registro conserva causas comprobadas y pasos de repetición. Los resultados
actualizados, comandos y conteos están en [el informe de suites](frappe-official-suites.md).
No modifica pins, validadores, permisos, negocio, Axelor o producción.

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
