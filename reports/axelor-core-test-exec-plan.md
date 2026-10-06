# ExecPlan — preparación del Core Test de Axelor

Estado: **IMPLEMENTACIÓN AUTORIZADA; ejecución en curso**.
Revisión: 2026-10-06 UTC. Rama: `lab/axelor-baseline`.
HEAD inspeccionado: `e0190090fd137576ce273e350d7ce6686d66baf9`.

El usuario autorizó implementar y ejecutar este plan, hacer commit/push solo
en `lab/axelor-baseline` y ejecutar CI. El upgrade sigue aplazado para otra
copia aislada con objetivo aprobado. Las secciones siguientes conservan el
plan preparado y sus observaciones históricas; los resultados nuevos se
publican aparte en `reports/axelor-core-test.md` y sus evidencias. Los tests
del baseline y de política monetaria no se cuentan como grupos nativos PASS.

Progreso de continuación (2026-10-06): checkout/ejecutor recuperado; historial
del baseline verificado antes del build; preparación de fixture separada por
petición y commit del consumo nativo de `Sequence`. La repetición de gates
se ejecuta antes de ampliar su alcance. Se implementan los campos de producto
con FK nativos y pruebas `PROD01-04` por operador real, más consultas de
`SEARCH01-04-NATIVE` por lector real. Toda dependencia ausente y subcaso no
ejecutado conserva estado explícito. La factura de búsqueda depende de CO00.
No se publica red pendiente, no se modifica ningún pin y no se declara cierre
de comparación con éxitos parciales.

Continuación del fixture independiente `BANK-BOOK-FIXTURE`: las cuatro filas
fijadas se implementan mediante PaymentVoucher de anticipo y su servicio nativo
de confirmación, sin factura ni asignación. Un journal nativo dedicado permite
anticipos (`excessPaymentOk`) sin alterar los journals de los gates; su secuencia
se prepara y confirma antes de consumirla. La prueba exige lectura nueva de
los vouchers/asientos/saldos, más replay de fixture conservando IDs. Compilación
y 14 regresiones locales comprobadas; prueba ERP pendiente. Esto no aprueba
importación, conciliación, concurrencia ni los otros grupos bancarios.

Continuación B26 (2026-10-06): conservar CI como aceptación. Preparar la plantilla
con cinco líneas/metadatos reales y tres requeridos oficiales, comprobar ocho
callbacks localmente y ejecutar preflight de guardado/lectura/replay en el ERP
real antes de gates/reinicio. El diagnóstico PostgreSQL/JPA local no alcanzó
save por falta de RequestScoped; se detuvo sin cambiar scopes, permisos ni red.
No se convierte una herramienta de diagnóstico en requisito del Core Test.

## 1. Referencia inmutable y alcance

Fuente común: commit
[`fcf690dbc58b2b2dcf8d045c49976e3613e804cf`](https://github.com/guilmondt/cencomun-erp-lab/tree/fcf690dbc58b2b2dcf8d045c49976e3613e804cf).
Se leyó mediante `git fetch --no-tags origin <SHA>`, `git show` y extracción de
blobs a `/tmp/ccm-frappe-reference-fcf690d`; no se cambió de rama ni se hizo merge.
La autorización histórica de Frappe escrita en esos documentos no es la
autorización de esta implementación; prevalece la instrucción actual del
usuario que aprueba implementar Axelor y mantiene Frappe sin modificaciones.

| Artefacto en ese commit | Identidad verificada |
| --- | --- |
| ExecPlan, `tasks/100-ccm-core-test.md` | SHA256 `fee93e1fc711b0f0b3f10a872bb3e828ef0475914e6712b09ea953477a7210b2` |
| Especificación corregida, `docs/CORE_TEST_SPEC.md` | SHA256 `8ea17b1f892184dc25834ff7dea42fa1bc45646f1cdd7ce8998184c2aa13027b` |
| `fixtures/ccm-core-v1/manifest.json` | SHA256 `28496929050e7cfeea214dbf0ee5cbd589a08ab2adb60e1849877778baaf9aed`; 16 archivos enumerados |
| `oracle.json` | SHA256 `d6dd932042d622b7ec9d2e1f5438d0fd8636d405d0fbb1c3856809017e38ec64` |
| `coverage-required.json` | **Revisión 2**, SHA256 `b248d6cea7d5b6994bcf21f6deb35a6a4887d4c4f5a8a3dcca09a84ac6f55655`; **34 grupos** |
| `docs/ACCEPTANCE_CRITERIA.md` | 14 criterios; bytes iguales a esta rama |
| `contracts/ccm-adapter.yaml` | Las mismas seis operaciones; bytes iguales a esta rama |

Se verificaron bytes y SHA256 de los 16 archivos contra el manifiesto,
incluidos los CSV con CRLF. El ExecPlan y CORE_TEST_SPEC corregidos **difieren
de las versiones antiguas de esta rama**: el plan usa expresamente los blobs
fijados. Por ejemplo, garantía conserva cantidad + DAY/MONTH/YEAR, sustituyendo
`warranty_months`; STORE usa FULFILLED y WEB SHIPPED. No se sobrescriben los
documentos antiguos ni se importan cambios de Frappe para resolver esa diferencia.

Tras autorización, se materializará exclusivamente el bundle compartido
`fixtures/ccm-core-v1` desde ese SHA, byte por byte, con comprobación previa y
posterior de sus hashes. No se copiarán la aplicación, scripts de plataforma,
locks de Frappe ni sus resultados PASS. Sus runners y evidencias se consultan
como descripción de las aserciones que debe reproducir Axelor.

El resultado publicado de Frappe es referencia histórica: 34 grupos PASS,
13/14 criterios PASS, criterio 13 BLOCKED y seis escenarios de patch UNRUN.
Esos estados no se transfieren a Axelor. No se reabre el cuestionario comercial;
se preservan LAB-ONLY-v1 y las decisiones de producción aplazadas.

## 2. Baseline comprobado antes de planificar implementación

Se leyeron primero CODEX_CLOUD_SETUP, AGENTS raíz/Axelor, versions.lock,
charter, protocolo y Task 100. Issue #1 preflight y guardrails se ejecutaron
antes de las comprobaciones del baseline, sin configurar Frappe.

| Comprobación | Resultado de esta preparación |
| --- | --- |
| Rama / estado inicial | `lab/axelor-baseline`, checkout limpio |
| Host oficial v9.1.8 | HEAD `1119727a3b53c8387b7fab535e184c25154d2eac` |
| Gitlink / AOS v9.1.8 | Ambos `0c70d561b19fc454eba9fdd41689258846626d75` |
| Java y javac activados por el helper | `21.0.12.1`, paquete `21.0.12.1+1-1~deb13u1` |
| Wrapper / AOP | Gradle `8.14.3`, plugin y artefactos AOP `8.2.3` |
| SHA256 de distribución del wrapper local verificado | `bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531` |
| `bash labs/axelor/scripts/validate.sh` | Compilación/JAR/metadata y **2 tests PASS**, 0 fallos/errores/skips, 15 s |
| Tests realmente ejecutados | `generatedMetadataIdentifiesTheCustomModule`, `registersWithThePlatformInjectorWithoutADatabase` |
| `ci/check-workflow.sh`, `ci/check-init-scope.sh` | Lint del workflow y ambas regresiones de scope/locks PASS; no son Core Test |
| `./scripts/preflight.sh`, `./scripts/verify-repo.sh` | PASS |
| Pins, wrapper original, `.gitmodules`, fuentes host/AOS | Sin diferencias tracked |

El preflight global detecta `javac` ausente del PATH por defecto; el JDK fijado
existe y el helper lo activa correctamente. No hace falta instalar otro Java ni
Gradle global. Las advertencias de APIs obsoletas no fallaron los checks; no se
actualiza a Gradle 9.

Se consultó la API de GitHub: el
[run 37228746936](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37228746936)
está `completed/success`, sobre
`cdc57c8656940fc6c4eed381244fbb514e702fcf`. HEAD actual difiere de ese código
solamente en documentación/reportes. Según su evidencia conservada en
[axelor-full-stack.md](axelor-full-stack.md), compiló AOS/frontend/WAR, ejecutó
2 tests Cencomun + 16 tests nativos de números fiscales, inició PostgreSQL 16.15
y probó autenticación/metadata y reinicio. Readiness inicial 422.42 s; reinicio
315.44 s. **Este turno no repitió ese job ni ejecutó servicios full-stack**;
el éxito histórico y los tests locales actuales tienen alcances distintos.

Conclusión acotada: Task 020 está validada para desarrollar la extensión. El
módulo sigue vacío y no demuestra reglas de ERP del Core Test. No se necesitan
cambios del borrador del entorno ni nuevos dominios para preparar este plan.

## 3. Diseño propuesto mediante mecanismos nativos

Se ampliará **el módulo existente** `labs/axelor/cencomun-baseline`, con código
propio en `com.cencomun.core.*`. No se creará un segundo módulo ni se editarán
fuentes upstream. Los modelos/vistas/configuraciones declarativos del módulo,
bindings Guice y repositorios soportados implementarán las extensiones.

| Clave | Mecanismo propuesto y frontera |
| --- | --- |
| N1 producto | Extensión XML de `com.axelor.apps.base.db.Product`, campos Cencomun y vistas extendidas; `Partner` cliente. Usar el merge de dominios soportado, como hacen sale/supplychain con Product. Java propio en com.cencomun; los modelos nativos generados conservan su paquete nativo y quedan como outputs, sin editar su fuente. Buscar/persistir campos con permisos de servidor. |
| N2 Cashea | Entidades Cencomun cabecera/líneas con Company/Partner/Product y referencias nativas. Estado funcional propio; servicio transaccional valida canal, actor, cantidades enteras y transiciones. Confirmar con `SaleOrderConfirmService.confirmSaleOrder`; cancelar con `SaleOrderWorkflowService.cancelSaleOrder`, sin escribir directamente statusSelect. |
| N3 inventario | `SaleOrderStockService.createStocksMovesFromSaleOrder`, `StockMoveService.plan/realize/cancel`, comprobación nativa `StockLocationLineService.checkIfEnoughStock`. Entrada inicial nativa, costos nativos, almacén por escenario. Consultar currentQty, avgPrice, WAP de líneas e historial; futureQty no representa existencia física. Una salida por pedido, sin duplicarla al facturar; sin reservas en este perfil. |
| N4 contabilidad | `SaleOrderInvoiceService` o `StockMoveInvoiceService`, `InvoiceLineService.compute`, `InvoiceService.validate/ventilate`, `InvoicePayment` y sus servicios de creación/validación. Invoice inAti con Tax/TaxLine sintéticos; Company/Account/Journal/Period/PaymentMode configurados. Evidencia desde Invoice, Move/MoveLine, pagos y aplicaciones nativas. Costo de ventas y retenciones requieren resolver B2 antes de ampliar casos. |
| N5 FX | `Currency`, `CurrencyConversionLine`, `CurrencyService`, CurrencyScaleService y autorización de tasa Cencomun. Rangos de validez de **un solo día** para fechas fijadas, selección exacta antes del pago y BigDecimal HALF_UP por línea; dinero escala 2 y tasas hasta 6. Sin fallback de tasa antigua. |
| N6 compras | Solicitud Cencomun enlazada a PurchaseOrder, acciones XML y servicios nativos `PurchaseOrderService.requestPurchaseOrder` y `PurchaseOrderWorkflowService`. Política LAB en servicio de aprobación: base con cargos/descuentos, tasa de solicitud, actor distinto del creador, nivel mínimo por umbral y versión de decisión. Revisar mediante ciclo nativo soportado, cancel/draft/request cuando corresponda; no restablecer statusSelect desde el adaptador. |
| N7 caja | Cierre Cencomun con snapshot por canal/moneda obtenido de MoveLine/pagos nativos; preparar/confirmar por servicio, sin contabilidad paralela. Confirmado inmutable también por REST/repositorio, no solo por botones. Cashea pendiente separado del efectivo. |
| N8 banco | `BankStatement/BankStatementLine`, credit/debit con signo normalizado, BankDetails/Company y `BankReconciliation`/líneas contra MoveLine; servicios de carga/conciliación nativos. Extensión Cencomun para hashes de archivo/transacción, clasificación LAB y decisión manual, sin autoelegir candidatos ambiguos ni utilizar escrituras SQL. |
| N9 seguridad/API | Roles/User, MetaPermission/MetaPermissionRule, `JpaSecurity.check/getFilter`, scope Company, guards en servicios/repositorios y acciones declaradas. REST/acciones autenticadas de AOP y un adaptador externo con seis rutas; ninguna conexión a PostgreSQL desde el adaptador/MCP. Las escrituras físicas/financieras directas fuera del servicio autorizado se rechazan. |
| N10 durabilidad | Entidades Cencomun RequestKey, Audit, Event/Outbox, Import/BankMatch/RateAuthorization con claves únicas y locks JPA. Resultado/payload hash persistidos; dominio + clave + evento en el mismo commit. AuditLog/track de AOP como soporte, más auditoría semántica inmutable. Rechazos auditados en una unidad de trabajo posterior al rollback, sin conservar efectos de negocio rechazados. |
| N11 tests/medición | JUnit y axelor-test con DI para unit tests; integración real sobre PostgreSQL en el host completo. Inspector nativo independiente por repositorios/servicios de lectura, separado del cálculo del adaptador. Cliente HTTP, MCP stdio y consumidor ficticio persistente; métricas por request mediante instrumentación soportada, sin capturar SQL ni secretos. |

El adaptador expondrá exactamente searchProducts, getInventory,
getCustomerBalance, createPurchaseDraft, getCashStatus y createCasheaOrder,
con las rutas actuales del contrato. Las acciones internas para aceptar,
entregar/liquidar, caja, tasas y banco se ejecutan por mecanismos Axelor
autenticados; no se añaden al catálogo de herramientas MCP ni al contrato neutral.
La identidad real de User se conserva hasta el servicio: ningún proxy ejecuta
los pedidos de todos los actores como administrador.

## 4. Oráculo que no puede cambiar

Conservar parámetros y respuestas del ExecPlan fijado, además de las cifras:
visibilidad y financiación independientes; garantías 30 DAY/6 MONTH/1 YEAR y
ceros con las tres unidades; precio conservado al deshabilitar Cashea;
referencia de proveedor distinta del SKU; cero/fracción/costo negativo inválidos;
roles y empresa; estados STORE/WEB; motivos; precisión; errores y deduplicación.

| Caso | Bruto / ingreso / impuesto USD | Comisión / envío | Neto agregado / indicador Cashea | Transferencia / pago directo | Resultado contable |
| --- | --- | --- | --- | --- | --- |
| CO00 | 125.00 / 125.00 / 0.00 | 8.00 / 0.00 | 117.00 / 47.00 | 67.00 / 50.00 | 47.00 |
| CO01 | 125.00 / 125.00 / 0.00 | 10.50 / 0.70 | 113.80 / 43.80 | 63.80 / 50.00 | 43.80 |
| TAX01-S | 137.50 / 125.00 / 12.50 | 8.80 / 0.00 | 128.70 / 58.70 | 73.70 / 55.00 | 46.20 |
| TAX01-W | 137.50 / 125.00 / 12.50 | 11.55 / 0.70 | 125.25 / 55.25 | 70.25 / 55.00 | 42.75 |

Cada caso: stock 5/5/5, valor 500.00 → 3/4/5, valor 430.00; costo 70.00,
una salida, una factura y dos pagos, saldo final 0.00. TAX01 mantiene un pasivo
12.50; se separa del indicador Cashea y no se añade otro impuesto al bruto.
La carga inicial se excluye de los asientos de venta. Normalizar categorías
de cuenta y suma Debe/Haber, sin exigir el mismo número de apuntes internos.
La liquidación aplica financiado = transferencia + comisión + envío, sin
descuento comercial de la base imponible, gasto duplicado o baja de deuda ficticia.

Compras: 199.99/200.00 BUYER, 200.01/999.99/1000.00 MANAGER,
1000.01 DIRECTOR; PO07 cargos/descuento → 200.00; PO08 8000 VES → 200.00;
PO09 8000.40 VES → 200.01. Cambio de monto invalida aprobación; no autoaprobación.
Caja CS000 sin diferencias; CS001 USD -2.00, VES +10.00, POS/TRANSFER 0.00,
Cashea pendiente 125.00, recibido 0.00. Banco: cinco filas, cuatro únicas,
un duplicado, una conciliación automática exacta; tres conciliaciones tras
decisiones manuales, T005 y BK004 pendientes; reimportar no añade efectos y -10
preserva signo. FX usa 40/41 por fecha y autorización de 40.5 para 2026-10-03;
dos líneas 0.01 → 0.41 + 0.41 = 0.82.

Normalizar solo IDs técnicos, sufijos nativos y timestamps generados mediante
mapping explícito. Dentro de una ejecución API/MCP, **los IDs nativos deben
ser idénticos**, también al invertir creación/replay. Dinero, datos funcionales,
stock, permisos, estados y errores no admiten normalización para ocultar diferencias.

## 5. Matriz de los 34 grupos obligatorios

IDs, fuente, revisión mínima y criterios proceden literalmente de
coverage-required.json revisión 2. Todos están **UNRUN en Axelor**; esta matriz
es trazabilidad del plan. Cada grupo deberá ejecutar sus subcasos completos,
con observación nativa, no un único test superficial por fila.

| # | Grupo exacto | Fuente / rev. mínima | Criterios | Ejecución y aserción propuesta |
| --- | --- | --- | --- | --- |
| 1 | CO00-NATIVE | business / 1 | 1,3,4,5,11 | N2–N4: STORE completo; documentos, balances y stock contra CO00. |
| 2 | CO01-NATIVE | business / 1 | 1,3,4,5,11 | N2–N4: WEB completo con guía; oráculo CO01 y gasto de envío una vez. |
| 3 | TAX01-S-NATIVE | business / 1 | 1,3,4,5,11 | N2–N4: inAti 10%, ingreso 125, pasivo 12.50; oráculo STORE. |
| 4 | TAX01-W-NATIVE | business / 1 | 1,3,4,5,11 | N2–N4: misma separación fiscal, comisión/envío WEB y saldos exactos. |
| 5 | PROD01-04 | business / 1 | 1,5,11 | N1: persistir seis pares de garantía; flags independientes, SKU/referencia y precio retenido. |
| 6 | VAL01-04 | business / 1 | 4,5 | N1–N4: qty cero/negativa/fracción, precio cero/negativo/0.005, P003 no elegible, financiado fuera de rango y costo nativo negativo: rechazo 422 sin efectos. |
| 7 | STATE01-04 | business / 1 | 3,4 | N2/N9: rutas válidas, REJECTED/CANCELLED previos, NEW→SETTLED y cancelación posterior rechazados, roles correctos. |
| 8 | INV01-03-INSUFFICIENT | business / 1 | 4,5 | N3: pedido 6 con stock5 queda APPROVED; no factura/salida; rollback e historial verificados. |
| 9 | FX01-03-MONEY01-03 | business / 1 | 3,5 | N5: fecha exacta, falta de tasa, autorización/denegación, 40/41 y redondeo 0.82; pagos nativos. |
| 10 | PO01-09-NATIVE | finance / 1 | 1,3,7 | N6: límites de seis compras + cargos/moneda PO07–09; ciclo nativo y matriz de roles. |
| 11 | PO07-09-REVISION-SELF | finance / 1 | 3,7 | N6: revisión Approved→Draft invalida decisión y reevalúa 200→200.01; denegar selfbuyer y montos inválidos. |
| 12 | CASH00-06-NATIVE | finance / 1 | 1,3,5,6 | N7/N4: movimientos fuente nativos; CS000/001, nota con diferencia, confirmación gerente y snapshots inmutables. |
| 13 | BANK-BOOK-FIXTURE | finance / 1 | 1,11 | N8/N4: crear cuatro cobros BK001–004 de CBANK por servicios y leer sus referencias/importes pendientes. |
| 14 | BANK01-05-NATIVE | finance / 1 | 1,3,8 | N8: exacto/probable/ambiguo/duplicado/unmatched; decisiones, reimportación y signo negativo, conciliaciones nativas. |
| 15 | API01-06-SIX-ROUTES | http / 1 | 3,9 | N9: las seis rutas; moneda/datos completos, NEW/Draft, primera201/replay200, payload conflict409. |
| 16 | IDEM01-02-CREATE-CONCURRENT | http / 1 | 3,4,9 | N10/N9: dos clientes misma clave → 201+200 y un objeto; otra clave mismo ID409; replay sin permiso403. |
| 17 | PERM-API-NATIVE | http / 1 | 3,9 | N9: matriz por adaptador, REST nativo y acciones; anónimo401, denegado403, inválido422/conflicto409, scope otra empresa y vínculos inalterables. |
| 18 | CASH04-06-HTTP-IMMUTABLE | http / 1 | 3,6,9 | N7/N9/N10: edición, confirmación y manipulación REST de confirmado rechazadas; actor/instante/snapshot intactos, rechazo auditado. |
| 19 | SEARCH01-04-NATIVE | http / 1 | 3,12 | N1/N9: conjuntos por código/nombre/proveedor, customer nombre/teléfono, factura/ref y TrackingNumber; páginas2 completas P001/P002/P003 sin duplicados ni fugas. |
| 20 | TAX02-04-IDEM-CONCURRENT | http / 1 | 3,4,5,9 | N2–N4/N10: pares de entrega y settlement STORE/WEB mismos keys →200/200, false/true; key distinta409; stock3 y efectos únicos. |
| 21 | BANK-CONCURRENT-1000 | http / 1 | 8,9 | N8/N10: mismo CSV1000 concurrente →200/200, created1000 en resultado original y replay; exactamente1000 líneas únicas. |
| 22 | MCP01-06-STDIO | http / 2 | 3,9,10 | N9/N11: initialize2025-03-26; seis tools; ocho pares completos API/MCP (seis + dos creaciones inversas), mismos IDs; excluir _meta y comprobar replay aparte. |
| 23 | IDEM03-LOST-RESTART | recovery / 1 | 4,9,14 | N10/N11: perder respuesta tras commit mediante salida73 del adaptador; reiniciar PostgreSQL/app/job/adapter y cache configurada; replay200, un objeto y mismos efectos TAX. |
| 24 | IDEM04-EVENTS-RECOVERY | recovery / 2 | 3,6,7,9,14 | N10/N11: 503 sin efecto → éxito y una aplicación → reinicio solo consumidor con persistencia → mismo event_id, dos recepciones y una aplicación. |
| 25 | FIXTURE-HASH-NATIVE-EXPORT | audit / 1 | 1,11 | N1/N11: 16 hashes, conteos/lecturas/exportación nativa, CBANK separado; comparar originales sin reinterpretar CSV. |
| 26 | AUDIT01-03-NATIVE | audit / 2 | 3,6,7,8 | N10: parsear before/after semánticos, actor/fecha/objeto/motivo/correlación, cadenas de estados y cifras/vínculos de compras/caja/tasa/banco; auditoría inmutable. |
| 27 | IDEM-TAX-NATIVE-EFFECT-COUNTS | audit / 1 | 1,4,5,8,9 | N3/N4/N8/N10: inspector independiente cuenta una salida/factura/dos pagos/evento por TAX, pasivo12.50, banco1000 e IDEM-LOST/CREATE únicos después del replay. |
| 28 | SUPPORTED-CONFIGURATION | audit / 1 | 1,3,11,14 | N1/N6/N9/N10: exportar modelos/bindings/roles/scopes/acciones/config Company-cuentas-Apps, instalación idempotente; configuración crítica solo UI=0. |
| 29 | STATE-UNKNOWN-ATOMIC | business / 2 | 3,4 | N2/N9: UNKNOWN-LAB por API409 y persistencia nativa rechazada; snapshots de todos los efectos iguales. Selección en UI sola es insuficiente. |
| 30 | STATE-DELIVERY-WITHOUT-ACCEPTANCE | business / 2 | 3,4,5 | N2/N3: STORE NEW/REVIEWED; WEB NEW/REVIEWED/APPROVED → físico rechazado409, sin efectos. |
| 31 | STATE-WEB-NO-GUIDE | business / 2 | 3,4,5 | N2/N3: PREPARING→SHIPPED sin guía422; sin factura, salida, pagos o nuevo evento. |
| 32 | STATE-CANCEL-BEFORE-HANDOVER | business / 2 | 1,3,4,5 | N2/N3: STORE APPROVED y WEB APPROVED/PREPARING → CANCELLED; SaleOrder cancelado nativamente, stock5/5/5, cero salida/factura/pagos/eventos nuevos; motivo/before/after. |
| 33 | MCP-FORBIDDEN-CRITICAL-ACTIONS | http / 2 | 3,6,7,8,9,10 | N9: ocho objetos elegibles del suplemento; tools no ofrecidas -32602 y llamada directa Axelor con mismo actor403: aprobación, entrega STORE, despacho WEB, dos settlements, caja, tasa y banco. |
| 34 | MCP-DENIALS-NATIVE-EFFECTS-AUDIT | audit / 2 | 3,4,5,6,7,8,10 | N9/N10/N11: ocho rechazos auditados, snapshots de estados/stock/asientos/saldos/eventos intactos; sin auditoría/evento de éxito. |

Distribución conservada: business13, finance5, http9, recovery2, audit5.
El serial mide búsqueda del registro nativo, no trazabilidad física; su límite
opcional se declara como en el ExecPlan, sin eliminar las búsquedas obligatorias.

## 6. Matriz de cierre de los 14 criterios

Todos pendientes de ejecución. La cobertura obligatoria se agrega con la
prioridad **FAIL > BLOCKED > UNRUN > PASS**, manteniendo los mínimos de revisión
y resultados de esta ejecución. Una fila ausente/antigua no permite PASS.
Los criterios 2 y 13 necesitan evidencia adicional a los 34 grupos.

| Criterio | Evidencia necesaria para evaluarlo |
| --- | --- |
| 1 objetos soportados | Grupos vinculados por coverage-required, metadata/modelos XML, registros nativos y puntos de extensión N1–N8. |
| 2 upstream intacto | Hashes/HEAD/gitlink y diff host+AOS, pins, wrapper, generación/empaquetado; upstream cambiado=0. |
| 3 permisos | Todos los grupos vinculados, matriz de roles/empresa por servicio/API/REST, negativas MCP y auditoría; ningún bypass de administrador. |
| 4 estados | Grupos de estados/validación/stock/idempotencia; atomicidad mediante snapshots nativos, no solo status del pedido. |
| 5 dinero | Cuatro oráculos completos, TAX concurrente, FX/half-up por línea, efectos contables/valoración nativos y negativos. |
| 6 caja | Cierre y ataques HTTP/nativos/MCP; auditoría útil e inmutable y recuperación del evento. |
| 7 compras | Límites, conversiones/cargos, revisión/selfbuyer, actor/versión y evento sin duplicación. |
| 8 banco | Importación y conciliación nativas, hashes/file replay/concurrencia1000, pendientes y denegaciones auditadas. |
| 9 API | Seis rutas por Axelor, errores/durabilidad/roles; adaptador sin drivers ni acceso DB de ERP. |
| 10 MCP | Seis tools, ocho equivalencias y negativas completas, mismo actor y mismos IDs nativos. |
| 11 fixtures | Hash/conteo/exportación y lectura por modelo nativo; también carga benchmark 1000 productos/100 clientes/1000 NEW/1000 filas. |
| 12 búsqueda | Conjuntos exactos, orden/paginación y scope, sin duplicados; límites de serial declarados. |
| 13 patch | En copia: target compatible fijado, backup, upgrade/migrate, suites completas de plataforma+Cencomun y restore; baseline18 tests no lo aprueba. |
| 14 reproducible | Instalación/config versionadas, recuperación, copia restaurada con nueva ejecución revisión2 de **13 grupos business +5 finance**, guardrails y hashes. |

Publicar PASS/FAIL/BLOCKED/UNRUN sin reducir denominadores. Un fallo observado
de una capacidad es FAIL; un prerrequisito imposible con causa comprobada es
BLOCKED y sus dependientes UNRUN. Aprobar exige **34/34 grupos y 14/14 criterios**
PASS, además del ensayo de patch; cierre con limitaciones no equivale a aprobación.

## 7. Bloqueos y comprobaciones técnicas prioritarias

No se ha demostrado un defecto funcional de Axelor: aún no se ejecutaron esos
casos. Se distinguen prerrequisitos observados de riesgos que requieren prueba.
Para cada condición se conservará primer error/comando/exit code y evidencia
saneada, impacto por grupo/criterio y solución verificable; no se altera el oráculo.

### B1 — build del módulo vacío y grafo de dependencias (prerrequisito observado)

El build actual no declara dependencias AOS; ccm-cloud.settings.gradle solo
incluye Cencomun. Los locks full-stack se generan por run y se reproducen offline,
pero no constituyen un grafo completo congelado en la rama. Sin preparación
adicional no se pueden compilar/importar servicios ERP desde el módulo Core.
Impacto: todos los grupos de integración, criterios 1/11/14.

1. Tras autorización, declarar dependencias de proyecto necesarias (supplychain,
   bank-payment y sus transitivas) en el módulo propio; configurar el host original
   completo externamente, conservando upstream y el wrapper verificado.
2. Congelar el grafo de Core y los runtimes de harness/consumidor con versión y
   checksum antes de ejecutar; locks propios o bundle externo inmutable verificable.
3. Verificar codegen/classes/test/JAR/WAR y replay estricto/offline sin tareas que
   escriban fuentes; comprobar extensión Product efectiva y upstream diff vacío.

### B2 — costo de ventas y retenciones de liquidación (riesgo no validado)

StockMove.realize y su extensión supplychain inspeccionados actualizan cantidades,
WAP y entrega; ese recorrido no acredita por sí mismo asiento COGS/Inventario.
AccountingCutOffSupplyChain genera apuntes de cut-off, que no deben confundirse
con costo de ventas. InvoicePayment presenta un importe y descuentos financieros;
no se ha probado que descomponga la comisión/envío de esta liquidación como exige
el fixture. Invoice usa escalas internas 3 y Product/Stock 10, frente a dinero LAB2.
Impacto: CO00/CO01/TAX01, VAL/INV/FX e IDEM-TAX; criterios 1/4/5/9.

1. Configurar Company, Apps, cuentas/journals/periodos, escala2, impuesto inAti
   y valoración nativa; ejecutar primero CO00 y TAX01-W en PostgreSQL aislado.
2. Inspeccionar stock/WAP y MoveLine reales. Verificar ingreso125, impuesto12.50,
   costo70, Inventario-70, transferencia70.25 y gastos11.55/0.70, saldo0 y Debe=Haber.
3. Si falta automatismo nativo, evaluar una extensión de servicio Cencomun que
   use **valoración nativa** y MoveCreateService/MoveLineCreateService/
   MoveValidateService.accounting y conciliación/aplicación nativa. Documentar
   intervención, vínculos y unicidad; no usar cut-off/descuento para alterar el impuesto,
   asientos externos, SQL ni fixtures con resultados cambiados. Mantener dos pagos.
4. Verificar concurrencia/rollback con un único StockMove/factura/impuesto/gasto.
   Si la vía soportada no logra esos efectos, reportar FAIL o bloqueo comprobado
   y continuar casos independientes; no certificar contabilidad con cálculos del adapter.

### B3 — seguridad nativa, estados y revisión de compras (prerrequisito observado)

JpaSecurity/REST soportan permisos y filtros, pero las reglas LAB no existen en
el módulo vacío. PurchaseOrderWorkflowService.validatePurchaseOrder inspeccionado
comprueba estado/cálculo y actor, sin aportar los umbrales USD y selfbuyer LAB.
Un selection XML o un botón oculto no demuestra rechazo por servidor; las tasas
CurrencyConversionLine aceptan fromDate/toDate, incluido toDate nulo.
Impacto: criterios 3/4/5/6/7/8/9/10 y grupos negativos/de FX.

1. Versionar roles/scopes y política LAB en servicios; conservar validaciones
   nativas y bindings de supplychain al extender sus repositorios/servicios.
2. Proteger también REST/actions/repositorios para vínculos, estados, físico,
   finanzas y cierre inmutable. Probar rechazo tanto con credencial como con DI
   bajo el actor real; no conceder write financiero a MCP para satisfacer otra ruta.
3. Configurar tasas de día exacto y validar ausencia antes de convertir/pagar;
   probar 2026-10-03 sin tasa y luego autorización40.5, dejando 2026-10-04 ausente.
4. Verificar todos los errores/snapshots del contrato y la revisión de aprobación
   por ciclo soportado. Cualquier diferencia conserva el resultado esperado y se registra.

### B4 — auditoría semántica y outbox durables (prerrequisito observado)

AOP contiene AuditLog con previous/current state y un bus de eventos; eso no
acredita motivo/correlación, inmutabilidad, auditoría de denegaciones tras rollback
ni entrega durable de eventos. El módulo vacío no tiene RequestKey/Audit/Outbox.
Impacto: criterios 3/4/6/7/8/9/10/14 y grupos AUDIT/IDEM/MCP.

1. Modelar persistencia mediante XML/repositorios JPA propios: claves únicas por
   empresa/operación/payload y tipo/objeto/versión de evento; locks JPA, no caché volátil.
2. Emitir outbox en el mismo commit del dominio; dispatcher mediante job/servicio
   soportado con retries. Persistir auditoría de rechazo fuera del rollback del dominio.
3. Ejecutar revisión2 íntegra: JSON útil antes/después, ocho negativas elegibles
   y ningún efecto de éxito; pérdida post-commit y secuencia503/éxito/reinicio/replay.
4. Verificar dos recepciones y una aplicación en el consumidor ficticio persistente,
   mismo event_id y IDs de negocio, también después de reiniciar la app/job/DB.

### B5 — ejecución y recuperación externas (prerrequisito observado)

El baseline de CI tiene un DB efímero y smoke de metadata; aún no tiene fixture
Core, backup/restauración, usuarios LAB ni el cliente de las 34 agrupaciones.
Cloud queda para análisis/compilación/unit tests. Impacto: integración completa
y criterio14; ningún supuesto de procesos conservados por snapshot.

1. Reutilizar GitHub Actions y sus contenedores fijados; añadir un job Core separado
   solo tras autorización, sin ejecutar automáticamente Core al editar este plan.
2. DB Core y DB recuperación **distintas de cualquier baseline**, marca de laboratorio,
   credenciales generadas privadas, pg_dump/pg_restore de PostgreSQL16.15, checksum
   y prueba de recuperación antes de restauraciones destructivas sobre DB propia.
3. Instalar apps/config por APIs/repositorios/servicios soportados, sin demos que
   contaminen casos. Readiness autenticada sobre fixture, timeout900s ya probado;
   los reinicios no se confunden con una recreación de DB.
4. Restaurar copia y repetir 13+5 grupos nativos revisión2; verificar comandos,
   conteos, source/pins y cleanup. Redis no se añade por imitar Frappe: reiniciar
   PostgreSQL/AOP/job/adapter y la caché que realmente configure este Axelor.

### B6 — patch y suite completa (etapa pendiente; no hereda el bloqueo de Frappe)

`git ls-remote --tags` de ambos upstreams ofrece **v9.1.9**: host commit
`a9291b7fd8b73210157f2843b4bbc6fa97419c37`, AOS/gitlink
`f8345ec00e9ad15db523ba0b8eb9f97f667b2e2c`. Se inspeccionó el host de ese commit
sin checkout: Java21, wrapper8.14.3 y plugin8.2.3. Es un **candidato**, no un target
de upgrade aceptado ni una prueba de compatibilidad. No se cambiaron pins/HEAD.
Impacto: criterio13 y sus seis escenarios adicionales, fuera de los 34 grupos.

1. Esperar Core estable de ambas plataformas; entonces fijar objetivo tras revisar
   migraciones/compatibilidad, sin alterar el baseline9.1.8.
2. Snapshot y copia, upgrade/migrate; ejecutar suites completas de módulos de
   plataforma y Cencomun, con fixtures oficiales aislados y conteos reales.
3. Verificar restore/rollback y los seis PATCH-TARGET/UPGRADE/MIGRATE/
   PLATFORM-FULL-REGRESSION/CENCOMUN-FULL-REGRESSION/RESTORE.
4. Si el target/suite se bloquea, registrar causa e intentos y mantener criterio13
   BLOCKED y dependientes UNRUN; no usar los 16 tests fiscales del baseline como sustituto.

### B7 — métricas comparables (limitación metodológica por resolver)

Frappe midió HTTP serial con datos congelados y recorder dentro del RPC. El
baseline Axelor solo midió readiness; no tiene métricas de negocio/query/DB por
request ni recursos idénticos demostrados entre Cloud y GitHub Actions.
Impacto: comparación de rendimiento; no cambia el oráculo funcional.

1. Aislar benchmark después del checkpoint: 1000 productos,100 clientes,1000 NEW,
   1000 filas; semilla100. Misma carga/payload/IDs deterministas, sin medir replay como create.
2. Por search/inventory/create:20 warmups y1000 muestras seriales; p50/p95/p99
   nearest-rank, tiempos crudos ms, errores y métricas nativas por request.
3. Instrumentar de forma soportada y apagar medición al terminar; registrar CPU,
   límites cgroup, memoria, JVM/GC, DB, workers y frío/caliente. Si los recursos
   difieren, explicarlo y no inferir ganador/SLA; métrica inaccesible=N/D con motivo, nunca0.

## 8. Secuencia acotada después de autorización

1. **Congelar entrada y runner**: bundle exacto, mapping, locks/runtime del harness,
   scopes, recuperación probada y host completo (B1/B5). Mantener el preset de
   gestores de paquetes; sumar solo dominios con bloqueo observado. TLS/checksums
   activos, sin secretos de producción.
2. **Validar el camino nativo crítico**: producto, CO00 y TAX01-W, contabilidad,
   stock, liquidación y negativos (B2/B3). Esta etapa decide si el diseño soportado
   reproduce el oráculo; un impedimento se publica antes de ampliar trabajo.
3. **Completar los siete bloques**: producto/Cashea/caja/compras/banco/API-eventos-MCP/
   búsqueda, permisos y auditoría. Tests de servidor y aceptación por cada bloque;
   no cambiar resultados ni upstream para obtener PASS.
4. **Ejecutar matriz34 revisión2** en PostgreSQL/host completo: business13→finance5
   →http9→recovery2→audit5, con preparación de objetos elegibles y almacenes por
   escenario. Restaurar el checkpoint al repetir una suite; preservar intentos,
   evitar resultados acumulados o antiguos y continuar casos independientes.
5. **Reproducir y medir**: copia restaura y repite business13+finance5; benchmark
   separado; packaging/metadata, locks offline, source/guardrails y conteos.
6. **Evaluar patch** solamente al cumplir su condición (B6), en copia aislada.
7. **Publicar evidencia de Axelor**: comandos/exit codes, run/commit/hash manifest,
   actual nativo por grupo, coverage revision2, matriz14 y métricas/limitaciones.

Ubicaciones futuras propuestas: código/config/test en el módulo Axelor existente;
harness en `labs/axelor/core-test/`, CI bajo `labs/axelor/ci/` y workflow Axelor;
resultados en `reports/evidence/axelor-core/` y `reports/axelor-core-test.md`.
No se crean ahora. Los grupos conservarán los nombres de fuente business/finance/
http/recovery/audit para contrastar cobertura; el publicador será de Axelor,
sin rutas ni lectura de evidencia Frappe para decidir PASS. Regresiones de
clasificación/archivado comprobarán casos ausentes, evidencia antigua y
FAIL/BLOCKED/UNRUN antes de confiar en el informe agregado.

El oráculo se consume únicamente en aserciones del harness, nunca como fuente
de importes/asientos para los servicios. Las extensiones calculan con entradas
del pedido y costos/validaciones nativos; el inspector lee los documentos
persistidos y comprueba sus efectos. Los guards LAB se limitan a la empresa y
objetos marcados: un contexto interno de escritura autorizada no puede ser
aportado por headers del cliente ni sobrevivir entre requests.

Registrar archivos/LOC propios, migraciones/configuración, upstream0, build y
tests con su alcance, llamadas ERP por acción neutral, tiempos, workarounds,
huecos documentales e intervenciones. Guardar datos privados/backups fuera de
Git y artefactos; publicar solamente evidencia sintética saneada. Excluir Cashea/
MRW reales, fiscalidad venezolana, combos cero, devoluciones, variantes, cargas
comerciales, producción y decisiones comerciales aplazadas.

## 9. Fuentes nativas inspeccionadas

Paths relativos al AOS fijado
[`0c70d561b19fc454eba9fdd41689258846626d75`](https://github.com/axelor/axelor-open-suite/tree/0c70d561b19fc454eba9fdd41689258846626d75):

- Dominios base/Product, sale/Product y supplychain/Product: merge de entidad;
  stock/StockLocationLine: currentQty/futureQty/avgPrice; stock/StockMoveLine:
  cantidades/escala10/WAP; stock/StockMove: trackingNumber; account/Invoice:
  inAti/totales/escala3; bank-payment/BankStatementLine: credit/debit/ref/fecha.
- SaleOrderConfirmSupplychainServiceImpl:85–155; SaleOrderStockService;
  SaleOrderWorkflowServiceSupplychainImpl:87; StockMoveServiceImpl:526–605;
  StockMoveServiceSupplychainImpl:171–250; StockLocationLineServiceImpl:366.
- SaleOrderInvoiceService, InvoiceService, InvoiceLineServiceImpl:394–434,
  InvoicePaymentMoveCreateServiceImpl:140, MoveCreateService,
  MoveLineCreateService, MoveValidateService; AccountingCutOffSupplyChainServiceImpl.
- PurchaseOrderService.requestPurchaseOrder y
  PurchaseOrderWorkflowServiceImpl:69–90; CurrencyServiceImpl:130–158;
  BankReconciliationReconciliationServiceImpl y SupplychainModule:431–453.
- APIs públicas verificadas con javap en los JARs AOP8.2.3: JpaSecurity,
  JpaRepository, Resource, RestService, AuditLog, JPA, GuiceExtension y JobRunner.

La inspección acredita existencia de estos mecanismos, no ejecución de reglas
del Core Test ni ausencia de otros mecanismos aún no explorados.

## 10. Estado de entrega y límite de autorización

- [x] Baseline y pins comprobados, preflight antes de Task100.
- [x] ExecPlan/referencia/oráculo/manifiesto/revisión2 leídos sin merge ni checkout Frappe.
- [x] 34 grupos y 14 criterios mapeados; causas/impactos/pasos/verificación documentados.
- [x] Plan acotado y coherencia de IDs/revisiones/criterios/hashes comprobada.
- [x] **Autorización explícita recibida para implementar este plan en Axelor.**
- [ ] Crear/ejecutar los 34 grupos y publicar resultados completos; en curso.

La preparación original se limitó a este documento. Después, el usuario autorizó
implementación, ejecución, commit/push exclusivamente a lab/axelor-baseline y CI.
Main, Frappe, producción, versions.lock y fuentes upstream quedan fuera del alcance.
No hay autorización para merge, despliegue ni cambio de pins/objetivo de actualización.

### Repetición 37411893961 y correcciones B11–B14

Artefacto completo conservado: 2 gates BLOCKED, PROD/SEARCH/BANK-BOOK FAIL,
29 grupos UNRUN. Usuarios reales y frontera de Sequence comprobados; no hay
éxito económico. Se conserva colección de Move, se autorizan cuentas concretas
por journal, se corrigen tipos de permisos y paginación AOP. 14 regresiones
Python, 2+7 tests propios y compilación full-native/offline pasan localmente.
Repetir gates primero e independientes después; no declarar correcciones
verificadas en ERP hasta esa ejecución. No se amplía la red ni se cambia upstream.

### Independiente N5 — FX01-03/MONEY01-03

Se prepara mientras corre el único CI de los gates; no se cancela ni duplica ese
job. Los dos rangos de CurrencyConversionLine duran exactamente un día, de
profile.json. CurrencyService selecciona la fecha y convierte/redondea cada
línea; no se introduce tasa anterior, oráculo en el cálculo ni tabla paralela.
La ausencia de tasa debe devolver 422 desde el fallo nativo. Un operador real
recibe 403 al autorizar; sólo CCM Manager puede registrar la tasa manual.
CcmRateAuthorization conserva FK a la conversión y compañía, motivo y usuario
real, dentro del mismo commit. Se usa el repositorio y tracking de AOP.

Aceptación parcial de conversión: dos conversiones fijadas; rechazo sin tasa;
rechazo del operador; ambos con snapshot fresco sin diferencias; autorización
por login manager y lectura nueva; 0.41+0.41=0.82 desde el servicio nativo.
La revisión de paridad B19 confirma que falta el recorrido de pagos: cuatro
pagos nativos contra tres facturas USD, como en la referencia fija. El grupo
completo exige los pagos VES 40/41/0.41/0.41, fecha/tasa/ID observado, asiento
ACCOUNTED en USD, conciliación confirmada y factura liquidada, todos leídos
en otra petición después del commit. Tasas y cálculos solos nunca aprueban el grupo.
La API de prueba exige CCM_CORE_LAB y compañía LAB. No añade herramientas MCP
ni aprueba los seis endpoints, auditoría integral o idempotencia. El grupo
conserva UNRUN hasta el siguiente CI; los tests locales sólo validan compilación
y rechazo de evidencias incorrectas. Pins/fixtures originales intactos.

### Repetición 37413918081 y siguiente ejecución

PROD completo PASS; stock inicial real 5/5/5 persistido, sin Sequence NoResult.
Gates bloqueados al finalizar el SaleOrder construido sin estado inicial.
Se usa SaleOrderCreateService, conservando todos los servicios posteriores y
sell como una transacción. El inspector añade el asiento de apertura separado
de efectos de venta. SEARCH se instrumenta para distinguir cliente/scope/consulta;
no se modifica su permiso sin causa demostrada. BANK conserva saldo nativo firmado
y exige el importe no aplicado positivo del fixture. FX/MONEY entra al siguiente
CI como independiente, sin preceder los dos gates. 17 regresiones locales.

Artefacto 11390399358 bloqueado por proxy (sa17, Forbidden, dos intentos);
no se añade dominio ni se publica red. Se conserva log completo y avisos JSON
etiquetados como fuente secundaria. Los avisos controlados no se recortan a mitad
de JSON; exports fallidos se guardan antes de evaluar. El CI anterior ya terminó,
por lo que el siguiente push no cancela ni duplica tareas.

### Revisión de paridad B19 durante CI 37416107406

Se conserva ese único CI, sin cancelarlo. El extractor y finalize revalidan
el caso FX desde sus datos nativos y rechazan el PASS antiguo de seis pasos;
los cálculos válidos se conservan como parciales. Una regresión reproduce
exactamente ese error de completitud. Se añaden rechazos de pagos ausentes,
lecturas sin frontera de commit, asiento draft, fecha incorrecta y deuda pendiente.

La extensión InvoiceGenerator oficial prepara el encabezado. InvoiceLineService
calcula la línea P002 sin mover stock; InvoiceService valida/contabiliza la factura.
InvoicePaymentCreateService, InvoiceTermPaymentService y InvoicePaymentValidateService
generan cuatro cobros VES, asientos y conciliaciones. Preparación de journal,
cuenta CASH-VES y secuencia confirma antes; cada factura y todos sus pagos
comparten transacción. No se escriben estados o saldos para simular éxito.
El compilador consume el proyecto axelor-account ya fijado del mismo host;
la extensión se compila sólo en el perfil full-stack, sin nuevos pins de baseline.
El reloj LAB avanza al último día de fx.json tras los gates para mantener
activa la validación nativa contra facturas futuras. No cambian fechas ni tasas.
### Continuación autorizada — SEARCH y PDF LAB (2026-10-06)

CI37425320931 confirmó el guardado nativo de dirección y ejecutó PROD/BANK
PASS, SEARCH/FX FAIL y gates BLOCKED por PDF opcional. Se registran B28/B29
antes de ampliar trabajo. Corregir únicamente placeholders de Permission.condition,
con scope y parámetros intactos; probar composición nativa y repetir búsquedas
por lector/denegación ajena. Configurar AppInvoice PDF automático false sólo en
LAB, con ventilación false (no omitida) y lectura efectiva/persistida posterior
al commit. Las regresiones locales no sustituyen aceptación por CI. Continuar
CO00 primero, TAX01-W segundo y casos independientes; conservar resultados
parciales frente a grupos completos. No cambiar oráculo/fixtures/pins/upstream.

### CI37429209635 y revisión de vínculo nativo — 2026-10-06

CI finalizado FAILURE: 3PASS/3FAIL/28UNRUN, criterios1PASS/6FAIL/6UNRUN/1BLOCKED.
Dirección nativa, configuración PDF=false/ventilación=false, PROD/BANK y los
cuatro pagos FX se verificaron en este commit. Gates y SEARCH fallan por vínculo
de factura no exportado; B30 documenta causa/impacto antes de ampliar trabajo.
Usar el overload completo INVOICE_ALL con guard nativo, conservar getInvoices
y verificar cabecera/FK de líneas/compañía/GL después del commit. Lectura de
lector conserva scope y prueba denegación403; no agregar permisos. Regresiones
rechazan cabecera null y vínculos aparentes por referencia. Repetir CO00 antes
de TAX01-W y después casos independientes en un solo CI. Gates administrador
PASS seguirán siendo parciales; 34 grupos/14 criterios completos no se infieren.

### Independiente — FIXTURE-HASH-NATIVE-EXPORT

Preparado durante el único CI37432900300, sin cancelarlo ni duplicarlo.
La referencia fija exige hashes de16 archivos, tres productos/clientes,
VES nativo y nueve roles cargados. El módulo ya crea Reader/Operator/Manager;
se preparan sólo los restantes metadatos Role por repositorio nativo, sin
usuarios/contraseñas/grants nuevos ni cambios a los permisos existentes.
Su existencia no aprueba subcasos funcionales de roles, compras, caja o MCP.
El inspector lee bytes del bundle realmente cargado en el JAR y modelos
persistidos, después de otro commit/petición; exporta IDs/FK/valores reales.
Runner/finalize/extractor revalidan contra el mismo manifiesto y fixtures;
regresión rechaza PASS sólo con hashes, registros ausentes, IDs duplicados,
valores/compañía distintos y lecturas dentro de la transacción de preparación.
Se añade además lectura company/Account.company/MoveLine.move del GL para
verificar explícitamente scope y propiedad de los asientos de los gates.
Los exports grandes se publican por registros completos numerados; el extractor
sólo reconstruye la sección cuando están todos, sin índices duplicados.
Una regresión verifica pérdida/duplicación sin inferir evidencia ausente.
Nada se cuenta como aceptación ERP hasta el siguiente CI completado.

CI37432900300 finalizó: CO00/TAX01-W gates administrador PASS, getInvoices y
cabecera/FK/compañía comprobados después del commit; oráculo revalidado desde
export completo con código de842a4dadcd74470dc6041d67d59bdfaf28803410. SEARCH
lector y403 ajeno PASS; PROD/BANK/FX completos PASS del mismo commit.
Matriz4PASS/30UNRUN, criterios1PASS/12UNRUN/1BLOCKED. No se completan los grupos
económicos por esos gates. Se envía una única ampliación independiente del
export de fixtures/scope GL después de terminar ese CI; repetir gates primero.

## Continuación agrupada: ciclo de pedidos, roles y atomicidad

Después de CI15 se ejecutará un bloque único: cuatro recorridos económicos por
operador/simulador reales, ocho validaciones, insuficiencia de stock, estados
excepcionales y negativos revisión2 (2 desconocidos,5 entregas sin aceptación,
WEB sin guía,3 cancelaciones previas). Los modelos Cencomun usarán FK reales a
SaleOrder/StockMove/Invoice; las transiciones económicas, clave, auditoría de
éxito y outbox comparten transacción. Los rechazos auditan tras rollback, sin
conservar efectos económicos. La posible incompatibilidad de cancelación nativa
confirmada está descrita en B31 antes de ampliar el trabajo. Los subcasos se
revalidan por lecturas posteriores al commit; ninguna etiqueta PASS se hereda.
Continuarán compras, caja, banco, API/MCP, concurrencia, recuperación y medición
según esta matriz; un avance parcial no cierra la tarea autorizada.

Revisión causal de los negativos de 80f94067: controles nativos válidos y causas
específicas obligatorios para enum/coste; CRUD genéricamente prohibido o clase
AxelorException solos no aprueban. Revisor reforzado aplicado también al CI16,
sin sustituir evidencia ejecutada ni duplicar su job. Cancelación confirmada
que contradice el contrato se clasifica FAIL funcional observado (B31),
con tres tentativas independientes, expectativa intacta y rollback comprobado.

### Continuación financiera agrupada posterior a CI16

Seis grupos se ejecutarán en el mismo run: PO01–09, revisión/self, CASH00–06,
CASH04–06 HTTP inmutable, BANK01–05 y BANK-CONCURRENT1000. PurchaseOrder nativo
create/request/validate/cancel/draft; fecha solicitud01Oct y tasa40; PO07 usa
TaxLine porcentual de15/base180 y freight10 con descuento fijo5 (totales nativos).
CcmPurchase guarda control de rol/decisión y FK, no sustituye el ERP. Una revisión
invoca cancel/draft oficiales: invalida estado y firma vigente; el historial
validatedBy/date del documento nativo permanece como historial de su decisión
anterior, y sólo su nuevo REQUESTED→VALIDATED puede aprobar la revisión.
Caja deriva sólo de ocho Move/MoveLine ACCOUNTED del journal dedicado; VES usa
CurrencyService/MoveLineCreateService y el pending125 nativo no es recibido.
Banco usa BankStatementLineCreationService y BankReconciliationLine/Validate;
composición de CSV compartido, signos y criterio de emparejamiento propios,
efectos/FK/status/remaining nativos. IBAN público de ejemplo, cuenta/cliente
sintéticos del LAB; no son credenciales ni datos de producción.
Toda aceptación continúa pendiente de CI, con conjuntos cerrados de subcasos,
controles de roles, snapshot independiente y agregador que rechaza pruebas vacías.


Continuación B34 (2026-10-06): CI7d9702f ejecutó 22 grupos, 16PASS/6FAIL/12UNRUN.
Los cuatro ciclos económicos completos y ambos grupos de caja pasan. Conservar
coste/cancelaciones como FAIL funcional. Corregir línea de compra nativa no
computada y campos Bank inexistentes, con regresiones de API oficial. Implementar
un bloque de seis grupos API/stdio/permisos; restringir private audit/key/outbox
y escrituras MCP en servicios, acciones oficiales y CRUD. Guardas Guice son
extensión Cencomun LAB, upstream intacto. Todo PASS requiere runtime del commit;
seguir impuestos concurrentes, auditoría, eventos, recuperación y benchmark.
