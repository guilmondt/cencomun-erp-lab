# Métricas Core Axelor — CI37469716840

SHA `4230b2b32b1fbfd6b45c4f6efea6052498f6e4d9`. Fuentes originales de ambas fases en
[runs/37469716840](evidence/axelor-core/runs/37469716840/isolated-repeat.json).
Todas las métricas de ejecución siguientes provienen de este CI. Los timings
de gates/arranque no sustituyen el benchmark y no se imputan muestras ausentes.
El éxito de un benchmark o de la repetición no aprueba los grupos funcionales FAIL.

| Fase | Benchmark observado | Muestras con calentamiento |
| --- | --- | --- |
| primary | PASS | 3060 |
| repeat | PASS | 3060 |

Perfil fijo seed100:1000productos/100clientes/1000pedidosNEW/1000filas bancarias;20calentamientos+1000muestras seriales por operación, percentiles nearest-rank.

| Fase | Operación | Muestras | p50 ms | p95 ms | p99 ms | Errores |
| --- | --- | --- | --- | --- | --- | --- |
| primary | search | 1000 | 23.65852 | 38.68102 | 80.09883 | 0 |
| primary | inventory | 1000 | 27.02869 | 32.38729 | 82.22944 | 0 |
| primary | create | 1000 | 30.79762 | 42.34433 | 87.66176 | 0 |
| repeat | search | 1000 | 24.4198 | 39.2466 | 82.00365 | 0 |
| repeat | inventory | 1000 | 28.55381 | 35.38583 | 88.56327 | 0 |
| repeat | create | 1000 | 31.67498 | 40.04455 | 89.52004 | 0 |

Los archivos benchmark.json/benchmark-raw.csv conservan tiempos crudos, HTTP,
query_count/db_ms/server_ms. JDBC usa callbacks Hibernate SessionEventListener;
la frontera de servicio excluye autenticación/serialización e hilos aislados de
secuencia. elapsed_ms incluye la ruta HTTP del adaptador. No son mediciones de
la misma frontera, ni se afirma igualdad de recursos con Frappe.

Recursos primary: `{"platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.41", "python": "3.13.5", "logical_cpus": 4, "cpu_affinity": 4, "memory_total_kb": 16377684, "cpu.max": "max 100000", "memory.max": "max"}`.

Recursos repeat: `{"platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.41", "python": "3.13.5", "logical_cpus": 4, "cpu_affinity": 4, "memory_total_kb": 16377684, "cpu.max": "max 100000", "memory.max": "max"}`.

Métricas del servicio/JDBC derivadas de las1000muestras, excluyendo20warmups.
Cada frontera conserva su unidad propia; percentiles nearest-rank.

| Fase | Operación | Queries min/mediana/max | Servicio p50 ms | JDBC p50 ms |
| --- | --- | --- | --- | --- |
| primary | search | 16/16/16 | 7.752604 | 5.725655 |
| primary | inventory | 18/18/19 | 11.189671 | 8.090076 |
| primary | create | 47/47/48 | 14.452792 | 4.850123 |
| repeat | search | 16/16/16 | 7.918503 | 5.686158 |
| repeat | inventory | 17/18/18 | 11.76254 | 8.349982 |
| repeat | create | 47/47/48 | 14.692569 | 5.078222 |

CI total:3223s. Suites Java ejecutadas por fase de build, sin duplicar la compilación para réplica:

| Suite | Tests | Fallos | Errores | Skips |
| --- | --- | --- | --- | --- |
| CencomunModuleTest | 2 | 0 | 0 | 0 |
| CoreOrderPolicyTest | 9 | 0 | 0 | 0 |
| CoreFinancePolicyTest | 2 | 0 | 0 | 0 |
| CoreNativeScopeTest | 2 | 0 | 0 | 0 |
| MoneyPolicyTest | 7 | 0 | 0 | 0 |
| NativeAddressTemplateTest | 8 | 0 | 0 | 0 |
| NativePermissionFilterTest | 5 | 0 | 0 | 0 |
| NativeOrderModelTest | 4 | 0 | 0 | 0 |
| NativeBankCsvTest | 3 | 0 | 0 | 0 |
| NativeFinanceModelTest | 7 | 0 | 0 | 0 |
| NativeInvoiceRuntimeTest | 2 | 0 | 0 | 0 |
| TestTaxNumberHelper | 16 | 0 | 0 | 0 |

Upstream diffs efectivos: `{"host": 0, "aos": 0}`; pins contra el blob base conservados. WAR SHA256 `10f062c955a445f3763af47bab1b8fa3f74922158bef7cbe4af6aa98928047d0`.

Código propio: archivos/líneas físicas y no vacías, incluidos comentarios; sólo
fuentes tracked del SHA, sin generados, dependencias, build, evidencias o Frappe.

| Categoría | Archivos | Líneas físicas | No vacías |
| --- | --- | --- | --- |
| CI runner | 12 | 682 | 655 |
| Core harness | 16 | 3705 | 3464 |
| Java runtime | 52 | 3638 | 3493 |
| Java tests | 11 | 544 | 505 |
| Python regression tests | 8 | 1249 | 1182 |
| module resources | 5 | 237 | 237 |

99 archivos Axelor modificados desde e0190090; inventario y hashes en source-metrics.json.

Intervenciones del bloque: cinco causas B37 corregidas juntas y un conteo antiguo
B38 corregido tras conservar su CI sin arranque; B39 corrige dos causas de
transporte sin cambiar negocio ni expectativas.11modelos ORM nativos según
SUPPORTED-CONFIGURATION ejecutado; no migración SQL manual ni ensayo de upgrade.
Fixture/configuración/secuencias se confirman antes de stock; la transacción
venta/entrega/factura/liquidación y sus rechazos conserva su atomicidad.
Reinicios propios y restore a otra DB prueban la misma versión, no actualización.
