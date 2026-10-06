# ExecPlan — 16 resultados acotados desde baad8f9

Autorizado el 2026-10-06. Solo lab/frappe-baseline, PR #4 borrador.
La publicación baad8f9 y restauración externa fcf690d ya están acreditadas por
el coordinador: no repetirlas. Ninguna suite completa nueva.

1. Comprobar acceso al ejecutor y ausencia de runners; conservar antes de
   continuar logs/evidencias/configuraciones retenidas y hashes originales.
   Registrar los límites de identidad de instancia; arrancar solo servicios
   retenidos con scripts idempotentes, sin reconstruir sitios o credenciales.
2. Instrumentar de forma saneada contexto request, configuración/imports,
   coincidencia de credenciales retenidas, respuesta/motivo nativo de login y
   parámetros de redirección OAuth solo por nombres/presencia. Nunca tokens,
   cookies, valores de credenciales ni query completa. Guard offline intacto.
3. Reproducciones representativas en sitios oficiales aislados y procesos
   limpios con preparación CI nativa: Client (dos casos), FrappeClient (un login
   representativo), Performance (su login), OAuth (implicit token). Comparar
   con la secuencia retenida y precedentes pertinentes, sin repetir los nueve
   módulos sin hipótesis. Capturar quién crea/destruye request y primer fallo.
4. Corregir solo un defecto de preparación/harness propio demostrado y repetir
   módulos afectados. Sin request añadido por caso/reset de password/tasa nueva,
   cambios upstream/aserciones/pins/red/HOME/acceso/políticas ni oráculo.
   UNKNOWN no es límite inevitable. Si la corrección exige algo no autorizado,
   conservar FAIL/ERROR y la condición precisa, y continuar líneas independientes.
5. Conservar todo intento/counter/discovery/error de fixture y causalidad.
   Completos anteriores FAIL separados de diagnósticos acotados, criterio13
   BLOCKED/seis PATCH UNRUN. Hashes Cencomun y consulta autenticada al cerrar;
   repetir Core solo si un cambio afectó su runtime.
6. Ejecutar controles del guard/harness y guardrails. Publicar código/docs/
   evidencia saneada solo lab, PR #4 borrador. Si hay commit nuevo probado,
   preparar únicamente repositorio/ref/start_skill del borrador; conservar
   configuración restante. Guardar/Publicar a cargo del coordinador.

## Progreso

- Acceso a checkout baad8f9 limpio y 81 logs de intentos retenidos confirmado.
  Cero runners; servicios retenidos detenidos. La continuidad del filesystem
  no acredita por sí sola la misma instancia de kernel/procesos.
- Conservados 443 artefactos (441 idénticos, dos logs append-only), 38 archivos
  privados/configurados idénticos, common configs y 15 DB oficiales legibles.
- Defecto propio demostrado: install_db prefiere admin_password común, pero el
  helper escribía después otra conf de sitio. Nuevos sitios reutilizan la común
  retenida; ninguno anterior, password, política o acceso se cambia.
- 16 pendientes: 14 PASS/2 ERROR en ocho intentos acotados preservados.
  HTTP500 OAuth reproducido como SecurityException de tracker; Client frame537,
  request presente/cache_control None, asignaciones nativas observadas. No fix
  upstream/request falso. API key adicional FAIL/UNKNOWN conservado, sin reset.
- PATH PDF corregido por invocación; Client 11 PASS/2 ERROR. Observador ahora
  incluye Local nativo de Frappe y control de regresión. Benchmark sin profiling:
  Performance 22 PASS y umbral original intacto.
- 49.823 archivos Cencomun idénticos; lectura autenticada USD50.00/stock5 PASS.
  Core no repetido: 34 grupos previos, C13 BLOCKED/seis PATCH UNRUN.
- Informe detallado: reports/frappe-auth-request-diagnostics.md. Cierre y
  publicación saneada solo lab; PR #4 borrador. Nuevo draft ordinario solo
  referencia/instrucciones; Guardar/Publicar permanece con el coordinador.
