# Evidencia del piloto Axelor

Cada cohorte conserva su versión y sus resultados; consultar la matriz vigente
en [estado del piloto](../../../axelor-pilot-v1-status.md). `acceptance-v5`
contiene las operaciones UI, lectura nativa posterior, snapshots de controles
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
