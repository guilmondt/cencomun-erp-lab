# Architecture Decision Log

## ADR-XXX — Title
- Date:
- Platform: Shared / Frappe / Axelor
- Status: Proposed / Accepted / Rejected / Superseded
- Context:
- Options considered:
- Decision:
- Consequences:
- Upgrade impact:
- Evidence/tests:

## ADR-001 — Isolated Axelor cloud module baseline

- Date: 2026-10-04
- Platform: Axelor
- Status: Accepted for the initial laboratory baseline
- Context: Task 020 requires a custom module on Java 21, AOS v9.1.8 and AOP
  8.2, without upstream changes or business features. Full-stack services
  belong in a dedicated runner.
- Options considered: configure/build every AOS module in cloud; prepare a
  representative empty module in the official pinned webapp host.
- Decision: use webapp commit `1119727a3b53c8387b7fab535e184c25154d2eac`, its
  exact AOS gitlink, AOP 8.2.3, Java 21.0.12.1 and a checksum-enforcing local
  copy of its Gradle 8.14.3 wrapper. Register `com.cencomun:cencomun-baseline`
  through local integration, with scoped settings preserving the host root
  build/buildSrc, and lock the new module's dependency graph.
- Consequences: upstream tracked files and `versions.lock` remain unchanged;
  cloud validates module compilation, injection compatibility and generated
  discovery metadata. It does not establish whole-suite/ERP/server/database
  readiness. No Cencomun business behavior is implemented.
- Upgrade impact: the local scoped settings generator requires the pinned
  host's settings layout; Gradle alternate-settings deprecation must be
  revisited in a separately authorized wrapper upgrade. Full-suite frontend
  and database dependencies require dedicated runner validation.
- Evidence/tests: `reports/environment-preflight.md`,
  `reports/axelor-baseline.md`; 2 tests passed, 0 failed/errors/skipped;
  repeated setup and frozen-lock compile/test/JAR validation passed.

## ADR-002 — GitHub Actions for Axelor full-stack validation

- Date: 2026-10-04
- Platform: Axelor
- Status: Accepted; full-stack baseline validated on the hosted runner
- Context: Cloud setup reserves full ERP/database/service tests for an external
  runner. The user delegated the choice and repository GitHub Actions works.
- Options considered: hosted GitHub Actions; a maintained self-hosted server.
- Decision: use a branch-triggered workflow and disposable PostgreSQL/build
  containers on an actual hosted Docker VM. Fix official image/action/runtime
  references; keep the existing AOS/AOP commits, wrapper and Cencomun module.
- Consequences: no server administration or production secrets needed. Preserve
  source, frozen frontend installation and external per-run dependency locks;
  publish sanitized logs/test artifacts and authenticated read-only API evidence.
  Full-suite Maven locks are evidence of each run, not yet a completely frozen
  branch dependency replay. Cloud networking remains restricted and separate.
- Upgrade impact: changing an image/runtime/upstream reference requires its own
  checksum/reference checks and rerunning compilation, API smoke and restart.
- Evidence/tests: `reports/axelor-full-stack.md`,
  `reports/axelor-full-stack-exec-plan.md`, `.github/workflows/axelor-full-stack.yml`;
  run 37228746936 passed full compilation/WAR, 18 unit cases, strict offline
  Gradle replay, PostgreSQL authenticated metadata API and server restart with
  33 modules. First startup 422.42s, restart 315.44s; tracked upstream diffs empty.

## ADR-003 — Native Core entities with an independently retained cloud baseline

- Date: 2026-10-06
- Platform: Axelor
- Status: Accepted within the user-authorized Core Test implementation
- Context: Shared product fields require durable framework entities and real
  foreign keys to native company/product, while the original cloud AOP-only
  compilation and its frozen dependency lock remain reproducible.
- Decision: declare Cencomun models in `com.cencomun.core.db`; the full-stack
  profile depends on the existing pinned AOS base project. Its build directory
  is `build/full`, set before AOP plugin application in the supported CI init
  script. Full dependency locks remain external per-run evidence. Cloud compiles
  the AOP services/policies, generates and parses the domain, and excludes
  native-FK generated classes/resources from its artifact.
- Consequences: full-stack compilation and authenticated native CRUD are
  mandatory for entity acceptance. Cloud unit tests never prove their native
  persistence. Exclude any merged `com.axelor` generated dependency classes
  from the custom compilation; verify that its full JAR contains none. All
  native ERP classes remain supplied by the fixed upstream modules.
- Permissions: product tests use an actual synthetic operator, native Role and
  Permission with `self.company.id = ?1` evaluated from `__user__.activeCompany.id`.
  No global wildcard grant, impersonation or administrator CRUD acceptance.
- Upgrade impact: AOS API or domain changes require recompile and native FK/CRUD
  regression on a separately approved target; no baseline pins are changed.
- Evidence/tests: `PROD01-04` runner implements six warranty quantity/unit
  round trips and price retention on disable, with separate committed REST
  rereads. Acceptance remains pending until the new full-stack run executes it.

## ADR-004 — Native daily currency configuration and scoped rate authorization

- Date: 2026-10-06
- Platform: Axelor
- Status: Implementation authorized; native acceptance pending
- Decision: use AOS CurrencyConversionLine with one-day validity and the pinned
  CurrencyService for payment-day selection and line rounding. Manager
  authorization lives in a Cencomun AOP entity linked to the native conversion,
  with company, reason and actual approving User in one transaction. Native
  overlap validation remains enabled. No external provider or secret is used.
- Permissions: authenticated native Operator/Manager sessions can calculate;
  only Manager can authorize in the LAB company. The custom service checks the
  actual native role and company on each call. No general currency/AppBase CRUD
  grant is given. The service is unavailable unless CCM_CORE_LAB=1.
- Consequences: AOS currencies are global application configuration in this
  isolated database. This test does not establish a production multitenant FX
  policy, the six neutral routes, audit completeness or rate idempotency.
- Evidence: conversions/rates are partial. Complete FX01-03-MONEY01-03 parity
  requires three native USD invoices and four native VES receipts (40, 41,
  0.41, 0.41), with posted USD effects and liquidation read after commit.
  The supported InvoiceGenerator extension uses the existing pinned account
  project; InvoicePayment creation, term allocation, validation, posting and
  reconciliation remain native. Dedicated LAB CASH-VES account/journal/sequence
  commit during preparation. Missing-rate/operator denials must leave all native
  effects unchanged. No stocks are moved for these invoices, matching the reference.
- Rounding: the daily USD/VES quote and the posted VES/USD effective rate are
  exported separately. Native posting derives the latter from rounded company
  amount/payment amount: 0.01 USD / 0.41 VES, not an invented exact reciprocal.
  Acceptance checks both the native daily quote and rounded booked amounts.
  The aggregator rejects calculations alone; native runtime verification is pending.

## ADR-005 — Preparación nativa de direcciones y preflight enfocado

- Date: 2026-10-06
- Platform: Axelor
- Status: Accepted within the authorized fixture correction; ERP CI validation pending
- Context: The actual AddressBaseRepository save renders all lines, computes
  fullName and checks required AddressTemplateLine.metaField before persistence.
  Testing the renderer alone missed a null child collection in CI 37420752108.
- Decision: resolve persisted native Address metadata initialized by AOP; create
  the five DEFAULT importer fields with streetName/city/zip required, use native
  parent helpers and modern address fields. Keep all formatting and validation
  in the unchanged native repository. Run callback regressions, then a focused
  authenticated ERP save/post-commit read/replay before economic gates/restart.
- Consequences: only fixture prerequisites are prepared separately; no business
  oracle, transaction boundary, permission or baseline pin changes. Local JPA
  lacking native HTTP scope is diagnostic only; CI remains Core acceptance.
- Upgrade impact: recheck the official metadata/importer/save contract in a
  separately approved isolated upgrade; no baseline upgrade is authorized here.
- Evidence/tests: 8 native callback cases passed locally; local JPA stopped at
  RequestScoped initialization, save UNRUN. Current CI and evidence are recorded
  in reports/axelor-core-test.md; no historical Core PASS is carried forward.
## ADR-006 — Placeholder nativo para Permission.condition

2026-10-06. CI37425320931 reproduce búsquedas vacías por lector y error nativo
String/Long. AOP8.2.3 Filter.build numera cada `?`; condiciones previamente
numeradas producen una consulta final que reutiliza el primer binding para
compañía y nombre. Se usan placeholders `?` exclusivamente en Permission.condition,
como los permisos oficiales AOS fijado. Scope/conditionParams y grants quedan
idénticos; consultas directas Query mantienen `?1`. Cinco regresiones ejecutan
Filter/JPQLFilter/Query nativos, incluidas composición nombre/teléfono, factura,
reproducción del defecto y Query directo. Aceptación autenticada del ERP pendiente.

## ADR-007 — PDF automático de factura fuera del contrato Core LAB

2026-10-06. Autorización expresa del usuario tras CI37425320931: configurar
AppInvoice.autoGenerateInvoicePrintingFileOnSaleInvoice=false sólo con
CCM_CORE_LAB=1 y administrador del fixture. Se usa repositorio AppInvoice
nativo; no se modifica upstream ni se crean PrintingTemplates/demo. La
configuración efectiva del AppAccountService y la persistida se exportan en
lecturas posteriores al commit; ambas deben mostrar PDF automático false e
isVentilationSkipped=false. Una configuración con ventilación omitida se rechaza.
InvoiceService.validate/ventilate, reglas, roles, GL y oráculo permanecen íntegros.
Contabilización y save preceden la rama opcional PDF en AOS fijado. Dos tests
nativos de configuración PASS; la evidencia económica exige GL contabilizado,
pagos y liquidación reales. PDF automático no se prueba ni equivale a validación
económica. Repetición en CI pendiente.

## ADR-008 — Facturación completa INVOICE_ALL y trazabilidad nativa

2026-10-06. CI37429209635 confirmó stock/COGS/liquidación nativos y cuatro
pagos FX, pero el overload corto no asignó Invoice.saleOrder. El inspector de
cabecera omitió facturas/GL/pagos del gate y SEARCH no probó su vínculo.
Se ejecuta el overload completo del wizard fijado con INVOICE_ALL de la clase
oficial SaleOrderRepository y su guard de facturabilidad. La cabecera la asigna
y guarda AOS; Cencomun no repara FK ni modifica upstream. Se conserva getInvoices
como lectura oficial y se exige después del commit tanto cabecera como cadena
InvoiceLine.saleOrderLine.saleOrder y propiedad InvoiceLine.invoice, con misma
venta/compañía. La consulta por referencia externa es sólo un selector; nunca
sustituye las FK. El lector usa sus permisos Invoice existentes y la denegación
ajena sigue siendo 403. No se cambian oráculo, estados, pins ni transacciones
económicas. La regresión rechaza cabecera null, fuente ausente, factura/venta
equivocada y compañía ajena. Compilación local no sustituye aceptación ERP.

## ADR-009 — Export verificable de fixtures y metadatos de roles

2026-10-06. El grupo independiente FIXTURE-HASH-NATIVE-EXPORT conserva el
contrato de la referencia fija:16 hashes del bundle cargado, productos y
clientes nativos, VES y nueve metadatos Role. Sólo se crean los Role ausentes
en el runtime LAB por repositorio nativo. No se crean usuarios/credenciales
ni se cambian grants existentes. Cargar nueve nombres no aprueba permisos
funcionales; esos grupos/subcasos mantienen su estado pendiente.
Una petición posterior al commit exporta IDs/FK/valores y hashes reales.
Runner, finalizador y recuperación de logs rechazan PASS sin export completo
o que contradiga los fixtures. Sin cambiar oráculo ni resultados esperados.
Los gates añaden scope nativo de Move/Account y propiedad MoveLine.move;
es una comprobación adicional, sin modificar efectos económicos.

## ADR-010 — Estado Cencomun con efectos y seguridad nativos

2026-10-06. Se reutiliza el único módulo para CcmOrder/líneas, claves,
auditoría y outbox. FK de compañía, producto, actor, SaleOrder, StockMove e
Invoice son reales. Se incorpora únicamente el proyecto supplychain del AOS
fijado, sin artefactos/versiones nuevos ni cambiar locks/pins originales. Los
servicios nativos confirman en APPROVED, entregan/facturan/contabilizan COGS en
FULFILLED/SHIPPED y cobran/liquidan en SETTLED. La transacción incluye estado,
clave, auditoría de éxito y evento; el recurso registra rechazos después del
rollback. Fallos sintéticos tras entrega/liquidación prueban rollback real.
Los repositorios Cencomun bloquean CRUD genérico y la auditoría es inmutable.
Roles reales separados conservan grants previos; permisos READ usan scope de
compañía y placeholders oficiales. Los usuarios sintéticos existen sólo en
la DB efímera del CI, sin credenciales persistentes locales/producción.

B31 conserva como incompatibilidad a probar la cancelación nativa de pedidos
confirmados. No se degrada statusSelect ni se suplanta el servicio nativo.
El costo negativo se intenta con un StockMove real; si el ERP lo acepta se
revierte únicamente para limpiar el diagnóstico y el subcaso queda FAIL.
Cada grupo tiene una lista cerrada de subcasos, con snapshots posteriores a
commit/rollback y regresiones del agregador. El éxito de administrador no
sustituye roles/estados/atomicidad. Los resultados grandes del log se fragmentan
con índices únicos, cantidad exacta y SHA256, sin aceptar evidencia truncada.
