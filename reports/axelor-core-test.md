# Core Test Axelor — ejecución en curso

Comparación **incompleta**. Referencia fija `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`,
16 fixtures idénticos, manifiesto/oráculo intactos, revisión de cobertura 2,
34 grupos y 14 criterios. Rama exclusiva `lab/axelor-baseline`.

Último CI finalizado: [37425320931](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37425320931),
commit `8b0a534b8c835aa01aadb753b65be7f4e4c3fbd6`, **FAILURE**.
El preflight de dirección pasó en ERP real. Gates bloqueados por impresión
opcional; búsquedas fallidas por composición de Permission.condition. No hay
venta, GL de venta ni pagos FX confirmados. PROD/BANK PASS se ejecutaron en
este commit; no se arrastran resultados históricos.

## Gates económicos parciales

| Gate, administrador real | Estado | Tiempo | Causa observada |
| --- | --- | --- | --- |
| CO00, primero | BLOCKED | 15.024 s | getInvoicePrintTemplate: configuración PDF ausente |
| TAX01-W, segundo | BLOCKED | 6.549 s | Misma dependencia opcional de PDF |

Los dos gates confirman Sequence y entrada inicial REALIZED; cada almacén
conserva 5/5/5, WAP 30/10/60 y apertura 500. La transacción de venta revierte
al generar PDF: no entrega ni factura persistidas. Stock final 3/4/5, COGS 70,
IVA y liquidación siguen sin demostrarse. Un gate administrador PASS seguirá
siendo parcial hasta ejecutar roles, estados, atomicidad, rechazos e idempotencia.

AddressBaseRepository guardó Address id=1, plantilla id=5, cinco hijos
persistidos y cinco MetaField reales; streetName/city/zip requeridos. Nombres
renderizados/computados nativamente, lectura después del commit, replay
idéntico. Preflight PASS en 1.484 s; no aprueba ningún grupo ni criterio Core.

## Casos independientes

- PROD01-04 PASS, 2.546 s: CRUD con operador real y lecturas posteriores al commit.
- BANK-BOOK-FIXTURE PASS, 0.989 s: cuatro cobros anticipados nativos, cuatro
  asientos contabilizados, ocho líneas y saldo no asignado 255; replay idéntico.
- SEARCH FAIL, 0.634 s: productos/paginación y denegación de compañía ajena 403
  ejecutados. Nombre/teléfono/serial no devuelven filas; diagnóstico nativo
  String/Long. Consulta de factura sin resultado porque CO00 revirtió.
- FX FAIL, 3.043 s: conversiones nativas parciales PASS 40/41/40.5 y 0.41+0.41=0.82.
  Rechazos sin efectos 422/403 y autorización gerente ejecutados. Se intentaron
  independientemente FX01, FX02 y MONEY-ROUND; los tres revirtieron por PDF.
  **Cero pagos nativos demostrados.** No se aprueba el grupo por cálculos/tasas.

## Corrección autorizada pendiente de aceptación por CI

Permission.condition usa ahora `?`, conservando predicados de compañía,
conditionParams `__user__.activeCompany.id` y grants. Query directo conserva
`?1`. La regresión nativa reproduce cómo el placeholder antiguo termina
vinculando nombre y compañía al mismo parámetro Long y verifica la composición
corregida con nombre/teléfono/factura.

AppInvoice.autoGenerateInvoicePrintingFileOnSaleInvoice=false se guarda por
repositorio nativo sólo con CCM_CORE_LAB=1 y administrador. isVentilationSkipped
se exige false; no se omite ventilación. El runner exige IDs y flags efectivos
más persistidos después del commit; GL sigue requiriendo status=3 y oráculo.
InvoiceService.validate/ventilate permanece intacto. **PDF automático queda
fuera del alcance probado; no se presenta como validación económica.** No hay
PrintingTemplate fabricada ni datos demo importados. Decisiones ADR006/007;
causa/impacto/pasos numerados en impedimentos B28/B29.

## Matriz de 34 grupos — último CI

**PASS 2 / FAIL 2 / BLOCKED 2 / UNRUN 28**. Gates parciales separados.

| Grupo requerido | Revisión mínima | Estado | Completo |
| --- | --- | --- | --- |
| CO00-NATIVE | 1 | BLOCKED | No |
| CO01-NATIVE | 1 | UNRUN | No |
| TAX01-S-NATIVE | 1 | UNRUN | No |
| TAX01-W-NATIVE | 1 | BLOCKED | No |
| PROD01-04 | 1 | PASS | Sí |
| VAL01-04 | 1 | UNRUN | No |
| STATE01-04 | 1 | UNRUN | No |
| INV01-03-INSUFFICIENT | 1 | UNRUN | No |
| FX01-03-MONEY01-03 | 1 | FAIL | No |
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
| --- | --- |
| 1 | BLOCKED |
| 2 | PASS |
| 3 | FAIL |
| 4 | BLOCKED |
| 5 | FAIL |
| 6 | UNRUN |
| 7 | UNRUN |
| 8 | UNRUN |
| 9 | UNRUN |
| 10 | UNRUN |
| 11 | BLOCKED |
| 12 | FAIL |
| 13 | BLOCKED |
| 14 | UNRUN |

Criterio 2 deriva de suites/WAR/pins/diffs upstream ejecutados del mismo commit,
sin PASS preasignado. Cualquier suite adicional fallida/error/skip se rechaza.
Criterio 13 BLOCKED por decisión del usuario: seis PATCH UNRUN. Benchmark y
recovery no se aprueban por smoke. Faltan 28 grupos y subcasos de los gates.

## Validaciones locales y límites

- Corrección SEARCH/PDF: 15 tests nativos PASS (8 dirección, 5 filtros, 2 flags),
  cero fallos/errores/skips. 24 regresiones Python PASS, incluidas cuatro pagos
  obligatorios, GL draft, flags incorrectos y continuidad de casos independientes.
- 2 tests baseline + 7 política PASS; compilación/JAR cloud y full-native
  con locks estrictos offline. Son validaciones locales, sin aceptación ERP.
- PostgreSQL local arrancó, pero el diagnóstico JPA anterior no alcanzó save
  por RequestScoped del contexto HTTP. No se sustituyen scopes ni auditoría.
  CI es fuente de aceptación; el preflight real nuevo ya pasó en CI12.
- [Tests locales SEARCH/PDF](evidence/axelor-core/search-invoice-local-20261006/validation.json),
  [diagnóstico Address anterior](evidence/axelor-core/address-preflight-local-20261006/diagnostic.json).
  Sin cambios de permisos del sistema/red ni credenciales persistentes.

## Métricas del CI 37425320931

- 24 regresiones Python; 2 baseline + 7 política + 8 callbacks + 16 upstream,
  sin fallos/errores/skips según atestación de ese commit.
- Readiness inicial 434.51 s; reinicio misma DB 321.42 s; job 19 min 26 s.
  AOP8.2.3, AOS9.1.8, módulo0.1.0, 33 módulos, login/REST autenticados.
- 4 CPU / afinidad4; Linux-6.17.0-1022-azure-x86_64-with-glibc2.41;
  disco libre 87089336320 bytes. HTTP administrador32, operador producto30,
  lector16, operador FX11 y gerente FX4.
- p50/p95/p99, 1000 muestras y timing query/DB: UNRUN.
- Upstream host/AOS diff exit codes0; pins SHA256
  `6b8a6b9e013df7756b9b1b14a296081cc9aee73885e970be1f634380cc1bb816`.
- WAR de CI12 SHA256 `bcb968829d6bbb45781783cb79f9f998d9489489b238f538b6a0cc75c31d61b5`.

## Evidencia y continuidad

[coverage.json](evidence/axelor-core/runs/37425320931/coverage.json),
[preflight nativo Address](evidence/axelor-core/runs/37425320931/address-preflight.json),
[build-evidence.json](evidence/axelor-core/runs/37425320931/build-evidence.json),
[runtime-metrics.json](evidence/axelor-core/runs/37425320931/runtime-metrics.json),
[procedencia/hashes/smokes](evidence/axelor-core/runs/37425320931/evidence-source.json).
Fuente secundaria: avisos JSON completos del log. ZIP11395194586 Forbidden en
productionresultssa14.blob.core.windows.net; un intento, sin ampliar/publicar red.
Log recuperable: `/workspace/ccm-axelor-runtime/ci-evidence/37425320931.log`.

La corrección actual repetirá CO00 primero y TAX01-W segundo, después casos
independientes. Sin PR, merge, despliegue ni modificaciones a main/Frappe/pins/
upstream. Arranque sólo en borrador; comparación permanece incompleta.
