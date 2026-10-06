# Última pasada completa de CI oficial

Autorizada desde `9cbfbbd5ccd99aaa0b90cabdc8447aea173fb25c`. No suma PASS de
reproducciones modulares. Los resultados completos anteriores se conservan.
Una pasada Frappe seguida de una ERPNext, un shard nativo por aplicación,
modo offline; criterio 13 BLOCKED y seis PATCH UNRUN.

## Preparación y estado del checkpoint inicial

- Original Cencomun: 49.823 archivos de env/apps/configuración/oráculo capturados
  por hash, fuentes originales limpias en sus SHAs fijados. Comparación posterior
  pendiente: [integridad previa](evidence/frappe-official/cencomun-final-integrity-before.json).
- Fuentes copiadas conservadas y recreadas en Frappe
  `97a5dd93ca5883bcc9c4ef9834120c5cba397b67`, ERPNext
  `fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba`, Payments
  `cca07d9f9392e2ea0e521c5975151db9e4b6c321`; tres checkouts limpios antes del runner.
- Sitio Frappe nuevo `ccm-upstream-frappe-final.test`, solo Frappe, hook oficial
  before_tests completado y mapa nativo verificado sin reparación. Worker del
  Bench oficial y SMTP ficticio local, sin relay. Cencomun no se instala aquí.
- Preparación inicial interrumpida antes de bootstrap: `set-config` interpretó
  una contraseña local con guion inicial como opción (exit 2). Credencial
  conservada; se usó el separador Click `--` y se completó el hook. Ningún test
  fue ejecutado en ese fallo. La inspección inicial acreditaba solo aislamiento,
  no preparación completa. [Registro saneado](evidence/frappe-official/frappe-final-preparation-interrupted.json).
- Discovery Frappe: 2.326 métodos, cero ejecutados; mismo código/pins.
  [Manifest por ID/categoría](evidence/frappe-official/frappe-discovery-final.json).
- 26 controles del harness PASS; guardrails PASS. No son tests oficiales.
- 48 archivos anteriores de intentos/observaciones registrados por hash para
  comprobar su conservación; sitios anteriores intactos. Ningún runner activo
  antes de iniciar. Primer y único completo nuevo Frappe CI iniciado; resultado
  todavía pendiente. ERPNext nuevo completo aún UNRUN.

## Runners completos autorizados

Los workflows fijados usan `run-parallel-tests`: Frappe
`.github/workflows/_base-server-tests.yml:112`, ERPNext
`.github/workflows/server-tests-mariadb.yml:192`. Un único shard incluye todos
sus módulos nativos, sin selecciones de módulos/métodos o exclusiones añadidas.
ERPNext usa bootstrap oficial y lightmode; Frappe no usa lightmode. Sus hooks,
fixtures, reinicio de usuario, decoradores y validaciones nativas se conservan.

```bash
set -e
cd /workspace/cencomun-erp-lab
source scripts/frappe-integral/env.sh
export PATH="$CCM_FRAPPE_ROOT/official-tools/bin:$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
"$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py frappe \
  --site ccm-upstream-frappe-final.test --ci-parallel --offline --observe
# Esperar y conservar el resultado Frappe antes de preparar/iniciar ERPNext.
"$CCM_FRAPPE_ROOT/official-bench/env/bin/python" scripts/official-tests/run.py erpnext \
  --site ccm-upstream-erpnext-final.test --ci-parallel --offline --observe
```

Cada completo reserva un intento exclusivo. Logs/XML/streams crudos y secretos
permanecen privados. Si falta resumen nativo, el contador es desconocido;
discovery/eventos observados no lo sustituyen. No excluir un caso que falle por
HOME/red/capacidad ausente, ni volver a ejecutar completos sin nueva corrección
demostrada. No modificar HOME, pins, upstream, permisos/aserciones, oráculo,
producción, main, Axelor ni repetir restauración cloud/Guardar/Publicar.
