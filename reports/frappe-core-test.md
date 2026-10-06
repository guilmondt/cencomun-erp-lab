# Core Test de Frappe/ERPNext — LAB-ONLY-v1

**CERRADO_CON_LIMITACIONES: PASS 13/14, FAIL 0/14, BLOCKED 1/14, UNRUN 0/14.** Los bloqueados mantienen el denominador; este resultado no aprueba integralmente el ERP. Axelor no se ejecutó ni modificó en esta tarea.

Cobertura obligatoria: 34 grupos; 34 PASS, 0 FAIL, 0 UNRUN. Cada grupo conserva entradas, observaciones nativas, vínculos/IDs e importes en sus JSON. Los seis escenarios de patch quedan UNRUN por el criterio 13. [coverage.json](evidence/frappe-core/coverage.json) impide conservar PASS con casos ausentes o evidencia anterior a la corrección.

| Criterio | Estado | Evidencia reproducible |
| --- | --- | --- |
| 1. Objetos soportados | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json) |
| 2. Core upstream intacto | PASS | [build.json](evidence/frappe-core/build.json) |
| 3. Permisos en servidor | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 4. Transiciones válidas y atómicas | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 5. Dinero determinista y TAX01 nativo | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json) |
| 6. Caja inmutable y auditada | PASS | [audit.json](evidence/frappe-core/audit.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 7. Compras por umbral | PASS | [audit.json](evidence/frappe-core/audit.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 8. Banco idempotente | PASS | [audit.json](evidence/frappe-core/audit.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json) |
| 9. API sin DB directa | PASS | [audit.json](evidence/frappe-core/audit.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 10. MCP vía adaptador | PASS | [audit.json](evidence/frappe-core/audit.json), [http.json](evidence/frappe-core/http.json) |
| 11. Fixtures compartidos cargados | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json), [benchmark.json](evidence/frappe-core/benchmark.json) |
| 12. Búsqueda completa | PASS | [http.json](evidence/frappe-core/http.json) |
| 13. Regresión tras patch | BLOCKED | [patch.json](evidence/frappe-core/patch.json) |
| 14. Setup reproducible | PASS | [audit.json](evidence/frappe-core/audit.json), [recovery.json](evidence/frappe-core/recovery.json), [reproducibility.json](evidence/frappe-core/reproducibility.json) |

## Corrección de cobertura — revisión 2

Contrato compartido: [coverage-required.json](../fixtures/ccm-core-v1/coverage-required.json). El oráculo económico y los bytes de los fixtures anteriores se conservan.

| Grupo obligatorio | Estado | Comprobación adicional |
| --- | --- | --- |
| AUDIT01-03-NATIVE | PASS | Motivo y JSON antes/después útiles; secuencia de estados, montos, notas y vínculos nativos de compras/caja/tasa/banco; inmutabilidad. |
| STATE-UNKNOWN-ATOMIC | PASS | Estado desconocido por API y Select nativo: rechazo, snapshot de efectos sin cambios. |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | PASS | STORE/WEB desde NEW/REVIEWED y WEB saltando PREPARING: 409 sin efectos. |
| STATE-WEB-NO-GUIDE | PASS | PREPARING→SHIPPED sin guía: 422, sin salida, factura, pago o evento nuevo. |
| STATE-CANCEL-BEFORE-HANDOVER | PASS | Cancelaciones APPROVED STORE/WEB y PREPARING WEB: SO nativo cancelado, stock intacto, sin factura/entrega/pago; motivo y antes/después exactos. |
| MCP01-06-STDIO | PASS | Equivalencia completa API/MCP en seis rutas; creaciones y replays en ambos sentidos con los mismos IDs. Metadata excluida y replay verificado por separado. |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | PASS | Ocho negativas en objetos elegibles: tool -32602 y RPC 403 para aprobación, entrega/despacho, liquidación, caja, tasa y banco. |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | PASS | Snapshots nativos inalterados, ocho auditorías de denegación y ausencia de auditorías/eventos de éxito. |
| IDEM04-EVENTS-RECOVERY | PASS | Éxito antes de reiniciar consumidor; efecto persistido; mismos event_id repetidos después: recepciones2 y aplicaciones1. |

## Casos económicos y TAX01

Todos los importes son USD ficticios; impuesto sintético incluido del 10%. Se verificaron facturas, entregas, Stock Ledger Entry, GL Entry y Payment Entry nativos, no asientos calculados externamente. Los JSON guardan los asientos completos por documento.

| Caso | Total | Ingreso | Pasivo impuesto | Costo | Comisión | Envío | Transferencia Cashea | Resultado contable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CO00 | 125.00 | 125.00 | 0.00 | 70.00 | 8.00 | 0.00 | 67.00 | 47.00 |
| CO01 | 125.00 | 125.00 | 0.00 | 70.00 | 10.50 | 0.70 | 63.80 | 43.80 |
| TAX01-S | 137.50 | 125.00 | 12.50 | 70.00 | 8.80 | 0.00 | 73.70 | 46.20 |
| TAX01-W | 137.50 | 125.00 | 12.50 | 70.00 | 11.55 | 0.70 | 70.25 | 42.75 |

En cada escenario: stock 5/5/5 y valor 500.00 → 3/4/5 y valor 430.00; una entrega, una factura y dos pagos; saldo final de factura 0.00. TAX01-S/TAX01-W también se ejecutaron concurrentemente y sus reintentos tras reiniciar mantuvieron un solo pasivo de 12.50. El indicador Cashea 58.70/55.25 contiene el impuesto y se distingue del resultado contable 46.20/42.75.

Caja: USD -2.00, VES +10.00, POS/transferencia 0; pendiente Cashea 125.00 separado del efectivo. Confirmación, rechazo de edición y auditoría inmutable comprobados. Compras: seis límites, cargos/descuento, VES, cambio de aprobación y autoaprobación. Banco: exacto/probable/ambiguo/duplicado/sin pareja, decisiones manuales, signo negativo y 1.000 filas concurrentes sin duplicación.

## Rendimiento observado

1000 productos, 100 clientes, 1000 pedidos NEW iniciales, 1000 filas bancarias; semilla 100. Por operación: 20 calentamientos + 1000 muestras seriales. Los IDs por muestra son deterministas; los demás valores de creación son iguales. No se mide replay como creación. HTTP local, dos workers; no se establece SLA de producción.

| Operación | Muestras | p50 ms | p95 ms | p99 ms | Errores |
| --- | --- | --- | --- | --- | --- |
| search | 1000 | 15.62455 | 20.90799 | 79.9335 | 0 |
| inventory | 1000 | 15.92619 | 24.0025 | 92.42482 | 0 |
| create | 1000 | 25.70902 | 32.1956 | 85.75072 | 0 |

Tiempos crudos, consultas y tiempo DB por muestra: [benchmark-raw.csv](evidence/frappe-core/benchmark-raw.csv). Recursos y metodología: [benchmark.json](evidence/frappe-core/benchmark.json). El recorder nativo mide dentro del servicio RPC; HTTP/autenticación externa están incluidos solamente en el tiempo extremo a extremo. No se grabaron SQL crudos ni credenciales.

## Reproducción y cambios propios

Ejecutar `bash scripts/core-test/run.sh` siguiendo [README](../scripts/core-test/README.md). El runner respalda/restaura únicamente sitios ficticios marcados, carga fixtures por Document APIs, mantiene pruebas independientes y publica comandos/códigos de salida. Regenera evidencia e IDs técnicos, conservando el oráculo.

Aplicación: 46 archivos Python/JSON, 3019 líneas informativas. Diez DocTypes versionados, campos nativos con Custom Field, Workflow, DocPerm, Property Setter y hooks; SQL de negocio manual: 0. No requiere configuración crítica exclusiva de UI. `bench migrate` sincroniza los modelos y ejecuta `core.setup.install` idempotente; no se añade patch manual ni se altera versions.lock.

Por venta STORE se usan 5 acciones del servicio; WEB 6. Nativos: un Sales Order, una Delivery Note, una Sales Invoice y dos Payment Entry. Una llamada ERP RPC por acción del adaptador. MCP stdio JSON-RPC ejecutó las mismas seis rutas, usando un actor sin aprobaciones ni movimientos financieros directos.

Subconjunto oficial de plataforma: 4 tests PASS; alcance: utilidades unitarias. Los cinco tests de registro/paquete también se ejecutan en el runner. Los grupos de negocio son integración real sobre MariaDB/Redis, incluidos HTTP, permisos y concurrencia. No se presenta esto como la suite completa upstream ni como regresión posterior a un patch.

Última pasada completa oficial desde 9cbfbbd, en sitios nuevos con fixtures oficiales y modo offline: Frappe FAIL, 2326 ejecutadas (2220 PASS, 9 FAIL, 47 ERROR, 50 SKIP); ERPNext FAIL, 3255 ejecutadas (3251 PASS, 4 ERROR). Contadores nativos completos; cero IDs descubiertos sin resultado. [Cierre, clasificación y conservación](frappe-official-final-ci.md) y [todos los intentos](frappe-official-suites.md). Los PASS modulares anteriores no se suman. Estas suites de baseline no acreditan las seis pruebas posteriores al patch. El runtime original, sus pins y 17 archivos compartidos mantienen sus hashes; lectura autenticada P001 USD50.00/stock5 cotejada nativamente. Los 34 grupos pertenecen a la ejecución 20261006T042836Z y no se repitieron sin cambio de runtime.

El sitio de reproducción separado restauró el checkpoint y repitió 13 grupos de negocio y 5 de finanzas sin modificar el sitio medido. Credenciales, encryption_key, dumps y logs completos permanecen privados, fuera del repositorio. Solo se publican hashes/metadatos y evidencias ficticias.

## Limitaciones, diagnóstico y resolución

1. **Criterio 13 BLOCKED; sus seis escenarios UNRUN.** Los tags oficiales de Frappe y ERPNext solo ofrecen 16.36.0 y 16.36.1 en la serie fijada. Ver comandos/SHAs/códigos en [patch.json](evidence/frappe-core/patch.json). No se inventa un patch ni se fuerza otra minor. Para resolver: (1) consultar nuevos tags oficiales compatibles de ambos proyectos; (2) fijar objetivo/SHAs y compatibilidad; (3) definir backup, copia, migración, regresión y rollback; (4) ejecutar únicamente el cambio autorizado; (5) comprobar suites y restauración. Una propuesta para otra minor requiere plan separado y aprobación previa. El baseline actual no cuenta como esas regresiones; no hay aprobación 14/14.

2. **Standard Buying resuelto; resultados oficiales separados.** Se prepararon sitios vacíos sin Cencomun, con fixtures oficiales y un Bench copiado para aislar tests de comandos. No se cambió la lista LAB ni el oráculo. Las suites oficiales conservan sus FAIL/BLOCKED/UNRUN reales, cantidades e IDs en [frappe-official-suites.md](frappe-official-suites.md); los cuatro unitarios históricos no las sustituyen. `pip check` detecta incompatibilidades preexistentes de requests/oauthlib que se documentan sin cambiar pins. Diagnóstico y repetición paso a paso: [README oficial](../scripts/official-tests/README.md). Esta evidencia no sustituye ni aprueba el criterio 13.

3. **Alcance técnico del laboratorio.** Cashea y consumidor de eventos son simuladores locales; entrega al menos una vez con deduplicación, no integración real. Serial verifica búsqueda del registro nativo; no seguimiento físico por serial. No se prueba localización fiscal venezolana, remisión del impuesto, devoluciones, combos a cero, integración MRW, producción ni SLA. Las decisiones comerciales aplazadas siguen en el ExecPlan.

4. **Intervenciones realizadas y preservadas.** Se añadieron Currency VES, grupos hoja, cuentas por defecto, listas nativas y cliente mariadb-dump 11.8.6 con checksum. Se corrigieron el mapeo bruto/neto de Payment Entry, precio/listas obligatorias, scope nativo sin permisos de empresa, auditoría de cierre sin diferencia y traducción de UniqueValidationError a 409. El proxy baseline apuntaba a otro sitio: el adaptador usa 127.0.0.1:8000 con Host ccm-core.test. No se modificó ese proxy. Los intentos fallidos se conservan en `evidence/frappe-core/attempts` y runs; los pasos exactos están en el README.

5. **Restauración cloud: PASS externo aportado por el coordinador.** Evidencia exacta y alcance en [frappe-cloud-restoration.md](frappe-cloud-restoration.md). No se reejecutó aquí ni modifica suites oficiales o criterio 13. El criterio 14 acredita setup/replay de sitio LAB y mantiene un alcance distinto. El snapshot verificado es fcf690dbc58b2b2dcf8d045c49976e3613e804cf; no se repitió Guardar/Publicar. Precio P001 USD50.00 y stock5 coinciden por adaptador y API nativa en el almacén HTTP. Los dos fallos HTTP iniciales se conservan con causa desconocida; no se inventa una explicación.

Versiones efectivas: Frappe/ERPNext 16.36.1, MariaDB 11.8.6, Redis 8.0.2, Python 3.14.0, Node 24.19.0, Bench 5.29.0, Cencomun 0.0.1. Fuente, SHAs, hashes, estados y resultados completos: [summary.json](evidence/frappe-core/summary.json).
