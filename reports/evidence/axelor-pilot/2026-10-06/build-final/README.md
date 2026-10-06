# Build final y regresión de compilación

Fuente `753728b3859ec0077c1294ae48b330edc320f6e3`; WAR y versión en
`final-build-manifest.json`. 64 pruebas del módulo y 16 del test upstream
fijado PASS, 93 Python Core y 2 Python del guardado de evidencia PASS.

El intento upstream offline falló porque faltaban tres dependencias fijadas
en caché. Se conserva su log. El siguiente intento por repositorios configurados
resolvió esas mismas versiones y pasó; no se actualizaron pins ni locks.
No confundir ese error de preparación con un test funcional fallido.
