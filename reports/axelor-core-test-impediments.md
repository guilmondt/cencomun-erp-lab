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
