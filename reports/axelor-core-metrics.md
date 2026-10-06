# Métricas Core Axelor — CI37462836624

SHA `068e76822da103c44934bf81a6bb0db4b8e12588`. Fuentes originales de ambas fases en
[runs/37462836624](evidence/axelor-core/runs/37462836624/isolated-repeat.json).
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
| primary | search | 1000 | 24.29372 | 40.30369 | 71.40727 | 0 |
| primary | inventory | 1000 | 27.64275 | 34.4417 | 74.60038 | 0 |
| primary | create | 1000 | 31.89197 | 38.81334 | 80.82316 | 0 |
| repeat | search | 1000 | 24.50675 | 35.18052 | 73.39737 | 0 |
| repeat | inventory | 1000 | 27.87362 | 34.5367 | 76.26783 | 0 |
| repeat | create | 1000 | 31.99067 | 43.16692 | 80.78528 | 0 |

Los archivos benchmark.json/benchmark-raw.csv conservan tiempos crudos, HTTP,
query_count/db_ms/server_ms. JDBC usa callbacks Hibernate SessionEventListener;
la frontera de servicio excluye autenticación/serialización e hilos aislados de
secuencia. elapsed_ms incluye la ruta HTTP del adaptador. No son mediciones de
la misma frontera, ni se afirma igualdad de recursos con Frappe.

Recursos primary: `{"platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.41", "python": "3.13.5", "logical_cpus": 4, "cpu_affinity": 4, "memory_total_kb": 16372440, "cpu.max": "max 100000", "memory.max": "max"}`.

Recursos repeat: `{"platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.41", "python": "3.13.5", "logical_cpus": 4, "cpu_affinity": 4, "memory_total_kb": 16372440, "cpu.max": "max 100000", "memory.max": "max"}`.

CI total:2325s. Suites Java ejecutadas por fase de build, sin duplicar la compilación para réplica:

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

Upstream diffs efectivos: `{"host": 0, "aos": 0}`; pins contra el blob base conservados. WAR SHA256 `9d05405761270ff394c522e46fc9ab94106e9e91fae55f7510580d86aca1f153`.

Código propio: archivos/líneas físicas y no vacías, incluidos comentarios; sólo
fuentes tracked del SHA, sin generados, dependencias, build, evidencias o Frappe.

| Categoría | Archivos | Líneas físicas | No vacías |
| --- | --- | --- | --- |
| CI runner | 12 | 682 | 655 |
| Core harness | 16 | 3664 | 3428 |
| Java runtime | 52 | 3638 | 3493 |
| Java tests | 11 | 544 | 505 |
| Python regression tests | 8 | 1193 | 1126 |
| module resources | 5 | 237 | 237 |

99 archivos Axelor modificados desde e0190090; inventario y hashes en source-metrics.json.

Intervenciones del bloque: cinco causas B37 corregidas juntas y un conteo antiguo
B38 corregido tras conservar su CI sin arranque.11modelos ORM nativos según
SUPPORTED-CONFIGURATION ejecutado; no migración SQL manual ni ensayo de upgrade.
Fixture/configuración/secuencias se confirman antes de stock; la transacción
venta/entrega/factura/liquidación y sus rechazos conserva su atomicidad.
Reinicios propios y restore a otra DB prueban la misma versión, no actualización.
