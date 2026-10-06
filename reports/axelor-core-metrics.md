# Métricas Core Axelor — CI37479552848

SHA `a2f462f67526af94409bd050bf277d78f4782387`. Fuentes originales de ambas fases en
[runs/37479552848](evidence/axelor-core/runs/37479552848/isolated-repeat.json).
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
| primary | search | 1000 | 24.75915 | 39.95614 | 87.95074 | 0 |
| primary | inventory | 1000 | 28.8615 | 34.90337 | 89.05583 | 0 |
| primary | create | 1000 | 31.68583 | 40.05151 | 91.25885 | 0 |
| repeat | search | 1000 | 26.30185 | 42.8621 | 87.28264 | 0 |
| repeat | inventory | 1000 | 29.02417 | 36.85416 | 86.69378 | 0 |
| repeat | create | 1000 | 32.63316 | 40.86747 | 89.65039 | 0 |

Los archivos benchmark.json/benchmark-raw.csv conservan tiempos crudos, HTTP,
query_count/db_ms/server_ms. JDBC usa callbacks Hibernate SessionEventListener;
la frontera de servicio excluye autenticación/serialización e hilos aislados de
secuencia. elapsed_ms incluye la ruta HTTP del adaptador. No son mediciones de
la misma frontera, ni se afirma igualdad de recursos con Frappe.

Recursos primary: `{"platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.41", "python": "3.13.5", "logical_cpus": 4, "cpu_affinity": 4, "memory_total_kb": 16373452, "cpu.max": "max 100000", "memory.max": "max"}`.

Recursos repeat: `{"platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.41", "python": "3.13.5", "logical_cpus": 4, "cpu_affinity": 4, "memory_total_kb": 16373452, "cpu.max": "max 100000", "memory.max": "max"}`.

Métricas del servicio/JDBC derivadas de las1000muestras, excluyendo20warmups.
Cada frontera conserva su unidad propia; percentiles nearest-rank.

| Fase | Operación | Queries min/mediana/max | Servicio p50 ms | JDBC p50 ms |
| --- | --- | --- | --- | --- |
| primary | search | 16/16/16 | 8.158424 | 5.929182 |
| primary | inventory | 17/18/19 | 11.974311 | 8.561949 |
| primary | create | 47/47/50 | 14.583929 | 5.099625 |
| repeat | search | 16/16/16 | 8.741547 | 6.095547 |
| repeat | inventory | 17/18/18 | 12.120512 | 8.546444 |
| repeat | create | 47/47/48 | 15.489177 | 5.157598 |

Duración observada de Gradle, extraída literalmente de los logs completos
del mismo run (no incluye instalación ni arranque del ERP):

| Log | Resultado y duración |
| --- | --- |
| full-build.log | Archivo no disponible; no imputado |
| frozen-build.log | Archivo no disponible; no imputado |

Conteos HTTP de los clientes instrumentados antes del benchmark/reinicio final;
incluyen preparación e inspecciones, no son el total global del ERP ni una
medida equivalente entre plataformas. Los seis endpoints y cada recorrido
económico conservan sus solicitudes en los archivos originales.

| Fase | Cliente | Llamadas registradas |
| --- | --- | --- |
| primary | administrator | 1417 |
| primary | product_operator | 30 |
| primary | search_reader | 16 |
| primary | fx_operator | 11 |
| primary | fx_manager | 4 |
| repeat | administrator | 1417 |
| repeat | product_operator | 30 |
| repeat | search_reader | 16 |
| repeat | fx_operator | 11 |
| repeat | fx_manager | 4 |

CI total:3246s. Suites Java ejecutadas por fase de build, sin duplicar la compilación para réplica:

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

Upstream diffs efectivos: `{"host": 0, "aos": 0}`; pins contra el blob base conservados. WAR SHA256 `8a4f2eea8bba4e6c9dbc13c8e1f2c7b6c6832524adf460781f120b9000781184`.

Código propio: archivos/líneas físicas y no vacías, incluidos comentarios; sólo
fuentes tracked del SHA, sin generados, dependencias, build, evidencias o Frappe.

| Categoría | Archivos | Líneas físicas | No vacías |
| --- | --- | --- | --- |
| CI runner | 12 | 682 | 655 |
| Core harness | 16 | 3745 | 3503 |
| Java runtime | 52 | 3638 | 3493 |
| Java tests | 11 | 544 | 505 |
| Python regression tests | 8 | 1315 | 1248 |
| module resources | 5 | 237 | 237 |

99 archivos Axelor modificados desde e0190090; inventario y hashes en source-metrics.json.

Intervenciones del bloque: cinco causas B37 corregidas juntas y un conteo antiguo
B38 corregido tras conservar su CI sin arranque; B39 corrige dos causas de
transporte; B40 limita el diagnóstico admin y corrige el consumo de cuerpo HTTP
del consumidor. No cambian negocio, permisos ni expectativas.11modelos ORM nativos según
SUPPORTED-CONFIGURATION ejecutado; no migración SQL manual ni ensayo de upgrade.
Fixture/configuración/secuencias se confirman antes de stock; la transacción
venta/entrega/factura/liquidación y sus rechazos conserva su atomicidad.
Reinicios propios y restore a otra DB prueban la misma versión, no actualización.
