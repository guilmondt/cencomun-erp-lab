# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 fixtures idénticos, manifiesto/oráculo intactos, cobertura revisión2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37429209635](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37429209635),
commit `27bdbd840f733eb3355658d3016b87edb4f3826d`, **FAILURE**.
PROD, BANK y FX completo PASS ejecutados en ese commit. CO00/TAX01-W y SEARCH
FAIL: no se demostró el vínculo de la factura en su export. No se arrastran PASS
históricos al siguiente commit. Causa/impacto/pasos/verificación: impedimento B30.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Causa observada |
| --- | --- | --- | --- |
| CO00, primero | FAIL | 15.990s | Inspector de cabecera no encuentra factura |
| TAX01-W, segundo | FAIL | 8.183s | Mismo vínculo no exportado |

La venta confirmó: stock3/4/5, WAP30/10/60, valoración430; COGS70 y liquidaciones
nativas contabilizadas. CO00: banco67/comisión8/AR75; TAX01-W:
banco70.25/comisión11.55/envío0.70/AR82.50. El export omite factura/GL/pago directo
por filtrar Invoice.saleOrder, null con el helper corto. Esos resultados son
parciales: ingresos, IVA y recorrido económico completo aún sin aceptación.
Un gate administrador PASS tampoco completará roles, estados, atomicidad,
rechazos e idempotencia del grupo.

Preflight de dirección PASS1.519s: AddressBaseRepository guardó dirección,
plantilla, cinco hijos y cinco MetaField; required streetName/city/zip;
render/compute/save/lectura posterior y replay nativos. No aprueba grupos Core.
AppInvoice efectivo y persistido id1: PDF automático=false e
isVentilationSkipped=false. InvoiceService.validate/ventilate permanece íntegro.
**PDF automático fuera del alcance probado**, sin PrintingTemplate ni demo.

## Casos independientes del mismo CI

- PROD01-04 PASS2.469s: CRUD con operador y lectura posterior al commit.
- BANK-BOOK-FIXTURE PASS0.794s: cuatro anticipos, GL contabilizado y saldo255;
  replay idéntico.
- SEARCH FAIL0.434s: nombre/teléfono/serial, productos/paginación y compañía
  ajena403 ejecutados. Factura existe, pero no se probó relación de venta.
- FX01-03-MONEY01-03 PASS4.222s: cuatro InvoicePayment nativos ids5/6/7/8,
  tres facturas3/4/5 y siete asientos15–21 ACCOUNTED. FX01: Oct1 VES40/USD1;
  FX02: Oct2 VES41/USD1; MONEY-ROUND: Oct3 dos VES0.41/USD0.01.
  Fechas, cotizaciones40/41/40.5, tasa efectiva redondeada, conciliación
  CONFIRMED y factura/AR0 se leyeron después del commit. Rechazos sin efectos
  y autorización por gerente real ejecutados. Conversión parcial se conserva
  aparte; el agregador rechaza cálculos/tasas sin los cuatro pagos y sus GL.

## Corrección de vínculo pendiente de aceptación ERP

Se usa el overload completo generateInvoice con la constante oficial
SaleOrderRepository.INVOICE_ALL y el guard de facturabilidad del wizard.
AOS asigna/guarda Invoice.saleOrder. Se conserva getInvoices y se exige además
InvoiceLine.invoice/InvoiceLine.saleOrderLine/SaleOrderLine.saleOrder, misma
factura/venta/compañía y coincidencia con las líneas económicas exportadas.
La referencia externa sólo selecciona; no prueba el vínculo. Lectura por
lector conserva scope/grants nativos y exige denegación ajena403.
Sin alterar sell transaccional ni validación/contabilización/liquidación.
25 regresiones Python y 2+7 tests baseline PASS; compilación/JAR full-native
offline con locks estrictos PASS20s. Son pruebas locales, no aceptación ERP.
La regresión rechaza cabecera null, FK ausente o compañía/factura equivocada.
ADR008 y ExecPlan documentan la decisión. Repetir CO00 antes de TAX01-W,
después independientes, en un único CI; no contar la corrección como verificada.

## Matriz de 34 grupos — último CI finalizado

**PASS3 / FAIL3 / BLOCKED0 / UNRUN28**. Gates parciales separados.

| Grupo requerido | Revisión mínima | Estado | Completo |
| --- | --- | --- | --- |
| CO00-NATIVE | 1 | FAIL | No |
| CO01-NATIVE | 1 | UNRUN | No |
| TAX01-S-NATIVE | 1 | UNRUN | No |
| TAX01-W-NATIVE | 1 | FAIL | No |
| PROD01-04 | 1 | PASS | Sí |
| VAL01-04 | 1 | UNRUN | No |
| STATE01-04 | 1 | UNRUN | No |
| INV01-03-INSUFFICIENT | 1 | UNRUN | No |
| FX01-03-MONEY01-03 | 1 | PASS | Sí |
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

**PASS1 / FAIL6 / BLOCKED1 / UNRUN6**.

| Criterio | Estado |
| --- | --- |
| 1 | FAIL |
| 2 | PASS |
| 3 | FAIL |
| 4 | FAIL |
| 5 | FAIL |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | UNRUN |
| 10 | UNRUN |
| 11 | FAIL |
| 12 | FAIL |
| 13 | BLOCKED |
| 14 | UNRUN |

Criterio2 exige suites/WAR/pins/diffs upstream ejecutados del mismo commit,
sin PASS preasignado. Criterio13 BLOCKED: actualización diferida a copia
aislada con objetivo aprobado; seis PATCH UNRUN. Faltan28 grupos y subcasos de
los gates. Benchmark/recovery no se aprueban por smoke.

## Métricas y procedencia del CI37429209635

- 24 regresiones Python; 40 tests Java reales: 2baseline+7política+8dirección+
  5filtros+2flags+16upstream, cero fallos/errores/skips.
- Readiness inicial419.44s; reinicio misma DB315.38s; job18min54s.
  Login/REST autenticados; AOP8.2.3/AOS9.1.8/módulo0.1.0, 33módulos.
- CPU4/afinidad4; Linux6.17.0-1022-azure, disco libre87087919104bytes.
  HTTP admin30/operador producto30/lector14/operador FX11/gerente FX4.
- p50/p95/p99, 1000muestras y query/DB timing UNRUN.
- Upstream host/AOS diff exit0; pins SHA256
  `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
  WAR SHA256 `5f8ad51754e5303acf785fd0c38501eaf8d1d5e34e53d15b1fb434de164b57d6`.

[coverage.json](evidence/axelor-core/runs/37429209635/coverage.json),
[gates](evidence/axelor-core/runs/37429209635/CO00-native-export.json),
[cuatro pagos FX](evidence/axelor-core/runs/37429209635/FX01-03-MONEY01-03.json),
[build](evidence/axelor-core/runs/37429209635/build-evidence.json),
[métricas](evidence/axelor-core/runs/37429209635/runtime-metrics.json),
[procedencia/hashes/smokes](evidence/axelor-core/runs/37429209635/evidence-source.json).
Fuente secundaria: avisos JSON completos del log. ZIP11396837860 Forbidden en
productionresultssa12.blob.core.windows.net, un intento; red sin cambios ni
publicación. Log recuperable: `/workspace/ccm-axelor-runtime/ci-evidence/37429209635.log`.

CI sigue siendo fuente de aceptación. Docker/PostgreSQL local no equivalen a
ERP fiable; el diagnóstico JPA anterior quedó en RequestScoped/saveUNRUN.
El preflight HTTP ya pasó en ERP real. No se crean credenciales persistentes.
Sin PR/merge/despliegue ni cambios main/Frappe/pins/upstream. La comparación
permanece incompleta y la actualización está fuera de esta ejecución.
