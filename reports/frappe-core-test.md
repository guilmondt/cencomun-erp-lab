# Core Test de Frappe/ERPNext — LAB-ONLY-v1

**CERRADO_CON_LIMITACIONES: PASS 13/14, FAIL 0/14, BLOCKED 1/14.** Los bloqueados mantienen el denominador; este resultado no aprueba integralmente el ERP. Axelor no se ejecutó ni modificó en esta tarea.

Se ejecutaron 28 grupos de comprobaciones: 28 PASS, 0 FAIL. Cada grupo conserva entradas, observaciones nativas, vínculos/IDs e importes en sus JSON. Los seis escenarios de patch quedan UNRUN por el criterio 13.

| Criterio | Estado | Evidencia reproducible |
| --- | --- | --- |
| 1. Objetos soportados | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json) |
| 2. Core upstream intacto | PASS | [build.json](evidence/frappe-core/build.json) |
| 3. Permisos en servidor | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 4. Transiciones válidas y atómicas | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 5. Dinero determinista y TAX01 nativo | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json) |
| 6. Caja inmutable y auditada | PASS | [audit.json](evidence/frappe-core/audit.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 7. Compras por umbral | PASS | [audit.json](evidence/frappe-core/audit.json), [finance.json](evidence/frappe-core/finance.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 8. Banco idempotente | PASS | [audit.json](evidence/frappe-core/audit.json), [finance.json](evidence/frappe-core/finance.json), [http.json](evidence/frappe-core/http.json) |
| 9. API sin DB directa | PASS | [audit.json](evidence/frappe-core/audit.json), [http.json](evidence/frappe-core/http.json), [recovery.json](evidence/frappe-core/recovery.json) |
| 10. MCP vía adaptador | PASS | [http.json](evidence/frappe-core/http.json) |
| 11. Fixtures compartidos cargados | PASS | [audit.json](evidence/frappe-core/audit.json), [business.json](evidence/frappe-core/business.json), [finance.json](evidence/frappe-core/finance.json), [benchmark.json](evidence/frappe-core/benchmark.json) |
| 12. Búsqueda completa | PASS | [http.json](evidence/frappe-core/http.json) |
| 13. Regresión tras patch | BLOCKED | [patch.json](evidence/frappe-core/patch.json) |
| 14. Setup reproducible | PASS | [audit.json](evidence/frappe-core/audit.json), [recovery.json](evidence/frappe-core/recovery.json), [reproducibility.json](evidence/frappe-core/reproducibility.json) |

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
| search | 1000 | 13.93223 | 18.30527 | 68.01272 | 0 |
| inventory | 1000 | 13.20916 | 18.83025 | 74.26556 | 0 |
| create | 1000 | 24.19097 | 32.79425 | 84.53232 | 0 |

Tiempos crudos, consultas y tiempo DB por muestra: [benchmark-raw.csv](evidence/frappe-core/benchmark-raw.csv). Recursos y metodología: [benchmark.json](evidence/frappe-core/benchmark.json). El recorder nativo mide dentro del servicio RPC; HTTP/autenticación externa están incluidos solamente en el tiempo extremo a extremo. No se grabaron SQL crudos ni credenciales.

## Reproducción y cambios propios

Ejecutar `bash scripts/core-test/run.sh` siguiendo [README](../scripts/core-test/README.md). El runner respalda/restaura únicamente sitios ficticios marcados, carga fixtures por Document APIs, mantiene pruebas independientes y publica comandos/códigos de salida. Regenera evidencia e IDs técnicos, conservando el oráculo.

Aplicación: 46 archivos Python/JSON, 2977 líneas informativas. Diez DocTypes versionados, campos nativos con Custom Field, Workflow, DocPerm, Property Setter y hooks; SQL de negocio manual: 0. No requiere configuración crítica exclusiva de UI. `bench migrate` sincroniza los modelos y ejecuta `core.setup.install` idempotente; no se añade patch manual ni se altera versions.lock.

Por venta STORE se usan 5 acciones del servicio; WEB 6. Nativos: un Sales Order, una Delivery Note, una Sales Invoice y dos Payment Entry. Una llamada ERP RPC por acción del adaptador. MCP stdio JSON-RPC ejecutó las mismas seis rutas, usando un actor sin aprobaciones ni movimientos financieros directos.

Subconjunto oficial de plataforma: 4 tests PASS; alcance: utilidades unitarias. Los cinco tests de registro/paquete también se ejecutan en el runner. Los grupos de negocio son integración real sobre MariaDB/Redis, incluidos HTTP, permisos y concurrencia. No se presenta esto como la suite completa upstream ni como regresión posterior a un patch.

El sitio de reproducción separado restauró el checkpoint y repitió los 14 grupos nativos de negocio/finanzas sin modificar el sitio medido. Credenciales, encryption_key, dumps y logs completos permanecen privados, fuera del repositorio. Solo se publican hashes/metadatos y evidencias ficticias.

## Limitaciones, diagnóstico y resolución

1. **Criterio 13 BLOCKED; patch y regresiones dependientes UNRUN.** La consulta oficial de Frappe en la serie fijada solo ofrece 16.36.0 y 16.36.1. Ver tags, SHAs, comandos y códigos en [patch.json](evidence/frappe-core/patch.json). No se fuerza otra minor/major. Para resolver: (1) terminar el Core Test de Axelor con este mismo manifiesto; (2) consultar tags oficiales posteriores compatibles de ambos ERP; (3) congelar objetivo y dependencias; (4) respaldar/restaurar en copia aislada; (5) actualizar/migrar allí; (6) ejecutar suites completas de plataforma y Cencomun; (7) comprobar rollback y publicar evidencias. Hasta entonces no hay aprobación 14/14 ni paridad integral.

2. **La suite oficial de integración de utilidades no se completó en el sitio con fixtures LAB.** El bootstrap de ERPNext intentó insertar Standard Buying con otra configuración y produjo DuplicateEntryError. `--skip-before-tests` no evita ese bootstrap lazy. Se ejecutó y contó por separado la categoría unit (4 tests); no se contó el primer comando deprecated que devolvió cero sin ejecutar tests. Para la regresión completa: (1) preparar otro sitio upstream vacío; (2) instalar dependencias de test fijadas; (3) cargar los fixtures oficiales antes de los LAB o usar listas de precio LAB con nombres distintos mediante mapping versionado; (4) ejecutar y contar suites; (5) repetir Cencomun con el mismo oráculo. Esta limitación no sustituye ni aprueba el criterio 13.

3. **Alcance técnico del laboratorio.** Cashea y consumidor de eventos son simuladores locales; entrega al menos una vez con deduplicación, no integración real. Serial verifica búsqueda del registro nativo; no seguimiento físico por serial. No se prueba localización fiscal venezolana, remisión del impuesto, devoluciones, combos a cero, integración MRW, producción ni SLA. Las decisiones comerciales aplazadas siguen en el ExecPlan.

4. **Intervenciones realizadas y preservadas.** Se añadieron Currency VES, grupos hoja, cuentas por defecto, listas nativas y cliente mariadb-dump 11.8.6 con checksum. Se corrigieron el mapeo bruto/neto de Payment Entry, precio/listas obligatorias, scope nativo sin permisos de empresa, auditoría de cierre sin diferencia y traducción de UniqueValidationError a 409. El proxy baseline apuntaba a otro sitio: el adaptador usa 127.0.0.1:8000 con Host ccm-core.test. No se modificó ese proxy. Los intentos fallidos se conservan en `evidence/frappe-core/attempts` y runs; los pasos exactos están en el README.

Versiones efectivas: Frappe/ERPNext 16.36.1, MariaDB 11.8.6, Redis 8.0.2, Python 3.14.0, Node 24.19.0, Bench 5.29.0, Cencomun 0.0.1. Fuente, SHAs, hashes, estados y resultados completos: [summary.json](evidence/frappe-core/summary.json).
