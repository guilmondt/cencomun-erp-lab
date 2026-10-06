# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 archivos de fixtures byte a byte, manifiesto/oráculo intactos, cobertura revisión 2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37413918081](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37413918081),
commit `66199825dcc333e9001a05b3b94cc68e6d843d2c`, **FAILURE**. Los gates siguen bloqueados;
PROD01-04 obtuvo PASS completo por operador real. Historial/pins/diffs/build
pasaron; el CI permanece rojo porque la cobertura requerida no está completa.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Evidencia |
| --- | --- | --- | --- |
| CO00, primero | BLOCKED | 7.101 s | Stock inicial persistido 5/5/5, WAP 30/10/60; venta revertida al fallar finalización |
| TAX01-W, segundo | BLOCKED | 1.394 s | Misma frontera; sin pedido, entrega, factura, costo ni liquidación de venta persistidos |

Error nativo: `Can only finalize a drafted quotation.` SaleOrder no tiene
estado default; su factory oficial lo inicializa. Se cambia al factory, sin
escribir statusSelect. Esta corrección todavía necesita repetición en ERP.
Se añade export separado del asiento de apertura del fixture, que el inspector
anterior excluía de los movimientos económicos de la venta.

La separación de preparación/confirmación corrigió Sequence: doce secuencias
visibles, incremento aislado nativo y entrada REALIZED=3 sin NoResultException.
El contador aislado puede avanzar durante un rollback: no demuestra éxito económico.
No se demuestran aún stock final 3/4/5, costo 70, impuestos y liquidación.
Incluso un futuro gate PASS como admin seguirá siendo parcial hasta ejecutar
roles, estados, rechazos, atomicidad e idempotencia del grupo completo.

## Independientes y correcciones verificadas

- PROD01-04 PASS, 2.409 s: seis combinaciones de garantía, precio conservado al
  deshabilitar, restauración y lectura nativa completa de tres perfiles con FK.
  Login real, usuario activo/no bloqueado y permisos de compañía comprobados.
- SEARCH FAIL, 0.460 s: aislamiento 403, cuatro búsquedas y ambas páginas de
  productos correctas. Primera búsqueda de cliente vacía. Se añade inspección
  de clientes/companySet y respuesta REST completa; no se elimina el permiso ni
  se atribuye una causa aún no demostrada. Factura/serial pendientes.
- BANK-BOOK FAIL, 1.268 s: el control de cuentas ya permite la confirmación, pero
  la aserción confundía importe no aplicado positivo con saldo firmado negativo
  de crédito AR. Se conserva el saldo nativo y se exige -importe, además de
  voucher positivo, asientos ACCOUNTED y replay. Fixture/oráculo intactos.
- B11 (colección Move) ya no se reproduce; el helper nativo mantiene la colección.
  B12 (Company frente a Long) y B13 (paginación) verificados por CRUD/productos.
  B14 (cuentas de journal) no reapareció en apertura ni recibo bancario.
- FX/MONEY preparado como independiente: CurrencyConversionLine de un día,
  CurrencyService y autorización por manager real con FK/auditoría Cencomun.
  Prueba falta de tasa, rechazo 403 sin efectos y redondeo 0.41+0.41=0.82.
  **UNRUN en ERP** hasta el siguiente CI; no se infiere PASS de compilación.

Causa observada, impacto, pasos numerados y verificación:
[axelor-core-test-impediments.md](axelor-core-test-impediments.md), B15–B18.

## Matriz de 34 grupos — último CI finalizado

PASS 1; FAIL 2; BLOCKED 2; UNRUN 29. Sólo PROD completo.
Los resultados parciales del administrador se mantienen separados.

| Grupo requerido | Revisión mínima | Estado | Completo |
| --- | ---: | --- | --- |
| CO00-NATIVE | 1 | BLOCKED | No |
| CO01-NATIVE | 1 | UNRUN | No |
| TAX01-S-NATIVE | 1 | UNRUN | No |
| TAX01-W-NATIVE | 1 | BLOCKED | No |
| PROD01-04 | 1 | PASS | Sí |
| VAL01-04 | 1 | UNRUN | No |
| STATE01-04 | 1 | UNRUN | No |
| INV01-03-INSUFFICIENT | 1 | UNRUN | No |
| FX01-03-MONEY01-03 | 1 | UNRUN | No |
| PO01-09-NATIVE | 1 | UNRUN | No |
| PO07-09-REVISION-SELF | 1 | UNRUN | No |
| CASH00-06-NATIVE | 1 | UNRUN | No |
| BANK-BOOK-FIXTURE | 1 | FAIL | No |
| BANK01-05-NATIVE | 1 | UNRUN | No |
| API01-06-SIX-ROUTES | 1 | UNRUN | No |
| IDEM01-02-CREATE-CONCURRENT | 1 | UNRUN | No |
| PERM-API-NATIVE | 1 | UNRUN | No |
| CASH04-06-HTTP-IMMUTABLE | 1 | UNRUN | No |
| SEARCH01-04-NATIVE | 1 | FAIL | No |
| TAX02-04-IDEM-CONCURRENT | 1 | UNRUN | No |
| BANK-CONCURRENT-1000 | 1 | UNRUN | No |
| MCP01-06-STDIO | 2 | UNRUN | No |
| IDEM03-LOST-RESTART | 1 | UNRUN | No |
| IDEM04-EVENTS-RECOVERY | 2 | UNRUN | No |
| FIXTURE-HASH-NATIVE-EXPORT | 1 | UNRUN | No |
| AUDIT01-03-NATIVE | 2 | UNRUN | No |
| IDEM-TAX-NATIVE-EFFECT-COUNTS | 1 | UNRUN | No |
| SUPPORTED-CONFIGURATION | 1 | UNRUN | No |
| STATE-UNKNOWN-ATOMIC | 2 | UNRUN | No |
| STATE-DELIVERY-WITHOUT-ACCEPTANCE | 2 | UNRUN | No |
| STATE-WEB-NO-GUIDE | 2 | UNRUN | No |
| STATE-CANCEL-BEFORE-HANDOVER | 2 | UNRUN | No |
| MCP-FORBIDDEN-CRITICAL-ACTIONS | 2 | UNRUN | No |
| MCP-DENIALS-NATIVE-EFFECTS-AUDIT | 2 | UNRUN | No |

## 14 criterios — pruebas ejecutadas

| Criterio | Estado |
| ---: | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | BLOCKED |
| 5 | BLOCKED |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | UNRUN |
| 10 | UNRUN |
| 11 | FAIL |
| 12 | FAIL |
| 13 | BLOCKED |
| 14 | UNRUN |

Criterio 2 PASS procede de host/AOS exactos, diffs upstream reales cero, blob
base de pins idéntico, WAR y suites del mismo run. Los demás criterios derivan
los grupos ejecutados y su revisión/completitud; los benchmark/recovery adicionales
no se aprueban por smoke. Criterio 13 BLOCKED por decisión expresa del usuario;
seis escenarios PATCH UNRUN. No hay upgrade.

## Métricas y validaciones

- CI actual: 2 originales + 7 de política + 16 upstream, sin errores/fallos/skips,
  según la atestación real del log; 14 regresiones Python en ese commit.
  Cambios locales posteriores: 17 regresiones, 2+7 tests y compilación nativa/offline PASS.
- Readiness inicial 422.47 s; reinicio con la misma DB 315.40 s. Job 19 min.
  No equivale a benchmark de operaciones ni a timings por tarea Gradle.
- Runner: 4 CPU visibles/4 de afinidad,
  `Linux-6.17.0-1022-azure-x86_64-with-glibc2.41`; disco libre 87098335232 bytes.
- Core HTTP: admin 16, operador 30,
  lector 11; incluye login/preparación.
  Muestras individuales del cliente no están en los avisos recuperados de este run.
- p50/p95/p99, 1000 muestras y query/DB timing: UNRUN.
- JAR propio sin clases com.axelor.*, pins y lock originales sin diferencias.

Pins SHA256: `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
WAR del run: `c1de664d05fa6909755abc9281bd5ba072af6aae1566c28c1886b6a841191714`.

## Evidencia, red y continuación

[coverage.json](evidence/axelor-core/runs/37413918081/coverage.json),
[build-evidence.json](evidence/axelor-core/runs/37413918081/build-evidence.json),
[runtime-metrics.json](evidence/axelor-core/runs/37413918081/runtime-metrics.json),
exports/gates, independientes, smoke y hashes en
[evidence-source.json](evidence/axelor-core/runs/37413918081/evidence-source.json).
Fuente **secundaria**: avisos JSON completos del log, cuyo hash se conserva.
El artefacto 11390399358 existe, pero su ZIP fue bloqueado dos veces con Forbidden
en productionresultssa17.blob.core.windows.net. No se descargaron sus XML ni
archivos ausentes. Artefactos completos históricos CI6/CI7 se conservan aparte.
El log completo es recuperable en
`/workspace/ccm-axelor-runtime/ci-evidence/37413918081.log`.

No se publica red pendiente. Continúa autorizada la repetición de gates y casos
independientes. No hay PR, merge, despliegue, modificación de main/Frappe/upstream/pins
ni declaración de cierre de comparación. La guía de arranque queda sólo en borrador.
