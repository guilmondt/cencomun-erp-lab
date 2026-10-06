# ExecPlan — última ejecución completa oficial desde 9cbfbbd

Autorizada explícitamente el 2026-10-06. Solo `lab/frappe-baseline`;
PR #4 borrador. Una ejecución completa de Frappe seguida de una de ERPNext,
sin filtros de módulos/métodos, con los runners CI fijados (un shard completo).
No sumar resultados modulares anteriores a estos nuevos completos.

1. Verificar HEAD 9cbfbbd, pins, ausencia de runners y estado original Cencomun.
   Conservar hashes/estado anterior y todos los sitios/intentos existentes.
2. Conservar las fuentes de prueba generadas y recrear la copia oficial desde
   los mismos SHAs limpios. Conservar el venv/pins. Crear sitios vacíos separados
   `ccm-upstream-frappe-final.test` y `ccm-upstream-erpnext-final.test`.
3. Frappe: preparación nativa before_tests y CI no-lightmode. ERPNext: helper
   prepare_payments sin colisión, seis registros JSON oficiales exactos mediante
   Document API antes de importar tests/bootstrap, BOM cero antes/después;
   bootstrap CI oficial y después CI lightmode. Verificar mapa nativo y apps.
4. Preparación, discovery y runners con guard offline. Conservar discovery por
   ID, contador nativo, resultados/skips por ID, errores de bootstrap/import y
   métodos sin resultado. No inventar conteos tras interrupción.
5. Arrancar worker exclusivo del Bench oficial y SMTP ficticio local; ejecutar
   Frappe completo una vez. Esperar su finalización antes de ERPNext. Si tests
   generan fuentes, conservarlas y recrear copia limpia en los mismos SHAs
   antes de ERPNext. No repetir un completo por un fallo sin nueva autorización
   o corrección demostrada.
6. Clasificar remanentes con traza/observación permitida: límite demostrado o
   causa desconocida. No excluir tests que requieran red/HOME/capacidad ausente.
   Conservar HOME, validadores, aserciones, permisos, pins y oráculo; criterio
   13 BLOCKED y seis PATCH UNRUN. Sin otra minor ni restauración cloud.
7. Verificar después originales/venv/configuración/pins/fixtures Cencomun.
   Si cambiaron su runtime, repetir regresión; si no, documentar aislamiento y
   lectura autenticada de precio/stock. Los 34 grupos previos mantienen su
   alcance y no se atribuyen a esta nueva pasada oficial.
8. Publicar checkpoints y cierre saneado solo en lab, con logs/credenciales/
   dumps privados fuera de Git. Guardrails y controles del harness, PR borrador.

Estado inicial: preflight y rama/HEAD comprobados; ningún runner activo.
Las nuevas suites siguen pendientes hasta tener sus propios resultados.
