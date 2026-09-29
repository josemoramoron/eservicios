# Estado Técnico — eServicios

_Última actualización: 29 de septiembre de 2026_

_Bitácora de deuda técnica y decisiones tomadas sobre la marcha. `.clinerules` queda solo con reglas de ingeniería vigentes; este archivo es donde se anota qué se detectó, qué se resolvió (con commit) y qué sigue pendiente._

## Deuda técnica


- ~~`deploy.sh` sin versionar~~ — **resuelto 2026-09-29**. Copiado tal cual a
  `scripts/deploy.sh`, hook `post-receive` actualizado a mano por SSH para
  llamar a la copia versionada (`sed` de una sola línea, con backup del hook
  antes de tocarlo), probado con un commit vacío + push (deploy corrió limpio,
  health check OK) y borrada la copia suelta vieja. Nota: no hizo falta
  esperar el túnel SSH (pendiente siguiente) — el acceso LAN/`eservicios-webmaster`
  de siempre alcanzó.
- ~~Túnel SSH vía Cloudflare para eservicios~~ — **resuelto 2026-09-29**.
  Ceiba21 tenía el patrón documentado (`ssh.ceiba21.com`, alias `ceiba21-tunnel`);
  eservicios no lo tenía, solo `eservicios-webmaster` por IP local (`192.168.20.74`,
  sin acceso remoto).
  - Al revisar el túnel `eservicios-prod` en el dashboard de Cloudflare apareció
    una ruta SSH ya existente, `ssh-botisa.3quasar.com` — pero es de Botisa, otro
    proyecto de Jose sin relación con eservicios (confirmado por Jose); no se tocó.
  - Servidor (Pi, túnel local no manejado por dashboard): backup de
    `/etc/cloudflared/config.yml`, agregada la regla `ssh.eservicios.org` →
    `ssh://localhost:22` ANTES del wildcard `*.eservicios.org` (si no, el wildcard
    la intercepta primero), validado con `cloudflared tunnel --config ... ingress
    validate` antes de aplicar, `systemctl restart cloudflared` (reconectó sano,
    sin downtime del sitio). DNS creado con
    `cloudflared tunnel route dns eservicios-prod ssh.eservicios.org` (necesario
    aparte del ingress porque el túnel no es dashboard-managed).
  - Cliente (laptop Ubuntu "asus"): `cloudflared` instalado (no estaba — ojo,
    el `.deb` de GitHub es por arquitectura, `arm64` para la Pi, `amd64` para la
    asus, un primer intento se corrió por error en la Pi y `dpkg` lo rechazó solo,
    sin causar daño). Alias nuevo en `~/.ssh/config`:
    ```
    Host eservicios-tunnel
      HostName ssh.eservicios.org
      User webmaster
      ProxyCommand cloudflared access ssh --hostname %h
      IdentityFile ~/.ssh/id_ed25519_eservicios_pi
    ```
    (mismo `User`/`IdentityFile` que ya usaba `eservicios-webmaster`, para no
    depender de una llave nueva).
  - Verificado extremo a extremo: `ssh eservicios-tunnel "echo CONEXION_OK && hostname && whoami"`
    → `CONEXION_OK` / `raspberrypi` / `webmaster`, sin pasar por la red local.
    El host key coincidió con el ya conocido de `eservicios-webmaster` en
    `known_hosts` (mismo Pi, confirmado).
- ~~`datetime.utcnow()` deprecado~~ — **resuelto 2026-09-26**. Se creó
  `app/services/tiempo_service.py` con un helper `ahora_utc()` que
  devuelve `datetime.now(datetime.UTC).replace(tzinfo=None)`: mismo
  datetime naive que devolvía `datetime.utcnow()` (compatible con las
  columnas `DateTime` de los modelos, que no usan `timezone=True`, sin
  necesitar una migración de BD), pero sin el `DeprecationWarning`.
  Reemplazados los 28 usos reales en 6 archivos de servicio
  (`vendor_registro_service.py`, `vendor_perfil_service.py` — ambos
  herederos del extinto `vendor_service.py` —, `estadisticas_service.py`,
  `subdominio_service.py`, `vendor_admin_service.py`,
  `vendor_email_verificacion_service.py`) y 3 archivos de test
  (`test_vendor_registro.py`, `test_vendor_perfil.py`,
  `test_vendor_whatsapp.py`). Pendiente: revisar si Ceiba21 tiene el
  mismo patrón (proyecto aparte, no tocado acá).

_Ver también: `.clinerules` (reglas de ingeniería)._
