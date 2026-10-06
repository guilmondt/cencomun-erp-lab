# Evidencia del piloto Axelor

Implementación `77da453`: 63 tests Java y 93 Python PASS. La aceptación limpia
por UI sigue pendiente en DB v3 al publicar este primer lote.

`diagnostic-v2` conserva hallazgos y pruebas de depuración: no es una aceptación
completa. La factura web experimental usó temporalmente tolerancia 0,01; ese
criterio fue descartado y vuelto a cero. La venta web posterior con comprobación
exacta sí pasó desde UI. El cierre guardó cero por colisión de campos: se conserva
como FAIL y no se modificó. El código publicado separa sus entradas temporales.

No incluye secretos, cookies, volcados de BD ni credenciales. Los nombres y
operaciones son ficticios. La evaluación histórica y sus dos FAIL son inmutables.
