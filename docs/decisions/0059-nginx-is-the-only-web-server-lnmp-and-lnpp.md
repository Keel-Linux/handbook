# 0059: nginx is the only web server, and LNMP and LNPP are the base stacks

Date: 2026-10-16
Status: **decided by the maintainer, 2026-10-16**: "começa com LNMP nginx
mariadb e PHP; não vai haver LAMP, vamos aposentar o Apache no Keel Linux
no lugar do nginx. E LNPP postgres python nginx." The coordinator decided
the details under the maintainer's standing delegation of design calls,
with the option of least power each time.

## What was asked

1. Keel retires Apache. nginx is the only web server.
2. There is no LAMP. The base stacks are LNMP (nginx, MariaDB, PHP) and
   LNPP (nginx, PostgreSQL, Python). LNMP is first.

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel has two web servers.
   Keel Web (0030) is nginx with Coraza and Anubis, and every new layer
   is built on it. The older recipes from TurnKey (WordPress, Moodle,
   Odoo, ejabberd, and the archived apache-php, LAMP and LAPP) use
   Apache. Each web server needs its own TLS setup, its own WAF, its own
   tests and its own security updates. Decision 0023 retired Apache only
   "per appliance", so no recipe had a target to move to.
2. **Whether it can be made to work.** It can. nginx with PHP-FPM serves
   PHP applications, and nginx in front of a WSGI server serves Python
   applications. Debian 13 has every part: `nginx`, `php8.4-fpm`,
   `mariadb-server` 11.8, `postgresql` 17, `gunicorn` 23.0.0 and
   `python3-psycopg` 3.2.6. keel converges the database pair by the
   engine that the spec names (`database.server.engine`), not by the
   name of the appliance, so a stack layer can be a pair too.
3. **Why this is better.** One web server means one TLS setup, one WAF,
   one bot filter and one set of tests. Each application is a layer on
   a stack layer, so the web half and the database half are built and
   tested once.

## Decision

1. **Apache is retired from Keel.** No new image carries `apache2`.
   nginx, as Keel Web carries it, is the only web server. The recipes
   that use Apache move to nginx one at a time, each in its own pull
   request, in the order below.

2. **LNMP and LNPP are two layers on Keel Web, one image each (0047).**

   | Stack | Chain | The layer adds | Repository |
   | --- | --- | --- | --- |
   | LNMP | Core, Web, `lnmp` | PHP-FPM 8.4, MariaDB 11.8 | `Keel-Linux/keel-lnmp` |
   | LNPP | Core, Web, `lnpp` | Python 3.13, gunicorn, PostgreSQL 17 | `Keel-Linux/keel-lnpp` |

   Each is built with `bt-layer lnmp --parent web` and `bt-layer lnpp
   --parent web`, and released by `keel-release` as the other layers
   are. An application is a layer on one of them.

3. **The database server is in the stack layer.** It is standalone by
   default. The pair of 0049 (MariaDB) and 0054 (PostgreSQL) is
   available by the spec: `database.server` and `appliance.vip`, as on
   the database layers. The appliance manifest of the stack
   (`lnmp.yaml`, `lnpp.yaml`, `base: web`) declares the database
   process on a `mesh` port, its Monit check, and the `db_password`
   secret.

   The stack images do not carry the `keel-mariadb` or the
   `keel-postgresql` manifest. Their `base` is `core`, so each would be
   a second manifest that no other manifest is built on, and `keel
   inspect` could not name the appliance. Thus the stack layer copies
   what the database layers add to the server: the bind to the two
   loopback addresses, the socket units of `mariadb-server` masked
   (keel-mariadb#29), and the first boot hooks that set and verify the
   password. A later change moves these files into one overlay package
   per engine (`kind: overlay`, `provides`, as the appendix of
   docs/manifest-v1.md describes). Then the database layers and the
   stacks share one copy.

4. **A stack puts its routes in an include directory of Keel Web.**
   keel does not render the sites of 0042 yet. keel-web 0.3.0 includes
   `/etc/nginx/keel-default.d/*.conf` in its default site and in the
   server behind Anubis (`unix:/run/nginx/keel-app.sock`). A stack puts
   its `location` blocks there. Thus a route works in the simple mode
   and behind Anubis in the cloud modes, and the sites stay conffiles of
   keel-web. When keel renders the sites of 0042, the routes move to the
   `web` section of the manifest.

5. **The Python application server is gunicorn, from Debian 13.** A
   systemd socket unit holds a unix socket, nginx proxies to it, and
   systemd starts gunicorn at the first request. The reasons:
   - It is in Debian main (`gunicorn` 23.0.0), so security updates come
     from Debian.
   - It is pure Python and needs no plugin. uWSGI needs
     `uwsgi-plugin-python3` beside the server, and its upstream is in
     maintenance mode.
   - A systemd socket is the deployment that the gunicorn documentation
     gives ("Deploying Gunicorn", systemd). No TCP port opens, so the
     firewall has nothing to add.
   - The service runs as its own system user with no shell and no
     write access outside its runtime directory.

   The Python libraries come from Debian 13 only (`python3-*`). Nothing
   is installed with pip into the system Python, as 0022 says.

6. **Each stack has a check page that proves each layer works.** It is
   at `/keel-check/` over HTTPS:
   - LNMP: a PHP page that reads from MariaDB.
   - LNPP: a WSGI application that reads from PostgreSQL.

   The page shows the version of the language and of the server, the
   role of the server (writable or read-only), and a row that the first
   boot writes. On a pair, the row on the replica comes from the
   primary, so the page also proves the replication. The page only
   reads: a write on a replica stopped the replication once
   (tracker#26). Its database account has `SELECT` on one database
   only. The server authenticates it by the operating system user
   (`unix_socket` for MariaDB, `peer` for PostgreSQL), so no password
   for it is in the image or on the disk. The page shows no `phpinfo()`
   and no configuration.

7. **TLS and the firewall are Keel Web's.** HTTPS uses the certificate
   of the machine (`default` in 0042), which keel-host-keys makes at the
   first boot. The firewall is the one keel derives from the manifests
   in cloud advanced (0041): 80 and 443 `public` from Web, 3306 or 5432
   `mesh`. PHP-FPM and gunicorn listen on unix sockets only.
   `WEBMIN_FW_TCP_INCOMING` is `22 80 443 12321`.

## What uses Apache today, and the order of the migration

Found on 2026-10-16 in every repository of `Keel-Linux` on git.pop.coop
and in the products of the build host.

| Where | What | Action |
| --- | --- | --- |
| `keel-apache-php`, `keel-lamp`, `keel-lapp` | Apache layers. Archived on git.pop.coop | Stay archived. The layers `apache-php`, `lamp`, `lamp-client`, `lapp` and `lapp-client` leave `conf/appliances` of `apt`, so no release builds them. Their published files stay until a withdrawal, which is a separate act |
| `keel-wordpress` | WordPress on Apache and PHP, a layer on `mariadb` | Step 4: WordPress on `lnmp`. Done on 2026-10-18 (docs/evidence/2026-10-18-wordpress-nginx-cross-site.md) |
| `keel-moodle` | `lamp.mk`, `apache-credit`, `sites-available/moodle.conf` | Step 5: Moodle on `lnmp` |
| `keel-odoo` | `lapp.mk`: Odoo 16 behind Apache | Step 6: Odoo on `lnpp`, as 0022 describes |
| `keel-ejabberd` | The `apache` overlay for its web pages | Step 7: on Web |
| `keel-nginx-php-fastcgi` | nginx, PHP-FPM and MariaDB from TurnKey, no Apache | Step 8: archived, `keel-lnmp` replaces it |
| `common` | `mk/turnkey/{apache,lamp,lapp,adminer}.mk`, `conf/apache-*`, `conf/adminer-apache`, `overlays/apache`, `overlays/confconsole-lamp`, `overlays/confconsole-lapp`, `plans/turnkey/lamp*`, `lapp`, `tomcat-apache` | Step 8: removed in one PR after the last recipe moves. `conf/php` points Webmin's PHP module at Apache's `php.ini`: the LNMP layer points it at PHP-FPM's |
| `inithooks` | `keel-host-keys.service` (`Before=apache2.service`), `lib/sslcert.sh` (`SSLCERT_SERVICES`) | Step 8. A name in a list has no effect when the unit is not there |
| `keel` | `keel/system/state.py` (`TLS_SERVICES`) | Step 8, as `inithooks` |
| `confconsole` | `plugins.d/Lets_Encrypt/dehydrated-wrapper` (the `apache2` case) | Step 8, as `inithooks` |
| `buildtasks`, `keel` tests | A bookworm patch of TurnKey's Canvas, and test fixtures that name `lamp` | No action: no image uses them |
| `webmin` | Webmin's own Apache module | No action: it is upstream code, and no Keel image installs `webmin-apache` |

The order:

1. This note.
2. keel-web 0.3.0: the include directory of decision 4.
3. `keel-lnmp`, then `keel-lnpp`, released as testing pre-releases
   (0052, section 8) and tested on the real platform with evidence
   (0053).
4. WordPress on LNMP (done on 2026-10-18).
5. Moodle on LNMP.
6. Odoo on LNPP.
7. ejabberd on Web.
8. The clean up: `keel-nginx-php-fastcgi` archived, the Apache parts
   of `common` removed, and `apache2` taken out of the lists in
   `inithooks`, `keel` and `confconsole`, one PR for each repository.

## What this amends

- **0023 and 0030**: "Apache retired per appliance" becomes "Apache
  retired from Keel". After step 8, no Keel image carries Apache.
- **0047**: the WordPress chain is Core, Web, LNMP and WordPress. The
  "Keel PHP" layer of 0047 is the `lnmp` layer: PHP-FPM with the MariaDB
  server that it embeds. An application on it keeps the database
  server enabled or disabled per mode, as 0047's table says.
- **docs/manifest-v1.md, appendix**: `base: php` and `base: python` in
  the examples are `base: lnmp` and `base: lnpp`.
- **0022** (proposed): its LNPP stack layer is `lnpp`, and its
  application server is gunicorn.

## When to revisit

- When keel renders the sites of 0042: the routes of decision 4 move to
  the manifest.
- When the overlay packages of decision 3 exist: the stack layers drop
  their copies.
