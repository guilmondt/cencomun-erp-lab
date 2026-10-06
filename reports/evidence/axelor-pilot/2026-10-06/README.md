# Evidencia del piloto Axelor

Cada cohorte conserva su versión y sus resultados; consultar la matriz vigente
en [estado del piloto](../../../axelor-pilot-v1-status.md). `acceptance-v6` es la cohorte final; `acceptance-v5`
conserva las operaciones UI anteriores, lectura nativa posterior, snapshots de controles
negativos y restauración. `ci-37524117138` clasifica por separado el CI de
`2e33cca`: 32 PASS / 2 FAIL conocidos; no es la regresión del artefacto final.

El primer lote, `77da453`, tenía 63 tests Java y 93 Python PASS pero aún no
aceptación limpia por UI. Ese estado inicial se conserva aquí como contexto.

`diagnostic-v2` conserva hallazgos y pruebas de depuración: no es una aceptación
completa. La factura web experimental usó temporalmente tolerancia 0,01; ese
criterio fue descartado y vuelto a cero. La venta web posterior con comprobación
exacta sí pasó desde UI. El cierre guardó cero por colisión de campos: se conserva
como FAIL y no se modificó. El código publicado separa sus entradas temporales.

No incluye secretos, cookies, volcados de BD ni credenciales. Los nombres y
operaciones son ficticios. La evaluación histórica y sus dos FAIL son inmutables.


`core-final` contiene la regresión nativa de `753728b`/WAR `35efd7cc…`, con
32 PASS y los dos FAIL históricos. `core-final-attempt1` preserva el intento
anterior con un fallo adicional de orden del lector, corregido después.
Los archivos `.tar.gz` contienen todos los JSON originales; `archive-manifest.json`
permite verificar hash y tamaño de cada uno sin depender del resumen. Extraerlos
en directorios vacíos separados. Ambos archivos se abrieron y comprobaron tras
crearlos. `build-final` conserva logs y resultados XML del build final.

La cohorte final `acceptance-v6` incluye además `restored-runtime`: navegador
y lectura nativa de la DB restaurada. Fuente/artefacto/verificadores quedan
fijados en `execution.json` y `build-manifest.json`.
