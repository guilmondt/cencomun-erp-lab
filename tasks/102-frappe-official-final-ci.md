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

## Progreso conservado

- Preflight desde 9cbfbbd, pins, fuentes originales limpias y ausencia de
  runners comprobados. Snapshot de integridad original anterior conservado.
- Checkpoint inicial 1953167: sitio Frappe nuevo, preparación nativa y
  discovery; fallo previo de Click conservado con cero tests ejecutados.
- Checkpoint c585df7: Frappe completo FAIL, contador nativo 2.326 (2.220 PASS,
  9 FAIL, 47 ERROR, 50 SKIP). Cero IDs descubiertos sin resultado. Dos
  correcciones del lector recuperaron resultados del mismo log, sin reejecución.
  35 controles del harness PASS; no se cuentan como pruebas oficiales.
- ERPNext nuevo: fuentes limpias recreadas después de terminar Frappe, seis
  FX oficiales intactas antes de imports/bootstrap, mapa nativo verificado,
  bootstrap exit 0/cero tests, discovery 3.255. Única pasada completa iniciada.
  Resultado, comparación original posterior y lectura autenticada pendientes.
- PR #4 permanece borrador. Todos los completos anteriores conservan su propio
  resultado; no se suman PASS modulares ni se vuelve a acreditar cloud.

## Cierre

Los ocho pasos concluyeron; los párrafos de checkpoint anteriores conservan
el estado que había en cada checkpoint. Una ejecución completa nueva por app:
Frappe 2.326 (2.220 PASS / 9 FAIL / 47 ERROR / 50 SKIP), ERPNext 3.255
(3.251 PASS / 0 FAIL / 4 ERROR / 0 SKIP). Ambos completos FAIL, resumen nativo
completo, cero IDs descubiertos sin resultado. No se suman PASS previos.

ERPNext: tres ERROR por ausencia de tasa nativa aplicable con rechazo offline
demostrado; uno UNKNOWN con desequilibrio contable 100. Frappe: cinco rechazos
offline terminales, 26 rechazos TCP locales de causa desconocida y 25 UNKNOWN.
Diagnósticos iniciales/revisados e intentos de cierre conservados.

Original: 49.823 archivos con hash idéntico antes/después, pins/fuentes/oráculo
intactos; consulta autenticada P001 USD50.00/stock5 cotejada nativamente. No se
repite Core sin cambio de runtime: 34 grupos de su ejecución previa mantienen
su alcance; 13 PASS/1 BLOCKED y seis PATCH UNRUN. 38 controles del harness y
guardrails PASS. Diez sitios oficiales, 48 evidencias y 32 logs históricos
conservados. Worker/SMTP exclusivos detenidos, cero runners oficiales activos.

Publicación final y límites: [informe completo](../reports/frappe-official-final-ci.md).
PR #4 borrador; no cambio minor/pins, producción/main/Axelor/upstream, tasas
inventadas/proveedores nuevos, HOME/permisos ni repetición cloud.
