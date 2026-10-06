# Inicio del entorno guardado ccm-erp-lab-frappe

Repositorio `guilmondt/cencomun-erp-lab`, checkout existente
`/workspace/cencomun-erp-lab`, rama `lab/frappe-baseline`. La referencia exacta
propuesta es el último commit probado que registre el borrador ordinario.
No crear worktrees ni reinstalar automáticamente. Leer AGENTS.md,
docs/CODEX_CLOUD_SETUP.md, versions.lock y task 103 antes de trabajar.

Core conserva 34 grupos PASS; criterios 13 PASS/1 BLOCKED, seis PATCH UNRUN.
Oficiales completos: Frappe y ERPNext FAIL, separados de Core. Los diagnósticos
acotados posteriores tampoco son suites completas. Leer
reports/frappe-bounded-cause-diagnostics.md y reports/frappe-core-test.md.
No modificar oráculo/pins/upstream/HOME, main/producción/Axelor, red, secretos,
variables persistentes, acceso o permisos. PR #4 continúa borrador.

La restauración cloud **fcf690d** ya pasó en otra tarea, con recibo externo en
reports/evidence/frappe-cloud/restoration-fcf690d-external.json. No repetirla ni
confundir sitios nuevos en esta máquina con esa prueba. Guardar el borrador no
publica un nuevo snapshot; la restauración del commit nuevo no está acreditada.

## Inicio conservando los datos

1. Verificar HEAD contra el SHA exacto del borrador revisado; rama lab y
   checkout limpio. No hacer reset/checkout/restore para forzar coincidencia.
2. Confirmar runtime, sitio y archivos privados retenidos, mostrando únicamente
   presencia. Si faltan, detener recuperación de datos y documentar faltantes;
   no ejecutar install, new-site, migrate, seed, restore o runner completo.

   ```bash
   cd /workspace/cencomun-erp-lab
   git rev-parse HEAD
   git branch --show-current
   git status --porcelain
   test -f /workspace/.local/frappe-integral/core-site-created
   test -f /workspace/.local/frappe-integral/core-private.json
   test -f /workspace/.local/frappe-integral/bench/sites/ccm-core.test/site_config.json
   ```

3. Los procesos pueden no sobrevivir al snapshot. Arrancar servicios retenidos
   con los gestores idempotentes, sin reemplazar datos ni credenciales:

   ```bash
   source scripts/frappe-integral/env.sh
   export PATH="$CCM_FRAPPE_ROOT/core-tools/usr/bin:$PATH"
   python scripts/frappe-integral/services.py start
   python scripts/core-test/http_services.py start
   python scripts/frappe-integral/services.py status
   "$CCM_FRAPPE_ROOT/bench/env/bin/python" scripts/core-test/readiness.py
   ```

   MariaDB loopback 3307, Redis cache13000/queue11000, web8000, worker,
   Socket.IO local, Nginx8080, adapter8090, consumidor ficticio8091.
   Sitio Core `ccm-core.test`, base `ccm_core_lab`; web nativa8000 con
   `Host: ccm-core.test`. Proxy8080 permanece en `ccm-frappe.test`.

4. Readiness usa Reader y sus claves retenidas privadamente. Exige LAB activo,
   medición desactivada, P001 **USD50.00/stock5** para la compañía/almacén HTTP
   retenidos; coteja adaptador con API nativa. Es consulta autenticada, sin
   creación de pedidos/eventos. No imprimir headers, claves o archivos privados.
5. Si falla un servicio: revisar `services.py status` y log con
   scripts/core-test/log_tail.py; no matar procesos ajenos ni borrar sockets.
   Repetir únicamente inicio del servicio detenido y readiness cuando termine
   su arranque. Si hay 401/403 o diferencia de datos, conservar FAIL y comparar
   rol, compañía, almacén y Host; no regenerar credenciales o resembrar.

## Evaluaciones y límites

El arranque no ejecuta Core ni oficiales. No lanzar run.sh/suites completas
automáticamente. Una futura repetición requiere objetivo autorizado y conservar
sitios/intentos previos; Core run.sh reemplaza datos ficticios de su sitio LAB.
Las suites oficiales usan Bench separado, sitios oficiales vacíos y guard
offline. Antes de preparar fixtures o iniciar runner, comprobar procesos y lock;
no duplicar activos ni reiniciar web durante tests.

Frappe/ERPNext 16.36.1, SHAs 97a5dd93ca5883bcc9c4ef9834120c5cba397b67 y
fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba. Python3.14.0, Node24.19.0,
MariaDB11.8.6, Redis8.0.2, Bench5.29.0, Yarn1.22.22, Nginx1.26.3. Dependencias
upstream/caches/archivos históricos son runtime, no repositorios adicionales.
No modificar pins para resolver límites. Criterio13 BLOCKED/seis UNRUN.

El coordinador revisará repositorio/ref e instrucciones y realizará
Guardar/Publicar. Internet/dominios, install_script, secretos, variables,
privacidad y permisos se conservan. No se requieren nuevos valores ni accesos.
