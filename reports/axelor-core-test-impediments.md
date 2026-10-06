# Impedimentos del Core Test Axelor

Referencia fija: `fcf690dbc58b2b2dcf8d045c49976e3613e804cf`.
Rama exclusiva: `lab/axelor-baseline`. Registro iniciado 2026-10-06 UTC.

## B01 — descarga de artefactos, observada antes de ampliar cobertura

La descarga autenticada de la evidencia del run histórico 37228746936 mediante
`gh run download` resolvió al host
`productionresultssa19.blob.core.windows.net` y devolvió **Forbidden**.
Se capturó el error fuera del repositorio; su URL firmada no se publica.
El dominio 19 no estaba en el acceso restringido publicado, que conservaba
los dominios 11 y results-receiver. No se infiere un fallo del ERP de este error.

Impacto: no se puede inspeccionar el ZIP completo de ese run desde este
entorno. Sí funcionan Git HTTPS y la API de estado/anotaciones de GitHub.
La ejecución nueva y el desarrollo local continúan de forma independiente.

Resolución:

1. Se guardó un borrador que añade exclusivamente el host 19 observado,
   conservando los cuatro dominios personalizados previos y el preset
   `package_managers`. No se añaden comodines ni se cambia TLS.
2. Guardar y publicar ese borrador desde los ajustes del entorno. Guardarlo
   mediante la herramienta no modifica la política del proceso en ejecución.
3. Repetir `gh run download <run> --repo guilmondt/cencomun-erp-lab --dir <ruta>`;
   mantener stderr privado para no publicar firmas de descarga.
4. Verificar el SHA del código ejecutado, los archivos JSON/XML y sus hashes
   antes de incorporar evidencia al informe. Si aparece otro host bloqueado,
   registrar ese resultado concreto antes de añadirlo.

Verificación actual: persistencia del borrador confirmada con
`requires_publish=true`; publicación y descarga posterior todavía pendientes.

## Límite U13 — upgrade aplazado expresamente

El usuario reservó la actualización para una copia aislada y un objetivo
aprobado posterior. Criterio 13 BLOCKED; sus seis casos de patch UNRUN.
Esto no autoriza cambiar ningún pin ni actualizar este baseline.

1. Aprobar aparte el objetivo y crear la copia aislada en el trabajo futuro.
2. Restaurar los checkpoints de negocio/finanzas allí y ejecutar los seis casos.
3. Verificar identidades, invariantes, efectos, locks y diffs upstream.

No se necesita una nueva decisión del usuario para seguir implementando el
Core Test autorizado en el baseline actual.

## B02 — tipo de producto omitido en la carga Cencomun

Observado en el [run 37402239707](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37402239707),
commit `de96ab5d2844e45ce60e574ded46d848607afce5`, job 112071782736.
Primero CO00 (3.259 s), después TAX01-W (0.240 s). Ambos llegaron al servicio
nativo de creación de líneas de la entrada inicial y fallaron con:

```
java.lang.NullPointerException:
Cannot invoke "String.equals(Object)" because the return value of
"com.axelor.apps.base.db.Product.getProductTypeSelect()" is null
```

La carga Cencomun había omitido `productTypeSelect`. El dominio nativo declara
los tipos `storable`/`service` sin valor por defecto. No es evidencia de una
limitación económica de Axelor: es un defecto de la configuración del test.
El estado BLOCKED publicado por ese primer controlador se conserva como
registro histórico, pero el resultado parcial se interpreta como **FAIL de
preparación**; no se infiere PASS de ningún grupo ni criterio de ese agregador.

Impacto: no se validaron stock final, costo de ventas, impuestos o liquidación.
Los IDs de las fases fallidas no demuestran persistencia; el inspector en una
petición nueva es la fuente para comprobar el rollback. El baseline full-stack,
16 tests upstream, build offline con locks y reinicio siguieron ejecutándose.

Resolución:

1. Configurar `productTypeSelect=storable` y monedas USD en los productos
   ficticios, sin modificar sus SKU, precios, costos, flags u oráculo.
2. Conservar explícitamente las líneas en la colección nativa del StockMove,
   condición de pago inmediata y secuencias del chart sintético. Son
   correcciones de uso del API encontradas en la revisión del gate.
3. Recompilar, ejecutar los tests y repetir CI en una base desechable nueva.
4. Exigir cantidades y WAP nativos, facturas/pagos/asientos reconciliados y el
   oráculo completo en lecturas posteriores al commit. Incluso si ese camino
   económico pasa como admin, mantener aparte roles, estados y atomicidad.

Verificación de la solución: pendiente del siguiente CI. Registrado antes de
ampliar la implementación de otros bloques.

## B03 — interrupción del ejecutor, recuperado

El turno anterior no recibió resultados de `pwd`, `/bin/pwd` ni del patch
intentado; las celdas se terminaron sin conocer la causa. No se atribuye a
Axelor ni a GitHub. El entorno existente volvió a responder el 2026-10-06:
`pwd` devolvió `/workspace` y el checkout estaba limpio en `c2a1402`.
Los cambios anteriores están recuperados en esa rama remota. Se descargaron
los logs del run 37403617182 a
`/workspace/ccm-axelor-runtime/ci-evidence/37403617182.log` y sus anotaciones al
JSON contiguo, sin publicar ampliaciones de red.

## B04 — secuencias no visibles para la transacción aislada nativa

Observado en el [run 37403617182](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37403617182),
commit `c2a1402`, job 112076137415. CO00 (3.108 s) y después TAX01-W
(0.468 s) fallaron en `native-initial-stock-receipt`:

```
jakarta.persistence.NoResultException:
No result found for query [SELECT self FROM Sequence self WHERE self.id = :id]
```

El inspector en peticiones nuevas no encontró compañía, stock, ventas,
entregas, facturas ni asientos: no se conservaron efectos del `seed` fallido.
La revisión del código oficial AOS `0c70d561b19fc454eba9fdd41689258846626d75`
confirma que `SequenceIncrementExecutorImpl.incrementAndGet` usa un hilo
`TenantAware` separado. `doIncrement` consulta `Sequence` por ID con lock;
`SequenceReservationServiceImpl` documenta el incremento y reserva aislados.
Nuestro `seed` creaba las secuencias y consumía sus números sin haber
confirmado la misma transacción. Un flush no resuelve la visibilidad entre
transacciones. Es un defecto de preparación Cencomun; la hipótesis queda
pendiente de verificación mediante la repetición del gate.

Impacto: los resultados económicos siguen sin demostrar; 2 gates bloqueados
en ese run y 32 grupos sin ejecutar. No es una corrección upstream ni prueba
de incapacidad del ERP. Se registra antes de ampliar casos independientes.

Resolución y verificación:

1. Ejecutar catálogo/configuración/secuencias en una petición de preparación
   del fixture, con repositorios y transacción nativos.
2. Leer en otra petición las 12 secuencias y sus versiones persistidas antes
   de crear la entrada inicial; guardar esos IDs como evidencia.
3. Ejecutar la entrada inicial y asiento de apertura en su transacción propia
   del fixture. Conservar íntegra la transacción de venta, entrega, factura,
   costo de ventas y liquidación, con rollback ante cualquier excepción.
4. Repetir CO00 primero y TAX01-W después en una base desechable; exigir los
   resultados del oráculo por lectura nueva, no sólo ausencia de excepción.
5. Verificar aparte roles, estados y atomicidad; el administrador económico
   nunca marca completos los grupos de aceptación.

También se eliminó una segunda planificación de la entrega: el servicio
oficial `createStocksMovesFromSaleOrder` ya ejecuta `planWithNoSplit`.

## B05 — referencia de pins ausente en checkout superficial de CI

El mismo run terminó con exit 1 en `finalize.py`: `git show
e0190090fd137576ce273e350d7ce6686d66baf9:versions.lock` devolvió exit 128.
El checkout de Actions tenía profundidad 1; el objeto de comparación no
estaba disponible. Criterio 2 queda UNRUN en ese run; el build y tests
completados no sustituyen la atestación que falló.

1. Configurar `actions/checkout` con historial completo (`fetch-depth: 0`),
   sin cambiar su SHA ni conservar credenciales.
2. Comprobar el commit y blob base y su diff de pins antes del build costoso.
3. Conservar la comparación SHA256 real con ese blob inmutable en finalize.
4. Ejecutar regresión con un clon superficial: debe rechazar historia
   ausente, aceptar tras fetch explícito del SHA y detectar pins alterados.
5. Confirmar la atestación completa y diffs upstream cero en el nuevo CI.

Los dominios de artefactos 19 y 1 continúan en borrador pendiente; no se ha
publicado ese borrador ni alterado el acceso de red a raíz de estas correcciones.

## B06 — regresión de historial interrumpió el runner antes de los gates

Run 37405633383, commit `129614595f7af509b4fd9e83b1d97520179755ad`:
checkout con historial completo, preflight y verificación del blob base PASS.
El container terminó al ejecutar el nuevo test Python de evidencia, antes de
compilar o iniciar el ERP. La anotación no incluía `evidence-tests.log`; la
descarga del artefacto 11387685627 devolvió Forbidden en el host 4 de blobs.
La causa exacta interna de ese test no está disponible en la anotación; no se
atribuye sin evidencia a ownership, Git o Axelor. Los gates siguen UNRUN en
ese intento, no prueban ni refutan la corrección de Sequence.

1. Publicar el log de esa etapa al fallar y añadirlo a la selección de errores
   sanitizados, conservando el exit no cero.
2. Aislar la prueba de historial en un repositorio temporal sintético de dos
   commits, sin depender de rama, ownership o montaje del checkout anfitrión.
3. Volver a ejecutar las siete pruebas localmente y CI con ese cambio real.
4. Verificar aparte en CI el SHA base real y después repetir ambos gates.

No se publica ni añade el host 4 al borrador de red para recuperar este log.

## B07 — referencia de StockMove separada del contexto después de planificar

Run 37405935889, commit `9e9e835ce6d6cad40994d0b860c739e516d2008c`:
CO00 5.881 s, TAX01-W 0.684 s; ambos fallaron en la entrada inicial con
`AxelorException: Cannot realize a stock move that is not planned.`
Las doce secuencias y sus versiones ya estaban confirmadas en otra petición.
La segunda lectura muestra que `inStockMove` pasó de nextNum 1 a 2: el
incremento nativo funcionó. El error `NoResultException` no se repitió.
Compañía 1 quedó persistida; stock, ventas, entregas, facturas y asientos
permanecieron vacíos tras rollback de la entrada inicial.

La fuente fijada de `planStockMove` devuelve void y sustituye su referencia
mediante `JpaModelHelper.ensureManaged`, antes y después del procesamiento de
líneas. Nuestro caller reutilizaba el objeto anterior, que podía estar separado
del contexto y seguir con DRAFT. `realizeStockMove` exige PLANNED antes de
recargarlo. No se puede resolver estableciendo el estado manualmente.

1. Conservar el objeto devuelto por cada save del repositorio nativo.
2. Después de servicios que limpian el contexto, recuperar el modelo con
   `JPA.find(EntityHelper.getEntityClass(model), id)`, siguiendo exactamente
   la semántica de `JpaModelHelper.ensureManaged` de upstream.
3. Comprobar y exportar PLANNED real después de plan; llamar realize con ese
   modelo administrado. Aplicar la misma disciplina al resto del recorrido.
4. Repetir ambos gates, exigiendo stock y contabilización reales en nuevas
   peticiones. Mantener la misma transacción y rollback de los efectos.

El estado BLOCKED del run se conserva; la causa es un defecto del caller
Cencomun, no una necesidad de modificar upstream. La corrección de esta
referencia está pendiente de repetir. B04 (visibilidad de secuencias) queda
verificado para el incremento que antes fallaba, sin afirmar éxito económico.
B05 quedó verificado: finalize publicó el blob base real, SHA256 de pins
idénticos, 2+7+16 tests y diffs host/AOS cero. Sólo ese criterio 2 pasó.

## B08 — clientes con compañía antes de configurar su contabilidad

Run 37407761697, commit `d1b3930486b7be0480ae394a506e149e700f493c`:
CO00 4.030 s, TAX01-W 0.222 s; ambos fallaron durante preparación con
`Warning ! : You must configure account's information for the company Cencomun synthetic LAB`.
La traza real apunta a `PartnerAccountRepository.save` →
`AccountingSituationInitServiceImpl.createAccountingSituation` →
`AccountConfigService.getAccountConfig`. Los clientes recién asociados a
`companySet` requieren la configuración que nuestro caller creaba después.
Es un defecto del orden del fixture; ningún gate llegó a consumir stock.
La corrección de B07 no queda probada por este run. Los casos independientes
también se intentaron; no se anticipa éxito de sus pasos no alcanzados.

1. Crear chart, configuración contable, periodos, modos y secuencias después
   de los productos y antes de guardar los clientes con su compañía.
2. Conservar los repositorios nativos de Partner y su creación de situación
   contable; no retirar la compañía ni desactivar su validación.
3. Repetir compilación y tests, y después CI en una DB desechable nueva.
4. Exigir preparación confirmada, entrada nativa PLANNED/REALIZED y lecturas
   económicas posteriores al commit, incluidos impuestos por línea.

Impacto: todavía no hay gates económicos aprobados. Comparación incompleta.
Una descarga de logs de ese job fue rechazada en el host 14 de blobs; se
registró sin añadir ni publicar ese dominio ni otros cambios de red.

## B09 — proxies de moneda separados al contabilizar la entrada inicial

Run 37409531164, commit `ebe8d0b9be92b07b13b54cb33ed6c7911a9fbb2d`:
CO00 6.859 s y TAX01-W 0.604 s alcanzaron
`native-initial-stock-accounting`. La planificación nativa devolvió estado
PLANNED=2 para los StockMove 1/2; la realización avanzó hasta preparar la
apertura. Falló `MoveCreateServiceImpl.createMove` con
`LazyInitializationException: Could not initialize proxy [com.axelor.apps.base.db.Currency#148] - no session`.
Las lecturas nuevas conservaron compañía/configuración pero ningún stock o
efecto económico: el fixture realizó rollback completo.

La corrección de B07 permite ya pasar la guardia PLANNED. B08 permite crear
los clientes y preparar catálogo. La misma limpieza nativa de JPA también
separa compañía/cliente/almacén y sus relaciones lazy. Es un defecto de
referencias del caller, sin necesidad de modificar upstream.

1. Administrar de nuevo compañía, cliente y almacén después de realizar el
   stock, antes de crear la apertura, usando el helper conforme a upstream.
2. Aplicar esa misma disciplina antes de contabilizar venta y liquidación,
   conservando la transacción conjunta y las validaciones nativas.
3. Repetir compilación/tests y gates en una DB desechable.
4. Exigir cantidades, costos, impuestos por línea y pagos/asientos persistidos
   después de commit. Ningún ID transitorio ni estado PLANNED parcial es PASS.

## B10 — autenticación de los usuarios sintéticos respondió 401

En el mismo run, la preparación de producto devolvió IDs de tres perfiles,
operador 2, rol 3 y permiso 34. No sustituyen una lectura nueva persistida.
PROD01-04 falló al autenticar en 0.476 s y SEARCH en 0.017 s: HTTP 401.
No hay round trips de garantía ni búsquedas demostrados. La causa de 401
todavía no se identifica con ese mensaje; no se atribuye sin pruebas a la
contraseña, caché o permisos. El AuthService fijado trata hashes ya cifrados
de forma idempotente; su código no respalda asumir doble hashing.

1. Leer usuarios y perfiles desde una petición nueva autenticada como admin.
2. Registrar sólo presencia/IDs, estado activo, roles y resultado booleano
   del matcher nativo; no exponer contraseñas, hashes o cookies.
3. Conservar el cuerpo público de error HTTP cuando aporte la causa del 401.
4. Corregir el defecto observado y repetir login y CRUD/búsquedas con los
   mismos actores y permisos. No sustituirlos por administrador.

Impacto: ambos grupos siguen FAIL/incompletos, gates aún BLOCKED. Continúa
el fixture bancario independiente; la comparación permanece incompleta.

Evidencia adicional recuperada sin ampliar la red: el artefacto 11389525853
de ese run se descargó completo. `app-first.log` declara para ambos usuarios
`Authentication failed ...: User is disabled.` La fuente oficial fijada
`axelor-base/src/main/resources/domains/User.xml:49` redefine blocked con
default=true; mirar solamente el constructor de AOP no reflejaba el dominio
fusionado AOS. La preparación Cencomun omitía activar sus usuarios sintéticos.

1. El admin del fixture configura blocked=false sólo para ccm-operator y
   ccm-reader, mediante sus repositorios nativos. No cambia defaults upstream
   ni se dan roles administrativos a esos actores.
2. Una nueva petición verifica presencia persistida, AuthUtils.isActive,
   rol por AuthUtils.hasRole y matcher nativo booleano, sin publicar hashes.
3. Repetir login HTTP y las mismas escrituras/lecturas bajo cada actor; no
   considerar esa activación corregida hasta observarlo en el nuevo CI.

## B11–B14 — defectos observados en la repetición 37411893961

Commit `8e6cafd2c89899d3c9ea8216f6b8d7a6f4105773`, artefacto completo 11390001620
descargado sin cambios de red. La moneda separada ya no produjo error (B09).
La lectura nueva confirmó tres perfiles y ambos usuarios activos, con rol y
matcher nativo verdadero. Sus logins HTTP funcionaron (B10 verificado).
Los grupos siguen incompletos: 2 BLOCKED, 3 FAIL, 29 UNRUN.

### B11 — colección contable con borrado de huérfanos

CO00 6.822 s y TAX01-W 0.766 s: `HibernateException: A collection with orphan
deletion was no longer referenced by the owning entity instance:
com.axelor.apps.account.db.Move.moveLineList`, durante apertura. El servicio
nativo createMove ya guarda el Move; nuestro caller sustituía su colección
administrada por un ArrayList distinto. No queda stock ni contabilidad tras rollback.

1. Añadir líneas con addMoveLineListItem, preservando la colección nativa.
2. Aplicar lo mismo a apertura, costo y liquidación; no cambiar commits ni estados.
3. Repetir compilación y gates, exigiendo lectura económica después del commit.

### B12 — parámetros de permisos con tipos incompatibles

PROD falló tras login real: `Cannot compare left expression of type java.lang.Long
with right expression of type com.axelor.apps.base.db.Company`. El parámetro
de configuración entregaba el objeto Company cuando el filtro espera su ID.

1. Usar condiciones explícitas sobre company.id y parámetro __user__.activeCompany.id.
2. Mantener equivalentes los filtros de Partner.companySet y TrackingNumber,
   mediante joins/exists que comparen IDs. No eliminar el aislamiento por compañía.
3. Actualizar también permisos ya preparados en LAB, y repetir CRUD por operador
   y rechazos del lector a otra compañía. Nunca reemplazar el actor por admin.

### B13 — orden de argumentos de paginación AOP

SEARCH, lector real, rechazó otra compañía con 403. La consulta de P001 devolvió
total=1 pero items=[]: se usaba Query.fetch(offset,size). Bytecode fijado de AOP
8.2.3 demuestra que fetchQuery usa el primer argumento en setMaxResults y el
segundo en setFirstResult: la llamada correcta es fetch(size,offset).

1. Corregir el orden, conservando filtros, límites y búsqueda nativos.
2. Repetir las cuatro búsquedas y ambas páginas; exigir 3 productos únicos completos.
3. Mantener aparte las búsquedas de cliente/serial/factura pendientes; no inferir PASS.

### B14 — journal de anticipos sin cuentas autorizadas

BANK-BOOK-FIXTURE falló al confirmar el primer voucher:
`Designated account CCM-BANK ... is not allowed on the journal CCM-BOOK`.
MoveLineControlService exige validAccountSet o validAccountTypeSet; estaban
vacíos. Es configuración del fixture, no un motivo para saltar ese control.

1. Autorizar sólo BANK y AR en el journal dedicado del fixture de anticipos.
2. Configurar conjuntos concretos de cuentas para los journals originales
   según apertura/ventas/costo/cobros/liquidación, conservando el control nativo.
3. Repetir los cuatro vouchers/asientos y sus saldos/replay desde otra petición.

Estos impedimentos se registran antes de continuar otras ampliaciones. El
oráculo, datos compartidos y pins permanecen intactos.

## B15–B18 — repetición 37413918081

Commit 66199825dcc333e9001a05b3b94cc68e6d843d2c, CI FAILURE. B11/B12/B13/B14
dejaron de reproducirse: stock inicial REALIZED=3, 5/5/5 con costos 30/10/60
persistidos; CRUD por operador completo PASS; búsquedas/páginas de productos
correctas; journal bancario permitió confirmar sus recibos. Gates aún incompletos.

### B15 — cotización creada sin inicialización nativa

Ambos gates: `Can only finalize a drafted quotation`, en finalización. SaleOrder.xml
no tiene default para statusSelect; instanciar el modelo no lo inicia como draft.
SaleOrderCreateServiceImpl.createSaleOrder es el mecanismo nativo que lo prepara
(línea 198 del commit fijado), además de fechas/direcciones/configuración.

1. Usar ese factory oficial antes de agregar líneas; no escribir statusSelect.
2. Registrar su estado inicial y mantener sell como una transacción completa.
3. Repetir ambos gates y exigir lecturas nuevas de todos los efectos económicos.

### B16 — búsqueda nativa de cliente vacía

Reader real ejecutó correctamente siete pasos de productos/aislamiento/paginación;
la primera consulta de Partner devolvió []. El log no prueba si falló el scope,
la preparación del cliente o la forma de la consulta. No se elimina el permiso.

1. Exportar por admin los clientes preparados, nombre/teléfono y companySet.
2. Guardar la respuesta REST completa y la consulta antes de la aserción.
3. Repetir con lector; diagnosticar con esos datos y conservar resultado esperado C001.

### B17 — saldo firmado de crédito comparado con importe sin signo

Libro bancario falló al exigir +100 en MoveLine.amountRemaining: AOS exportó
-100 para el crédito AR. MoveLineToolServiceImpl, líneas 444–445 del pin, documenta
que los créditos pendientes tienen -(credit-amountPaid). El importe no aplicado
del voucher y el fixture siguen siendo positivos; no cambia el resultado económico.

1. Conservar el saldo firmado nativo en el export, sin abs silencioso.
2. Exigir crédito AR pendiente=-importe y voucher restante=importe, más débito
   BANK, asiento ACCOUNTED, ausencia de aplicaciones y replay sin duplicación.
3. Guardar exports antes de evaluar y añadir regresión que rechace el signo incorrecto.

### B18 — artefacto bloqueado por proxy, log recuperable

Artefacto 11390399358 subido correctamente. Dos intentos de descarga fallaron
`Forbidden` en productionresultssa17.blob.core.windows.net. No se añadió ni
publicó ese dominio. El log completo sí se descargó a
`/workspace/ccm-axelor-runtime/ci-evidence/37413918081.log`; los avisos JSON completos
se recuperan como fuente secundaria etiquetada. No se infiere lo ausente.

1. Conservar hash/log/resultados recuperados; no guardar URLs SAS temporales.
2. Continuar compilación y casos independientes por los canales ya disponibles.
3. La disponibilidad futura del ZIP permitiría verificar sus archivos/hashes;
   no ampliar red ni declarar ese ZIP descargado mientras siga bloqueado.

## B19 — FX/MONEY calculado sin pagos nativos

Revisión de paridad del commit 013f962: NativeFxService.convert consulta
CurrencyService y devuelve importes/rate IDs, pero no crea pagos. La referencia
fija fcf690dbc58b2b2dcf8d045c49976e3613e804cf, business.json y finance.py,
registra una factura USD por caso y cuatro Payment Entries: FX01 (40 VES),
FX02 (41 VES) y MONEY-ROUND (dos de 0.41 VES). Un PASS basado sólo en tasas
es inválido para el grupo completo, aunque los cálculos sean correctos.

1. Conservar conversiones y autorización como evidencia parcial; exigir cuatro
   pagos nativos, fechas, importes y asientos desde otra petición tras el commit.
2. Usar factura y InvoicePayment oficiales de AOS, su creación de términos,
   validación, asiento y conciliación; no construir pagos o saldos simulados.
3. Añadir regresión del agregador contra cálculos/tasas sin pagos. El CI en
   curso 37416107406 se conserva; su resultado FX antiguo se revisará con este
   contrato estricto. No cambiar fixtures, oráculo ni pins para obtener PASS.

Continuación independiente: cada FX01/FX02/MONEY-ROUND conserva su propia
transacción nativa de factura/pagos. Si una falla, leer después de su rollback,
guardar el error y cualquier efecto observado y probar las otras fechas.
El grupo seguirá FAIL ante cualquier fallo, con conversiones parciales separadas;
ningún subcaso recibe PASS por una respuesta del servicio sin lectura confirmada.

## B20–B22 — repetición 37416107406

Commit 013f962, CI FAILURE. BANK-BOOK y PROD completos PASS. FX sólo conversión
parcial PASS; el PASS completo antiguo se rechaza y queda UNRUN. Gates avanzan
con el factory oficial (draft=1), sin Sequence NoResult. Venta/entrega/factura
se revierten juntas al fallar la facturación, mientras la apertura del fixture permanece.

### B20 — dirección de facturación requerida

CO00 falla en ValidateState.process: `Warning ! : Invoicing address missing`.
Los clientes del fixture no tenían Address/PartnerAddress; no se debe desactivar
la validación. También afecta a las nuevas facturas FX.

1. Preparar direcciones sintéticas nativas con PartnerAddress de facturación,
   entrega/default, durante la preparación confirmada, sin alterar fixtures compartidos.
2. Mantener PartnerService/InvoiceGenerator como consumidores de esas direcciones.
3. Repetir gates/FX y exigir ID de dirección e invoice/accounted effects frescos.

### B21 — régimen fiscal sin configurar

TAX01-W: `No account found for Tax: TAX-LAB-10 (company: CCM-LAB-001)`.
Las cuatro cuentas fiscales ya estaban asignadas, pero Account.vatSystemSelect
era el default 0; TaxInvoiceLine resuelve ese 0, y getTaxAccount sólo admite
sistemas 1/2. Además faltaba Company.partner y su AccountingSituation fiscal,
necesarios para InvoiceVatLiabilityService. No es una ausencia del impuesto nativo.

1. Configurar el régimen de las cuentas LAB y el Partner interno de Company
   con AccountingSituation nativa de devengo/entrega, en preparación confirmada.
2. Conservar cálculo/resolución/validación fiscal oficiales y tasa exacta del fixture.
3. Repetir TAX01-W; verificar base 125, IVA 12.50 y asientos, sin escribir estados/saldos.

### B22 — cliente presente pero REST del lector vacío

La inspección fresca confirma C001, nombre/teléfono exactos y company_ids=[1].
REST de lector devuelve {status:0,offset:0} sin data. Preparación del cliente no
explica el fallo; sigue sin demostrarse si falla filtro de permiso o consulta/selector.

1. Conservar esa respuesta y scope, sin ampliar permisos.
2. Comparar la misma consulta REST como admin y el filtro real JpaSecurity del lector,
   ejecutando la consulta con ese filtro. Registrar compañía, parámetros y conteos.
3. Repetir nombre/teléfono/serial; sólo datos leídos por el lector nativo aprueban búsqueda.

Continuación independiente: un rechazo/fallo en nombre o teléfono no debe
impedir probar serial y factura. Conservar cada consulta/diagnóstico y su fallo,
continuar las restantes y mantener SEARCH completo FAIL mientras cualquier
subcaso falle. Un fallo del diagnóstico tampoco debe ocultar la respuesta REST
original. El CI ya activo se conserva; no se cuentan pruebas del runner como ERP.

El artefacto 11391813114 vuelve a estar bloqueado por Forbidden en
productionresultssa16.blob.core.windows.net; un intento, sin ampliar/publicar red.
Log completo recuperado en /workspace/ccm-axelor-runtime/ci-evidence/37416107406.log.

### B23 — revisión estática de preparación del pago inicial

El CI todavía no alcanzó el cobro del gate. En el código fijado,
InvoicePaymentMoveCreateServiceImpl.fillMove suma InvoiceTermPayment.companyPaidAmount;
el constructor simple de InvoicePayment usado por el gate no crea esos términos.
Sin preparación de términos, esa suma queda en cero. Esto es una omisión observada
del adaptador, no una corrección ya demostrada mediante un gate ejecutado.

1. Vincular el pago a la colección nativa de Invoice y ejecutar
   InvoiceTermPaymentService.createInvoicePaymentTerms antes de validar.
2. Mantener toda la venta/liquidación en la misma transacción y no asignar montos
   de términos, saldos ni estados manualmente.
3. Repetir gates; exigir cuatro asientos contabilizados, pagos validados por el
   total bruto y saldo cero desde la petición de inspección posterior.

### B24 — reloj determinista y fechas de FX

Revisión del código fijado: VentilateState.setDate rechaza invoiceDate posterior
al reloj AppAccount. El gate prepara el reloj LAB en 2026-10-01; FX02/MONEY
usan 2026-10-02/03. El recorrido nuevo aún no se ejecutó en ERP; esta frontera
estática se corrige como preparación de entorno, sin desactivar el control.

1. Después de los gates, avanzar el reloj AppBase LAB al máximo día de fx.json,
   2026-10-03, durante la preparación FX confirmada.
2. Conservar fechas originales de las facturas/pagos y selección de tasa por
   paymentDate; no cambiar fixture/oráculo ni permitir facturas futuras.
3. Exportar el día preparado y repetir FX con fechas/tasas/asientos leídos
   después del commit. No considerar la corrección verificada hasta esa repetición.

## B25 — preparación revertida por plantilla nativa de dirección incompleta

CI 37418693317, commit fc684630: CO00 (4.941 s) y TAX01-W (0.434 s)
fallan al preparar catálogo con `java.lang.NullPointerException: Cannot invoke
"String.toCharArray()" because "input" is null`. AddressBaseRepository.save
ejecuta AddressTemplateService.setFormattedFullName; el servicio fijado renderiza
addressL2Str–addressL6Str además de templateStr. El fixture sólo completaba
templateStr, dejando las cinco plantillas de línea en null. La transacción se
revierte: faltan catálogo/usuarios para PROD, SEARCH y BANK, y FX rechaza
`Catalog must commit first`. No se alcanzó ningún pago o gate económico.

1. Completar las cinco plantillas nativas de línea con referencias a los campos
   de Address y el formato completo, durante la preparación confirmada.
2. Conservar el repositorio/renderer nativo y todas las validaciones; no escribir
   formattedFullName para evitar el callback ni separar los efectos de venta.
3. Repetir CO00 y TAX01-W antes de independientes; comprobar direcciones
   confirmadas y después los cuatro pagos/asientos/liquidaciones FX.

El ZIP 11393176285 devolvió Forbidden en productionresultssa18.blob.core.windows.net
en un único intento. Log: /workspace/ccm-axelor-runtime/ci-evidence/37418693317.log.
CI reporta 6 FAIL / 28 UNRUN; la evidencia secundaria íntegra sólo demuestra
5 FAIL / 29 UNRUN porque el aviso FX con dos stacks excede el límite de log.
Los PASS históricos de CI9 se mantienen aparte, nunca como éxitos de CI10.

1. Guardar recibo, hash del log y avisos íntegros recuperados, sin inferir el aviso FX.
2. Emitir un resumen FX acotado conservando el error y la ruta al JSON completo;
   añadir regresión para que un error grande no suprima la fila de cobertura.
3. Verificar extracción con JSON completo y conteos reproducibles en el siguiente CI,
   sin ampliar/publicar dominios ni reconstruir archivos truncados como originales.

Regresión adicional local: dos tests llaman al AddressTemplateServiceImpl oficial
con un contenedor Guice mínimo, sin DB; la plantilla preparada renderiza todas las
líneas y dejar addressL2Str=null reproduce la AxelorException causada por NPE.
Se ejecutaron con clases nativas compiladas del host fijado, usando un init script
externo para el classpath. El intento full-native del test encontró primero npm
ENOENT en /home/agent/.npm; no se amplió red ni se omitieron checks del CI.
Este resultado valida el callback, no confirma persistencia ni efectos económicos.
El CI incorpora los dos tests al perfil full-native y a su replay con locks.

## B26 — colección de campos requeridos de AddressTemplate no preparada

CI 37420752108, f058d213: el renderer supera B25, pero AddressBaseRepository
ejecuta después checkRequiredAddressFields y falla con `Cannot invoke
"java.util.List.iterator()" because the return value of
"com.axelor.apps.base.db.AddressTemplate.getAddressTemplateLineList()" is null`.
CO00 5.994 s / TAX01-W 0.523 s; preparación revertida. PROD/SEARCH/BANK/FX
se intentan y fallan por catálogo/usuario sin confirmar; ningún pago ejecutado.
El aviso FX ahora es JSON íntegro: matriz 0 PASS / 6 FAIL / 0 BLOCKED / 28 UNRUN.
ZIP 11393546981 Forbidden en el mismo host sa18; un intento, sin ampliar red.

Fuente fija revisada: AddressBaseRepository.save llama a setFormattedFullName,
AddressService.computeFullName y checkRequiredAddressFields antes de super.save.
AddressTemplateLine no tiene fieldName: usa FK metaField. El importador oficial
axelor-base/data-init/input-config.xml resuelve nombre + modelo Address; su
base_addressTemplateLine.csv DEFAULT tiene floor/postBox opcionales y
streetName/city/zip requeridos. MetaModelService.process y ModelLoader inicializan
los metadatos; la acción UI de Country selecciona el default de AppBase, pero
no sustituye su preparación explícita al crear por repositorio.

1. Resolver MetaField persistidos de Address con el fullName oficial; fallar antes
   de guardar si falta alguno. Crear cinco hijos con FK real y helper nativo
   parent/children; conservar las tres obligatoriedades oficiales.
2. Usar streetName, City y zip nativos para la dirección LAB. Completar las cinco
   plantillas soportadas; no introducir nombres calculados manualmente ni listas
   vacías para eludir el control. Renderer, computeFullName, validaciones y save
   permanecen upstream intactos.
3. Ejecutar las ocho regresiones de callbacks: formato/nombre y relaciones,
   plantilla null, colección null, MetaField null, metadatos incompletos y rechazo
   separado de cada campo obligatorio. Ejecutadas localmente: 8 PASS / 0 fallos,
   errores o skips, 0.696 s. No prueban persistencia.
4. Ejecutar address-preflight.py en el ERP real autenticado antes de los gates y
   del reinicio: guardado por AddressBaseRepository, IDs de hijos/metadatos,
   lectura en petición posterior al commit, replay y nueva lectura idéntica.
   Los callbacks se ordenan antes de WAR/launcher en la invocación Gradle; sus
   dependencias upstream pueden requerir compilación/frontend. El preflight del
   ERP requiere WAR y arranque. Aceptación CI aún pendiente en esta corrección.
5. Sólo después repetir CO00 y TAX01-W en ese orden, más casos independientes.
   Exigir direcciones/configuración confirmadas y cuatro pagos/asientos y
   conciliaciones FX mediante nuevas lecturas; no trasladar PASS históricos.

La separación se limita a preparar el fixture de dirección. Venta, entrega,
factura, liquidación y sus rechazos conservan sus transacciones y validaciones.
Evidencia local: reports/evidence/axelor-core/address-preflight-local-20261006.

## B27 — JPA local sin contexto HTTP completo, diagnóstico detenido

Docker respondió y la imagen PostgreSQL 16.15 fijada por digest arrancó, aceptó
conexión loopback y devolvió 16.15 (Debian 16.15-1.pgdg12+2). Esto no prueba un
runner full-stack fiable. El test de guardado nunca llegó a su cuerpo:
primero se observó el User de AOP sin partner; después faltó el binding nativo de
HibernateListenerConfigurator. Se corrigieron el classpath externo y el módulo
de test usando el patrón oficial BaseModule/AuthModule/AppModule, sin fuentes,
pins ni audit listeners modificados. El último diagnóstico (19.393 s) falla al
crear injector: `[Guice/ScopeNotFound]: No scope is bound to RequestScoped`,
InvoiceVisibilityServiceImpl / AccountConfigService, porque AppModule descubre
los módulos AOS y requiere scope HTTP. JUnit informa un initializationError,
1 fallo, 0 errores/skips; guardado y lectura posterior al commit UNRUN.

1. No sustituir RequestScoped por singleton ni desactivar validaciones/auditoría.
2. Usar el preflight enfocado dentro del ERP real en CI; requiere contexto HTTP
   nativo, sin modificar los permisos de Cloud ni ampliar red.
3. Verificar address-preflight.json PASS, IDs/MetaField/requeridos y replay desde
   lecturas posteriores al commit antes de interpretar nuevos gates económicos.

Contenedores propios eliminados con sus volúmenes; configuración privada temporal
eliminada, credenciales sintéticas efímeras sin persistencia. No se modificaron
permisos del sistema ni red. El diagnóstico se conserva fuera del checkout en
/workspace/ccm-axelor-runtime/address-preflight: logs sanitizados, XML, fuente de
test y persistence.xml; hashes y extracto exacto en diagnostic.json del informe
local. No se añade un test JPA fallido a las suites de aceptación del repositorio.
## B28 — CI12: PDF automático bloquea la contabilización confirmada

CI `37425320931`, commit `8b0a534b8c835aa01aadb753b65be7f4e4c3fbd6`:
el preflight de AddressBaseRepository PASS (1.484 s) confirma cinco líneas
nativas, tres campos requeridos, nombres derivados y replay idéntico después
del commit. CO00/TAX01-W llegan a InvoiceService.validateAndVentilate, pero
`getInvoicePrintTemplate` lanza `The configuration to print this model has not
been found`. Los tres intentos de pagos FX fallan por la misma dependencia.
La transacción revierte: no hay factura, entrega, GL de venta ni pagos
confirmados. Sólo entrada inicial/valoración y asiento de apertura persisten.

1. Configurar únicamente el runtime `CCM_CORE_LAB=1`, por repositorio nativo,
   con AppInvoice.autoGenerateInvoicePrintingFileOnSaleInvoice=false, autorizado
   expresamente. Rechazar una configuración con isVentilationSkipped=true.
2. Conservar validate/ventilate íntegros. El upstream fijado contabiliza y guarda
   antes de su rama opcional PDF; no crear PrintingTemplate ni importar demos.
3. Leer la configuración efectiva y la persistida después del commit; exigir
   flags false e IDs reales. Repetir gates y pagos con asientos status=3,
   importes/oráculo intactos. PDF automático queda fuera del alcance probado.

Corrección local implementada; dos tests del AppInvoice nativo PASS y 24
regresiones Python PASS rechazan flags incorrectos/ausentes. Repetición del
ERP pendiente; no cuenta como gate PASS.

## B29 — CI12: placeholder de Permission.condition se renumera dos veces

SEARCH con lector: nombre, teléfono y serial fallan. El diagnóstico nativo
devuelve `org.hibernate.query.SemanticException: Cannot compare left expression
of type 'java.lang.String' with right expression of type 'java.lang.Long'`.
El bytecode fijado AOP 8.2.3 confirma que Filter.build sustituye cada carácter
`?`: una condición `?1` pasa a `?11`. Los permisos oficiales AOS usan `?`.
Scope de compañía y conditionParams deben conservarse exactamente.

1. Cambiar exclusivamente los placeholders de Permission.condition a `?`.
   No alterar filtros directos Query que admiten `?1`, ni grants de roles.
2. Añadir regresión que ejecute JPQLFilter + Filter.equals + Filter.build
   oficiales y compruebe texto y orden/tipos de parámetros; conservar un
   test de Query directo y una reproducción negativa del placeholder antiguo.
3. Repetir búsquedas autenticadas por lector y denegación de compañía ajena
   en CI. Un test de composición sin DB no aprueba por sí solo SEARCH completo.

Corrección local implementada: cinco tests de composición nativa PASS,
incluida la reproducción de la consulta final defectuosa: compañía y nombre
reutilizan ?1 mientras el primer parámetro sigue siendo Long. Se conservan
exactamente scope, conditionParams y permisos. Repetición del ERP pendiente.
CI12 conserva PROD/BANK
PASS ejecutados, SEARCH/FX FAIL, gates BLOCKED y 28 grupos UNRUN; no se arrastran
resultados de commits anteriores. ZIP: un intento, proxy Forbidden en
productionresultssa14.blob.core.windows.net; se conservan avisos completos del
log como evidencia secundaria, sin cambios de red ni publicación.
## B30 — CI13: inspección incompleta del vínculo nativo venta/factura

CI37429209635, commit27bdbd840f733eb3355658d3016b87edb4f3826d, FAILURE:
AppInvoice efectivo/persistido id1 confirma PDF automático false y
isVentilationSkipped=false. Dirección, PROD/BANK y cuatro pagos FX PASS;
nombre/teléfono/serial por lector y denegación ajena403 ejecutados.
CO00/TAX01-W llegan al final del flujo, pero la aserción encuentra invoices=[]
al filtrar exclusivamente Invoice.saleOrder. SEARCH encuentra INV-CCM-001,
pero su cabecera saleOrder es null. AOS fijado proporciona getInvoices(SaleOrder)
con fallback explícito por InvoiceLine.saleOrderLine; el overload corto usado
no asigna la cabecera como el wizard. No cambiar datos ni resultados esperados
para acomodar el inspector.

Stock confirmado3/4/5, WAP30/10/60, COGS70 contabilizado; liquidación nativa
CO00 move5 (banco67/comisión8/AR75) y TAX01-W move10 se leen. Faltan la factura,
su asiento y pago directo en el export del gate: éxito económico completo aún
FAIL, aunque el servicio no revirtió. FX sí tiene sus cuatro InvoicePayment
ids5/6/7/8, tres facturas3/4/5 y siete asientos15–21 status3 con conciliación
confirmada y saldos0 después del commit. Se conservan parciales separados.

1. Ejecutar el overload completo de generateInvoice con la constante oficial
   SaleOrderRepository.INVOICE_ALL, la validación de facturabilidad del wizard,
   amount=0/isPercent=false y selecciones vacías (no usadas en INVOICE_ALL).
   AOS asigna y guarda la cabecera; no fabricar enlaces ni duplicar facturas.
   Conservar la transacción económica de sell y todos los servicios posteriores.
2. Conservar getInvoices(SaleOrder) y exportar además cabecera, compañía y FK
   InvoiceLine.invoice/InvoiceLine.saleOrderLine/SaleOrderLine.saleOrder.
   Exigir que ambas líneas pertenezcan a la factura y misma venta/compañía.
   Leer el vínculo bajo el scope Invoice existente del lector y comprobar 403
   ajeno. La referencia externa sólo selecciona la factura, no prueba el vínculo.
3. Añadir regresión del comprobador: rechazar factura sin vínculo, ID equivocado
   o compañía ajena. Repetir ERP/lecturas/oráculo; no sustituir FAIL por PASS
   hasta demostrar facturas, todos los GL y saldos nativos completos.

Matriz actual3PASS/3FAIL/28UNRUN; 14 criterios1PASS/6FAIL/6UNRUN/1BLOCKED.
ZIP11396837860: un intento Forbidden productionresultssa12.blob.core.windows.net;
se conservan logs estructurados, sin ampliar/publicar red. Corrección compilada
localmente y regresiones del inspector ejecutadas; aceptación ERP pendiente.

Verificación de B30: CI37432900300 (842a4dadcd74470dc6041d67d59bdfaf28803410)
confirma INVOICE_ALL, cabecera y ambas FK de líneas, misma venta/factura/
compañía. Lecturas nuevas después del commit revalidan oráculo, stock3/4/5,
valor430, COGS70, ingresos125, IVA0/12.50, anticipos50/55, banco67/70.25,
comisiones8/11.55, envío0/0.70 y AR0; cuatro GL por gate ACCOUNTED.
CO00 gate PASS15.960s, TAX01-W gate PASS8.563s; SEARCH completo PASS0.464s
con lector real y403 compañía ajena en búsqueda y lectura FK. Revalidación
independiente sobre los registros recuperados, usando comprobador de ese SHA,
también PASS. Este bloqueo está resuelto para el recorrido administrador;
no aprueba los grupos CO00/TAX completos ni roles/estados/atomicidad pendientes.
Matriz4PASS/30UNRUN; criterios1PASS/12UNRUN/1BLOCKED. CI global FAILURE por
cobertura pendiente, no por fallo de estos gates. ZIP bloqueado sa7, un intento;
no se amplía/publica red. El siguiente CI añade export de compañía de GL,
propiedad de líneas contables y fixture independiente; aún no aceptados.

## B31 — cancelación de SaleOrder confirmado antes de entrega

Inspección del AOS fijado 0c70d561b19fc454eba9fdd41689258846626d75:
SaleOrderWorkflowServiceImpl.cancelSaleOrder admite únicamente
STATUS_DRAFT_QUOTATION y STATUS_FINALIZED_QUOTATION. APPROVED en el contrato
congelado exige un pedido nativo confirmado; el override SupplyChain delega
al mismo guard. Esto afecta los tres subcasos de
STATE-CANCEL-BEFORE-HANDOVER (STORE APPROVED, WEB APPROVED/PREPARING).
La inspección de fuente no demuestra un fallo ejecutado ni una corrección.

1. Ejecutar el servicio oficial sobre cada pedido confirmado y conservar su
   error, estado y snapshots posteriores al rollback. Mantener CANCELLED como
   resultado esperado; no degradar statusSelect, clonar pedidos ni omitir guards.
2. Buscar una operación pública soportada que cancele el pedido confirmado
   conservando documentos, auditoría y atomicidad; si no existe, registrar la
   incompatibilidad del baseline y su impacto sin cambiar upstream ni pins.
3. Verificar cualquier solución con los tres subcasos, replay, actor real,
   stock5/5/5 y ausencia de entrega/factura/pagos/eventos de éxito nuevos.
   Continuar los estados, roles, rechazos y grupos independientes.

## CI15 — export nativo del fixture y scope contable

CI37435418318 de bd1f898b25af0ec90fcbe6ab7b2b27de0b87f913 completado:
5PASS/29UNRUN, criterios1PASS/12UNRUN/1BLOCKED. Los gates administrador CO00
10.872s y TAX01-W5.431s vuelven a PASS, separados de los grupos completos.
FIXTURE-HASH-NATIVE-EXPORT PASS exige bytes del JAR y registros nativos,
productos/clientes/monedas y nueve metadatos Role; no aprueba permisos funcionales.
Los asientos verifican compañía, cuentas y pertenencia de cada línea.
ZIP bloqueado productionresultssa4.blob.core.windows.net en un único intento;
logs estructurados conservados, sin ampliación ni publicación de red.

## Revisión causal posterior a 80f94067 (CI16 no duplicado)

STATE-UNKNOWN-ATOMIC necesitaba distinguir CRUD prohibido de enum inválido.
El CRUD válido REVIEWED y UNKNOWN-LAB se prueban como guardas, sin contar esos
rechazos como validación del enum. Un probe LAB separado usa Mapper.set nativo,
con control REVIEWED guardado, flush y lectura Hibernate, y UNKNOWN-LAB debe
fallar en ValueEnum.of con tipo/valor/cause frame específicos. Ambos probes
siempre revierten y se comparan snapshots económicos posteriores al rollback.
VAL01-04 exige un recibo nativo válido a coste30, mismo fixture/qty, realizado
y leído, junto con la tentativa -0.01. Un AxelorException de secuencia,
dirección u otra configuración no aprueba coste negativo: se requieren mensaje
específico y frame de validación stock, más el control válido. Si el ERP acepta
-0.01, el rollback de limpieza es FAIL funcional, nunca rechazo PASS.

1. Ejecutar controles/probes agrupados en la próxima ejecución de fuente,
   después del CI16 activo; no cancelar ni duplicar el job.
2. Revalidar también evidencia CI16 con el agregador reforzado, conservando
   resultado original aparte. Falta de controles causales significa cobertura
   UNRUN/incompleta; no transferir un PASS del comprobador anterior.
3. Registrar como FAIL funcional una cancelación ejecutada cuyo servicio
   rehúsa CANCELLED exigido, con error y los tres intentos. Un límite funcional
   del baseline no es un bloqueo de transporte/entorno. Mantener oráculo y guards.

## CI16 — hallazgos funcionales y pérdida diagnóstica del intento de entrega

CI37440203758/80f94067 ejecutó tres cancelaciones confirmadas y el coste -0.01.
Cancelación422 con SaleOrderWorkflowService y mensaje “Vous pouvez seulement
annuler un devis brouillon ou finalisé.”; coste negativo realizado y revertido
por limpieza. Ambos son FAIL funcionales, no bloqueos de entorno. Matriz revisada
9PASS/6FAIL/19UNRUN. UNKNOWN del run sólo probó CoreWriteScope, no ValueEnum.
Cuatro ciclos abortaron al comprobar delivery-rollback; faltó conservar el
intento antes del assert, por lo que el run no demuestra su causa nativa.

1. Guardar intento completo antes de aserciones, incluido snapshot después del
   rollback, y mensajes específicos; regresión falla si vuelve a perderse.
2. Repetir los cuatro ciclos en un único CI con probes causales agrupados,
   conservar servicio/efectos nativos y expectativas503/rollback intactas.
3. Diagnosticar sólo la respuesta real y verificar cualquier corrección con
   entrega, factura, COGS, liquidación, roles y rechazos. Continuar finanzas
   independientes mientras corre esa validación, sin otro CI simultáneo.

## Preparación financiera nativa y conservación de probes fallidos

La ampliación propia declara bank-payment del mismo checkout fijado; el intento
offline local no tenía jaxb-xjc3.0.1 en caché. Se resolvió mediante repositorios
existentes con TLS/pins, sin añadir/publicar dominios. Compilación nativa, locks
externos y replay offline estricto pasan; no prueban finanzas en el ERP.
Se separan preparación PURCHASE/CASH/BANK y confirmación de secuencias antes del
negocio; un fallo de configuración de una familia conserva su error y permite
continuar las otras. No se separa la transacción económica.

1. Confirmar el fixture específico mediante petición separada, ejecutar compras,
   caja y banco con actores reales y leer sólo después de commit/rollback en CI.
2. Adjuntar siempre el probe/control válido/intento inválido y snapshots antes
   de cualquier aserción. Regresiones locales fuerzan ambos probes a fallar y
   demuestran que se retienen respuesta y lecturas; no son validación ERP.
3. Verificar aprobación nativa/FX por fecha, ocho movimientos caja ACCOUNTED y
   factura125 pendiente excluida; statement/reconciliation nativos, signo-10,
   clasificaciones por recibos reales, replay/hash y 1000 filas concurrentes.
   Mantener todos UNRUN hasta prueba completa y revisar agregación independiente.

## B32 — orden temporal del fixture contaminó la guarda cronológica nativa

CI37442873626/37f9d28 conservó el intento delivery-rollback de los cuatro ciclos:
actor ccm-operator, esperado503/real422, VentilateState.checkInvoiceDate267 y
“La date de facture ou d'avoir ne peut être antérieure à la date de la dernière
facture ventilée : 2026-10-02”. Los snapshots posteriores verifican rollback de
stock/documentos/GL/keys/eventos. FX había contabilizado2Oct antes del ciclo1Oct.
Esto es una interferencia del harness/fixture, no prueba de un fallo de atomicidad
nativa ni razón para desactivar la guarda. UNKNOWN causal completo PASS del run;
VAL/cancelación siguen FAIL funcionales. Matriz10PASS/6FAIL/18UNRUN.

1. Preparar y confirmar las tasas/config FX antes de fixtures VES, sin crear
   facturas; ordenar todos los ciclos y pending de caja1Oct antes de pagos FX2/3Oct.
2. Conservar fechas/expectativas; no configurar ignoreInvoiceDate ni editar
   secuencias/status nativos para superar el guard. Regresión protege el orden.
3. Repetir cuatro ciclos completos, verificando503 real y snapshots de rollback,
   entrega/factura/COGS/liquidación nativos, denegaciones, replay y oráculo.
   Agrupar esa validación con seis grupos financieros; aún no verificada en ERP.
