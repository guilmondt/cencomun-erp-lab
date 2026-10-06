# Empaquetado de evidencia Core Axelor

Cambio de transporte y revisión; no modifica fixtures, oráculo, ejecución de
negocio, pins ni resultados esperados. CI `37453727869` del commit `5660bc7`
terminó con su formato original. No se canceló ni se repitió por este cambio.

El formato `ccm-isolated-repeat-index-v1` guarda rutas relativas, tamaños en bytes
y SHA256 de archivos completos para las fases `primary` y `repeat`, además del
recibo de restauración. Cada fase conserva sus 34 casos, gates económicos,
benchmark, build y smoke. Incluye los CSV, exports y demás archivos presentes;
no convierte archivos ausentes en evidencia. `phase-coverage.json` conserva la
cobertura original inmutable; el cierre puede actualizar `coverage.json` sin
invalidar el índice. El índice y la cobertura derivada no se auto-referencian.

El revisor carga **todos** los archivos referenciados, comprueba sus tamaños y
hashes y aplica las aserciones nativas anteriores sobre su contenido completo.
El campo `status` del índice no concede PASS. Faltantes impiden emitir aceptación;
una alteración o una aserción incumplida produce FAIL de revisión. Los criterios
conservan sus dependencias de grupos realmente ejecutados. La repetibilidad de
un FAIL funcional no transforma ese grupo en PASS.

```bash
python labs/axelor/core-test/evidence_index.py \
  --index RUTA_EVIDENCIA/isolated-repeat.json \
  --root RUTA_EVIDENCIA \
  --fixtures fixtures/ccm-core-v1
```

Para un resultado recuperado del formato anterior, `repackage_repeat.py` guarda
primero el agregado original fuera del árbol Git, verifica la copia y extrae
los dos conjuntos completos. Comprueba igualdad de los árboles de negocio antes
de reemplazar el agregado por el índice. Conserva tanto la causa original como
el nuevo veredicto de revisión. Un archivo por caso y fase evita duplicar todos
los casos dentro de otro JSON. Los resultados parciales y la matriz revisada
siguen separados de los originales de cada fase.

Si el ZIP no está disponible, el transporte futuro publica cada archivo original
una sola vez en fragmentos comprimidos con ruta, tamaño y SHA256. El extractor
reconstruye los bytes exactos; no acepta fragmentos incompletos o inconsistentes.
Cada fase publica sus archivos y su manifiesto antes del siguiente arranque, para conservar los casos independientes si la fase posterior no termina. Se suprimen las cápsulas de casos duplicadas durante ese modo CI. El log conserva
un índice pequeño, nunca el agregado de ambas fases. No se amplía la red.

La recuperación del CI actual usa su evidencia original, no vuelve a ejecutar
negocio. Cuando una fuente secundaria no contiene un archivo auxiliar del ZIP,
se documenta la ausencia; no se fabrica ni se declara descargado. El artefacto
remoto completo y el log original se conservan con su recibo de procedencia.

Validación local: 74 regresiones Python, incluida igualdad AST de las aserciones
de negocio con `5660bc7`, conservación de probes fallidos, hashes, rutas, fases
distintas y transporte individual. Estas pruebas no son aceptación full-stack.
La documentación oficial de GitHub limita archivos Git a
[100 MiB](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
Se comprobarán los tamaños reales antes de preparar el commit de evidencias.


Resultado real CI37453727869: índice22.428bytes, 92 archivos/60.654.190bytes
cargados y todos los hashes verificados. Igualdad completa con ambos árboles
originales; archivo individual máximo5.076.576bytes. Cápsula original íntegra
de65.662.508bytes en `/workspace/ccm-axelor-runtime/ci-evidence/37453727869-isolated-repeat-legacy.json`,
además del log completo original y artefacto remoto. Primaria26PASS/8FAIL,
réplica27PASS/7FAIL; repeticiónFAIL conservado, benchmarkFAIL. La revisión nueva
no ejecutó negocio. ZIP403 en sa8 una vez; ningún cambio de red.
