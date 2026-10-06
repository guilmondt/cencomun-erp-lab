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
