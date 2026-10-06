# Revisión reproducible del CI37479552848

Commit ejecutado: `a2f462f67526af94409bd050bf277d78f4782387`.
Los103 archivos originales de ambas fases conservan bytes y SHA256 del índice.
El ZIP no pudo descargarse: un intento, HTTP403, dominio sa5 no añadido.
El digest oficial del ZIP no sustituye la verificación de los archivos recuperados.

Desde la raíz del checkout, cargar TODOS los archivos y aplicar las aserciones:

```sh
python3 labs/axelor/core-test/evidence_index.py --index reports/evidence/axelor-core/runs/37479552848/isolated-repeat.json --root reports/evidence/axelor-core/runs/37479552848 --fixtures fixtures/ccm-core-v1
```

Para reproducir también el recibo detallado, extraer TODOS los `.py` de
`labs/axelor/core-test` mediante `git show` del SHA ejecutado a un directorio
externo (sin cambiar de rama); escribir `lab-commit` con ese SHA y pasar ese
directorio al revisor archivado:

```sh
python3 reports/evidence/axelor-core/runs/37479552848/post-run-review.py /tmp/ccm-ci24-frozen-validator
```

El revisor vuelve a cargar los103 originales, aplica las mismas aserciones,
comprueba ambas atestaciones contra el SHA y exige42entregas/reinicio/replay
en cada fase. Nunca aprueba desde el índice. Los recibos derivados no duplican
árboles de casos. La repetición PASS conserva los dos FAIL funcionales.
Los67JUnit proceden de la atestación que lee XML reales en CI; los XML y logs
auxiliares del ZIP no fueron descargados. Las93regresiones Python son locales;
el mismo comando completó en CI, sin conteo del log de CI recuperado.
