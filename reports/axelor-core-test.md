# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 fixtures idénticos, manifiesto/oráculo intactos, cobertura revisión 2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37416107406](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37416107406),
commit `013f9622d67ed921afd79b1ca66388a3e1e89eca`, **FAILURE**. PROD y BANK-BOOK completos
PASS. Gates bloqueados por requisitos de facturación/configuración. FX conservado
como conversión parcial PASS y grupo UNRUN: el antiguo PASS completo era incorrecto.
La matriz siguiente incorpora la revisión B19; conserva el resultado originalmente
reportado en el archivo del caso y en la procedencia, sin contar pagos inexistentes.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Causa observada |
| --- | --- | --- | --- |
| CO00, primero | BLOCKED | 13.360 s | ValidateState: Warning ! : Invoicing address missing |
| TAX01-W, segundo | BLOCKED | 5.441 s | No account found for Tax: TAX-LAB-10 (company: CCM-LAB-001) |

Factory oficial de SaleOrder verificado en ERP: estado draft=1; se superó la
finalización anterior sin escribir statusSelect. Entrada inicial REALIZED=3,
stock persistido 5/5/5, WAP 30/10/60 y asiento de apertura separado de 500 por
fixture. La venta/entrega/factura se revierten juntas al fallar facturación;
no hay efectos económicos de venta persistidos. Sequence NoResult no reapareció.
El contador aislado puede avanzar al fallar la transacción; sus huecos no prueban venta.

B20/B21: se preparan direcciones nativas y Company.partner/AccountingSituation
con régimen de entrega/devengo, además del régimen de las cuentas. Se conservan
validaciones fiscales y de dirección. B23: se preparan términos nativos del pago
inicial, requeridos por el servicio oficial. Estas correcciones están pendientes
de repetición en ERP. No se demuestran aún stock final 3/4/5, costo 70, IVA y liquidación.
Un futuro gate administrativo PASS seguirá siendo parcial hasta roles, estados,
rechazos, atomicidad e idempotencia del grupo completo.

## Casos independientes

- PROD01-04 PASS completo, 2.277 s: operador real, seis garantías, retención de
  precio al deshabilitar, restauración y lecturas nuevas de tres perfiles/FK.
- BANK-BOOK-FIXTURE PASS completo, 1.526 s: cuatro PaymentVoucher confirmados,
  cuatro asientos ACCOUNTED, ocho líneas persistidas, AR firmado negativo,
  vouchers no aplicados positivos por 255 y replay idéntico sin duplicados.
- SEARCH FAIL, 0.555 s: aislamiento 403, cuatro búsquedas de productos y dos
  páginas correctos; C001 existe con nombre/teléfono/compañía exactos, pero REST
  del lector devuelve status=0 sin data. El nuevo diagnóstico compara admin y
  filtro real JpaSecurity del lector. No se amplía el permiso. Serial/factura pendientes.
- FX/MONEY: conversiones parciales PASS, 0.581 s, tasas nativas 40/41/40.5 y
  0.41+0.41=0.82, rechazo 422 sin tasa, operador 403 sin efectos y autorización
  por manager real. **Cero evidencia de pagos en ese CI: grupo UNRUN.**
  Se añaden tres facturas USD y cuatro InvoicePayment VES mediante
  InvoiceGenerator, InvoiceLineService, InvoiceService y servicios de creación,
  términos, validación, asiento y conciliación. Importes 40/41/0.41/0.41,
  fechas/tasas/IDs observados, efectos USD y liquidación se exigirán en lecturas
  posteriores al commit. El agregado rechaza datos de tasas/cálculos solos,
  asientos draft, fechas incorrectas, pagos ausentes y deuda pendiente.

Impedimentos, impacto, pasos y verificación:
[axelor-core-test-impediments.md](axelor-core-test-impediments.md), B19–B24.

## Matriz de 34 grupos — CI revisado

**PASS 2 / FAIL 1 / BLOCKED 2 / UNRUN 29**. Parciales del administrador y
conversiones están separados. El CI antiguo reportó 3/1/2/28; B19 rechaza el
PASS FX completo. No se agregan resultados locales a la cobertura nativa.

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
| BANK-BOOK-FIXTURE | 1 | PASS | Sí |
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

## 14 criterios — evidencia ejecutada

| Criterio | Estado |
| ---: | --- |
| 1 | BLOCKED |
| 2 | PASS |
| 3 | FAIL |
| 4 | BLOCKED |
| 5 | BLOCKED |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | UNRUN |
| 10 | UNRUN |
| 11 | BLOCKED |
| 12 | FAIL |
| 13 | BLOCKED |
| 14 | UNRUN |

Criterio 2 procede de commits fijados, diffs upstream reales cero, blob base de
pins idéntico, WAR y suites de ese run. Ningún criterio está preasignado.
Benchmark/recovery no se aprueban por smoke. Criterio 13 BLOCKED por decisión
expresa del usuario; seis PATCH UNRUN. Sin actualización del baseline.

## Métricas y validaciones

- CI: 2 tests originales + 7 de política + 16 upstream; cero errores/fallos/skips,
  según atestación del log. 17 regresiones Python en ese commit.
- Cambios posteriores: 19 regresiones de integridad; pruebas locales 2+7 y
  compilación full-native con perfil de locks externo y replay offline estricto,
  en secuencia.
- Readiness inicial 422.52 s; reinicio de la misma DB 318.38 s.
  Job 19 min 16 s. Son timings de smoke, no benchmark de operaciones.
- Runner: 4 CPU visibles/4 de afinidad;
  Linux-6.17.0-1022-azure-x86_64-with-glibc2.41; disco libre 87100051456 bytes.
- HTTP: {"administrator": 23, "product_operator": 30, "search_reader": 11, "fx_operator": 8, "fx_manager": 4}. Incluye login/preparación;
  muestras individuales ausentes del log recuperado. FX corresponde a cálculos antiguos.
- p50/p95/p99, 1000 muestras y query/DB timing: UNRUN.
- JAR propio sin com.axelor.*, pins/lock originales y upstream sin diferencias.
- La ejecución simultánea de los perfiles Gradle produjo ClassNotFoundException
  de clases propias; repetir el perfil Cloud secuencialmente pasó 2+7.
  Los perfiles deben ejecutarse secuencialmente en este checkout compartido.

Pins SHA256: `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
WAR: `0075463fdef42500413014c31dca3cadaa3301847c274710ac2c8f59a8367abb`.

## Evidencia y continuidad

[coverage.json](evidence/axelor-core/runs/37416107406/coverage.json),
[build-evidence.json](evidence/axelor-core/runs/37416107406/build-evidence.json),
[runtime-metrics.json](evidence/axelor-core/runs/37416107406/runtime-metrics.json),
gates/exports/casos/smokes/hashes y revisión del PASS rechazado en
[evidence-source.json](evidence/axelor-core/runs/37416107406/evidence-source.json).
Fuente secundaria: JSON completo del log; no se infiere lo ausente.
ZIP 11391813114 bloqueado con Forbidden en productionresultssa16.blob.core.windows.net,
un intento, sin ampliar/publicar red. Log completo recuperable:
`/workspace/ccm-axelor-runtime/ci-evidence/37416107406.log`. Evidencias históricas
CI6/CI7/CI8 conservadas aparte, sin sustituir pruebas de la ejecución actual.

Se continúa la repetición autorizada de gates primero y casos independientes
después. No hay PR, merge, despliegue, cambio de main/Frappe/upstream/pins ni
cierre de comparación. Configuración de arranque guardada sólo como borrador;
no se publica ninguna ampliación de red pendiente.
