# 0042: Keel Web sites

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30**, with two changes to
the proposal (Nginx's standard layout, and IPv4 on by default) and the
answers to its open questions, all under "Resolved"; the text below
already reflects them. It turns Keel Web
(0030) from "Nginx, Coraza and Anubis are installed" into "an operator
declares sites and Keel serves them": the sites, how they are declared in
the spec, what keel renders from them, how the console edits them, and how
each one gets its certificate. It lands in Phase 3 of the roadmap
(tracker#46). Nothing here is implemented.

The maintainer's requirements, 2026-09-30, which this note answers:

- a console menu for the web server alone: add sites, `proxy_pass`,
  WebSocket and the rest. **The screen writes the spec; keel renders Nginx
  from tested templates.** No free-form configuration, except an
  allowlisted `extra` per site;
- every site has a **mode**: `http`, `tls-passthrough`,
  `tls-terminate-tcp`, `tcp` or `udp`;
- **certificates come from the existing confconsole Certificate feature**,
  which already issues through HTTP-01 or DNS-01; no new ACME flow.

## What exists today

Read on 2026-09-30 from `Keel-Linux/confconsole` (master, 7182873) and
`Keel-Linux/keel` (main, 3c6e456). The rest of the note is built on this,
so it is stated exactly.

**The Certificate feature of confconsole** is the `Lets_Encrypt` menu
(`plugins.d/Lets_Encrypt/`), three entries and a wrapper:

| File | What it does |
| --- | --- |
| `get_certificate.py` ("Certificate Creation Wizard") | Fetches Let's Encrypt's terms of service URL and asks the operator to agree. Asks for the challenge, `http-01` ("requires public web access") or `dns-01` ("requires your DNS provider to provide an API"). For `dns-01` it installs lexicon (below), lets the operator pick a provider from lexicon's list, and edits `/etc/dehydrated/lexicon_<provider>.yml` in a twelve line form. Then a form of five domain boxes: **one certificate, at most five names**, stored as the first uncommented line of `/etc/dehydrated/confconsole.domains.txt`. A wildcard line gets an alias (`*.example.org > star_example_org`). Then it runs `dehydrated-wrapper --register --log-info --challenge <type> [--provider <name>]` |
| `dns_01.py` | Installs lexicon with pip into a venv, `/usr/local/src/venv/lexicon` (`pip install dns-lexicon[full]`, after apt-installing `python3-pip` and `python3-venv` when missing), run through `/usr/bin/turnkey-lexicon`. The provider's credentials file is `/etc/dehydrated/lexicon_<provider>.yml`, root, 0600. **Only one provider file** may exist; two is an error on screen |
| `cert_auto_renew.py` | Toggles the execute bit of `/etc/cron.daily/confconsole-dehydrated` |
| `dehydrated-wrapper` | Copies the config, hook and cron from `/usr/share/confconsole/letsencrypt/` when missing. For `http-01`: finds what listens on port 80 with `netstat`, **stops it** (apache2, lighttpd, nginx, tomcat), starts `add-water`, a small Python server that serves the challenge tokens and a maintenance page for every other URL, runs `dehydrated --cron`, then **restarts** the server it stopped and `webmin.service`. For `dns-01`: the hook creates and deletes the `_acme-challenge` TXT record through lexicon, and afterwards the wrapper **restarts** whatever listens on 443. It backs up the certificate files first and restores them if anything failed |
| hooks (`dehydrated-confconsole.hook-{http,dns}-01.sh`) | `deploy_cert` writes the issued key and full chain to **one fixed set of paths**: `/etc/ssl/private/cert.key`, `/usr/local/share/ca-certificates/cert.crt`, and `/etc/ssl/private/cert.pem` (chain, key and DH parameters), which Webmin, the web shell and every web server read |
| cron (`dehydrated-confconsole.cron`) | Daily: if `/etc/ssl/private/cert.pem` ends within 30 days, runs the wrapper with `--force` |

dehydrated itself (0.7.2 in trixie) keeps each certificate under
`/var/lib/dehydrated/certs/<name>/`, where the name is the line's alias or
its first domain, with `privkey.pem` and `fullchain.pem` as symbolic links
to the current files. It reads a per-certificate `config` in that
directory, in which `CHALLENGETYPE`, `HOOK`, `WELLKNOWN` and `RENEW_DAYS`
(32 by default) may be set. It hands `deploy_cert` the paths in that
directory. Every uncommented line of the domains file is a certificate.

Four consequences for sites:

1. **A second certificate breaks the first.** The screen edits only the
   first line, but dehydrated issues every line, and every issuance writes
   the same three fixed paths: the last one issued wins.
2. **HTTP-01 takes every site down.** The wrapper stops Nginx for the
   duration of the challenge, and the cron's `--force` reissues every line
   whenever the one fixed certificate is due.
3. **Renewal restarts Nginx rather than reloading it**, dropping open
   connections, WebSockets included.
4. **lexicon comes from PyPI at run time.** It is not in Debian (checked on
   trixie), so DNS-01 installs code the Keel repository did not build, on
   the machine, from the network.

One defect found on the way: `invalid_domains` refuses a wildcard with
`http-01` in an `elif` that only runs for an empty box, so the check never
fires and Let's Encrypt refuses the order instead.

**keel's `tls` section** (docs/spec.md, docs/apply.md): `tls.acme` has
`enabled`, `challenge` (`http-01` or `dns-01`), `domains` and
`agree_tos`. `apply --system` writes `confconsole.domains.txt` and runs the
wrapper with `--challenge http-01` when the certificate in use is
self-signed, misses a domain or ends within 30 days, and `--defer-certificate`
skips the request at first boot. **It refuses `dns-01`**, because a DNS
provider and its credentials have no field in the spec. It knows one
certificate.

**Nginx in trixie** is 1.26.3, built (checked on the package) with
`http_v2`, `http_v3`, `http_realip`, `http_auth_request`, `stream`,
`stream_ssl_preread` and `stream_realip`; the stream module is the dynamic
`libnginx-mod-stream`, which depends on `nginx-abi-1.26.3-1` as Coraza's
module will (0041, step 5).

## Decision

1. **A site is declared in the spec, `web.sites[]`, and keel renders it.**
   The console screens are thin writers of the spec, like the Instance
   menu; `keel spec apply --system` renders Nginx from templates that live
   in keel, beside their tests, into **Nginx's standard Debian layout**:
   `sites-available/keel-<site>.conf` with its link in `sites-enabled/`,
   and the same for the stream side under `streams-available/` and
   `streams-enabled/`. keel owns only its own files, recognised by name and
   header (see "What keel renders"); sites an operator wrote by hand
   coexist and are left alone, `keel diff` reports drift only on keel's
   files, and `keel inspect` reports the others as present but not
   declared. No keel site is written by hand. The only free-form input is
   `extra`, a list of allowlisted directives.

2. **Five modes**, each a different path through Nginx:

   | Mode | Nginx | TLS | Coraza and Anubis | Version |
   | --- | --- | --- | --- | --- |
   | `http` | `http` block, `proxy_pass` | terminated here | apply | 1 |
   | `tls-passthrough` | `stream`, routed by SNI (`ssl_preread`) | intact to the backend | see nothing; the screen says so | 1 |
   | `tls-terminate-tcp` | `stream`, `ssl` listener, plain TCP to the backend | terminated here | see nothing | 2 |
   | `tcp` | `stream`, its own port | none | see nothing | 2 |
   | `udp` | `stream`, its own port, `udp` | none | see nothing | 2 |

3. **Port 443 is shared through a stream front, and only when it must be.**
   While no passthrough site exists, `http` sites listen on `[::]:443`
   directly, as a plain Nginx does. The first passthrough site moves 443 to
   a `stream` server with `ssl_preread`, which maps the SNI name to either
   the passthrough backend or the local `http` block, reached on a unix
   socket with the PROXY protocol, so the client's address survives the
   hop. See "Sharing port 443".

4. **The site names a certificate; the Certificate feature issues it.**
   `tls.certificate: <name>` on a site; the certificates themselves become
   a list in `tls.acme`, each a line of dehydrated's domains file with its
   name as the alias, each with its own challenge. The site screen hands
   off to the Certificate screen with the site's names filled in. HTTP-01
   is answered by Nginx itself from dehydrated's challenge directory, so
   no site stops; renewal reloads Nginx. DNS-01 is required for a wildcard
   and for a node with no public port 80. See "Certificates" for the
   changes the feature needs.

5. **The client's real address is a first-class setting**, `web.real_ip`,
   because CrowdSec, Coraza, Anubis, `limit_req` and the logs all key on
   it: `direct`, `proxy_protocol` from a trusted balancer, or a trusted
   `header`; every internal hop (the stream front, Anubis) carries it and
   the template restores it.

6. **Upstreams are named groups of servers with passive failover**
   (`max_fails`, `fail_timeout`, `backup`), which may be loopback, mesh
   addresses of other nodes, or a database VIP (0029). Active health
   checks are Monit's, derived like the manifest's (0041), and alert only.
   When every server of a group fails the site shows its maintenance page
   with 503, which covers the gap of a hot-standby promotion (0031).

7. **Safe by default, per site**: HTTPS only with a redirect from 80,
   HSTS once the certificate is a CA's, `X-Frame-Options`,
   `X-Content-Type-Options`, a `Referrer-Policy`, an optional
   `Content-Security-Policy`, an IP allowlist per path, Coraza's mode per
   site, and a `default_server` that refuses unknown names
   (`ssl_reject_handshake`, 444 on 80).

8. **IPv6 first, IPv4 on by default**: every listener is written on
   `[::]` first and on `0.0.0.0` second. `web.listen.ipv4: false` (or a
   site's `ipv4: false`) is the operator's opt-out, for an IPv6-only
   machine.

9. **An application's manifest declares its routes**; the operator's site
   says `routes: manifest` and chooses only names, certificate and
   protection. The manifest owns the fact that Odoo has a WebSocket on
   `/websocket` on port 8072; the spec owns the choice of the name it is
   served under (0041, choice 2).

10. **Apply is test first, keep the old on failure.** keel renders its
    files into a staging copy of `/etc/nginx`, runs `nginx -t` on it,
    installs them, runs `nginx -t` again and reloads; any failure puts
    keel's previous files back and does not reload. The screen shows the generated configuration and the `nginx -t`
    output before it commits anything, and restores the previous spec when
    apply fails, so the spec and the running Nginx never disagree.

11. **The version 1 and version 2 cut** is the maintainer's, with the items
    the requirements did not place assigned under "Version 1 and version
    2" (IP allowlist, gzip, SSE, logs and `extra` in version 1; gRPC in
    version 2).

## Sharing port 443

Nginx has one owner per listening socket: a `stream` server and an `http`
server cannot both listen on `[::]:443`. So when a passthrough site
exists, the stream module owns 443 and the `http` block moves behind it.

```nginx
# /etc/nginx/streams-available/keel-front.conf, linked from
# streams-enabled/ only while a tls-passthrough site exists
map $ssl_preread_server_name $keel_route {
    hostnames;
    git.example.org          keel_pt_git;        # passthrough, backend takes PROXY
    vault.example.org        keel_pt_vault_strip; # passthrough, backend does not
    default                  keel_http;          # every http site, and no SNI
}
upstream keel_http           { server unix:/run/nginx/keel-https.sock; }
upstream keel_pt_git         { server [fd4b:7c1e:30a2::3]:443; }
upstream keel_pt_vault_strip { server unix:/run/nginx/keel-pt-vault.sock; }

server {
    listen [::]:443;                 # IPv6 first
    listen 0.0.0.0:443;              # unless web.listen.ipv4 is false
    ssl_preread on;
    proxy_pass $keel_route;
    proxy_protocol on;               # always: the next hop learns the client
    access_log /var/log/nginx/keel-stream.access.log keel_stream;
}

# a passthrough backend that does not speak PROXY: one more local hop that
# reads the header, logs the real client, and forwards without it
server {
    listen unix:/run/nginx/keel-pt-vault.sock proxy_protocol;
    set_real_ip_from unix:;
    proxy_pass [fd4b:7c1e:30a2::4]:443;
    proxy_protocol off;
}
```

```nginx
# /etc/nginx/sites-available/keel-erp.conf, an http site behind the front
server {
    listen unix:/run/nginx/keel-https.sock ssl proxy_protocol;
    http2 on;
    server_name erp.example.org;
    set_real_ip_from unix:;
    real_ip_header proxy_protocol;
    # ... the site
}
```

Why this shape:

- **The front always sends PROXY.** `proxy_protocol` is a per-server
  setting in `stream`, not per route, so the front cannot send it to one
  backend and not another. It always sends it; the `http` block always
  expects it; a passthrough backend that does not speak it gets one more
  local hop that strips it. The real client address is therefore known at
  every hop, and the stream log has it for every passthrough site.
- **A unix socket, not a loopback port**, for the hop into `http`: it
  takes no port from the manifest's port space (0041, rule 17), needs no
  firewall rule, and cannot be reached from outside the machine, so
  trusting `unix:` for the PROXY header trusts only the front.
- **Only when needed.** A machine with only `http` sites, which is every
  simple installation, runs Nginx exactly as Nginx is usually run, and the
  stream front is one more thing that can fail only where it buys
  something. The cost is two topologies to test; the template tests cover
  both, and moving between them is an ordinary reload (the master process
  opens the new sockets).
- **No SNI, or an unknown name**, goes to `keel_http`, whose
  `default_server` refuses the handshake (`ssl_reject_handshake on`), so a
  scanner learns no certificate and no name.
- **HTTP/3 (version 2) is UDP** and never passes through the TCP front: an
  `http` site with `http3: true` listens `quic` on `[::]:443` directly.
- **A hand-written site on 443 blocks the front.** Once the front owns
  TCP 443, an `http` server of the operator's that still listens on 443
  cannot bind, and `nginx -t` does not catch that (it does not bind). So
  before linking the front, keel reads `nginx -T` and refuses to add a
  passthrough site while a file it does not own listens on TCP 443,
  naming the file; the operator moves that site to a keel site or off
  443 first.

Port 80 stays in the `http` block in both topologies: it serves the ACME
challenges and redirects to HTTPS. For a passthrough site's names it
forwards `/.well-known/acme-challenge/` to the backend's port 80, so a
backend that gets its own certificate by HTTP-01 still can, and redirects
the rest to HTTPS.

## The spec: `web`

A new top-level section, additive, so the spec stays `version: 1`. The
emitter writes every field out, defaults included (0027).

```yaml
web:
  listen:
    ipv4: true                  # [::] first, then 0.0.0.0; false opts out
  real_ip:
    source: direct              # direct | proxy_protocol | header
    trusted: []                 # CIDRs of the balancer or proxy in front
  logs:
    access: per_site            # per_site | off
  upstreams:
    - name: erp
      servers:
        - {address: "::1"}
      max_fails: 3
      fail_timeout: 10s
      keepalive: 16
  sites:
    - name: erp
      mode: http
      names: [erp.example.org]
      # ... below
```

### Global fields

| Field | Default | Notes |
| --- | --- | --- |
| `web.listen.ipv4` | `true` | Every listener is written on `[::]` first and on `0.0.0.0` second. Nginx's `[::]` listeners are `ipv6only=on`, so `false`, the operator's opt-out, makes the machine answer on IPv6 only |
| `web.real_ip.source` | `direct` | `direct`: the TCP peer is the client. `proxy_protocol`: a layer 4 balancer in front sends PROXY v1 or v2, and every public listener requires it. `header`: a layer 7 proxy in front sends `X-Forwarded-For` (see "Real client IP") |
| `web.real_ip.trusted` | `[]` | CIDRs of that balancer or proxy. Required and non-empty unless `direct` |
| `web.logs.access` | `per_site` | `off` keeps only the error logs; CrowdSec then has nothing to read, and the screen says so |
| `web.upstreams[]` | `[]` | Named groups, shared by sites. See "Upstreams" |
| `web.sites[]` | `[]` | The sites, in the order the screen lists them. Order has no meaning to Nginx |

### A site

| Field | Modes | Default | Notes |
| --- | --- | --- | --- |
| `name` | all | required | `[a-z][a-z0-9-]*`, at most 32; names the files, the logs and the checks |
| `mode` | all | required | `http`, `tls-passthrough`, `tls-terminate-tcp`, `tcp`, `udp` |
| `enabled` | all | `true` | `false` keeps the site in the spec and renders nothing for it |
| `names` | `http`, both `tls-*` | required | Server names, the canonical one first. `*.example.org` allowed. Unique across all sites |
| `port` | `tcp`, `udp`, `tls-terminate-tcp` | required | Its own listening port. Never 80, 443 or a port of the resolved manifest chain (0041, rule 17), so a site cannot take SSH, Webmin or the LAPI |
| `expose` | `tcp`, `udp`, `tls-terminate-tcp` | required | `public`, `mesh` or `loopback`, as 0041 defines them; the firewall is derived from it |
| `ipv4` | all | `web.listen.ipv4` | Per-site override |
| `to` | all but `http` | required | `{upstream: NAME, port: N}` |
| `proxy_protocol` | all but `http` | `false` | `true`: the backend receives PROXY and so the client's address. The screen asks whether the backend accepts it; one that does not breaks on the first byte |
| `tls.certificate` | `http`, `tls-terminate-tcp` | `default` | A certificate name from `tls.acme` (see "Certificates"), or `default`, the machine's |
| `tls.hsts` | `http` | `{max_age: 31536000, subdomains: false, preload: false}` | Emitted only while the certificate is a CA's: HSTS over a self-signed certificate locks visitors out |
| `redirect_http` | `http` | `true` | Port 80 answers 301 to HTTPS, except the ACME challenge path |
| `www` | `http` | `none` | `to_apex`, `to_www`, `serve` (both names, no redirect) or `none` (only the names listed). Adds the other name, which the certificate must cover |
| `redirect_from` | `http` | `[]` | `{names: [...], code: 301}`: old names that answer with a redirect to the canonical name, path and query kept. The certificate must cover them |
| `routes` | `http` | required | A list of locations, or the word `manifest` (see "Sites an application declares") |
| `routes[].path` | `http` | required | A prefix, `/` or longer; `= /exact` for an exact match. No regular expressions in version 1 |
| `routes[].to` | `http` | required | `{upstream: NAME, port: N}`, or `{static: DIR}` with `DIR` under `/var/www/keel/<site>/` |
| `routes[].websocket` | `http` | `false` | `Upgrade` and `Connection` passed, HTTP/1.1 to the backend, read timeout 3600 s |
| `routes[].stream` | `http` | `false` | For SSE and long polling: `proxy_buffering off`, `proxy_cache off`, read timeout 3600 s |
| `routes[].protocol` | `http` | `http` | `https` to a backend that only speaks TLS (verified against the system CAs, `proxy_ssl_server_name on`); `grpc` in version 2 |
| `routes[].max_body` | `http` | the site's | `client_max_body_size` for this path |
| `routes[].timeout` | `http` | `60s` | `proxy_read_timeout` and `proxy_send_timeout` |
| `routes[].allow` | `http` | `[]` | CIDRs; when not empty, everyone else gets 403 on this path (`allow`, `deny all`) |
| `routes[].extra` | `http` | `[]` | See "The `extra` allowlist" |
| `max_body` | `http` | `16M` | The site's `client_max_body_size` |
| `protect.waf` | `http` | `enforce` if the `coraza` overlay is enabled, else `off` | `enforce`, `detect` (log only, for a new site) or `off` |
| `protect.anubis` | `http` | `true` if the `anubis` overlay is enabled, else `false` | Route the site through Anubis (0030), under the one global policy the `anubis` overlay ships; `false` is the per-site opt-out. Per-site policies are version 2 |
| `headers.frame_options` | `http` | `SAMEORIGIN` | `DENY`, `SAMEORIGIN` or `off` |
| `headers.csp` | `http` | none | A `Content-Security-Policy` value, checked for the characters of the grammar; no default, because a wrong one breaks the application |
| `headers.referrer_policy` | `http` | `strict-origin-when-cross-origin` | |
| `gzip` | `http` | `false` | `true` compresses text types; off by default because compression over TLS of a response that mixes a secret with input is what BREACH attacks |
| `maintenance` | `http` | `{mode: auto}` | See "Maintenance page" |
| `extra` | `http` | `[]` | Server-level, see "The `extra` allowlist" |
| `http3`, `cache`, `limit_req`, `basic_auth`, `client_certificates` | `http` | absent | Version 2; declared here so the names are reserved |

`X-Content-Type-Options: nosniff` is always sent. Every proxied request
carries `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` and
`X-Forwarded-Host`, set by the template and not by `extra`.

### Upstreams

| Field | Default | Notes |
| --- | --- | --- |
| `name` | required | `[a-z][a-z0-9-]*` |
| `servers[].address` | required | A literal IPv6 or IPv4 address: `::1`, a mesh address of another node, a database VIP. Never a name: a name resolved once at start is a name that silently stops being true (the reason docs/spec.md gives for `localhost`) |
| `servers[].backup` | `false` | Used only while every non-backup server is down |
| `servers[].weight` | `1` | |
| `max_fails`, `fail_timeout` | `3`, `10s` | Passive failover: after that many failed attempts within the time, the server is skipped for that time |
| `keepalive` | `16` | Idle connections kept per worker; `0` for none |
| `check` | none | `{type: http, path: /web/health, expect: 200}` or `{type: tcp}`: an active check Monit runs against every server of the group, `on_failure: alert` |

The port is not part of the group: a route names `{upstream: erp, port:
8072}`, so the hosts of an application are written once and each port it
serves (Odoo's 8069 and 8072) is a route's choice. keel renders one Nginx
`upstream` per group and port that a site uses.

**Mesh and VIP rules.** A mesh address is the overlay address of another
node (0020, 0024); traffic to it already runs inside WireGuard, so `http`
to it is not plain text on the wire. A group lists either a VIP or the
real addresses of a replicated set, never both, since the standby behind a
real address is read only (0031) and the VIP already moves to the active
node (0029). In version 1 the VIP exists for the database appliances only
(0041, "Resolved"), so a VIP upstream is for a `tcp` site (version 2)
that publishes a database to the mesh.

**Active checks.** Monit's (0040). keel derives them from `upstreams[].check`
into `/etc/keel/monit/keel-web.conf`, rendered and included exactly as
0041 has the manifest's checks rendered and included, named
`web-<upstream>-<n>`, always `alert`: Monit cannot restart a process on
another node, and Nginx's passive failover is already routing around it.
A loopback server whose process a manifest declares gets no second check;
the manifest's check restarts it.

## Examples

### An Odoo site, declared by hand

Odoo on this node: the HTTP workers on 8069, the gevent worker on 8072
for `/websocket` (Odoo 16 and later) and `/longpolling` (up to 15). Only
the one that the installed Odoo serves is needed; both are shown.

```yaml
web:
  listen: {ipv4: true}
  real_ip: {source: direct, trusted: []}
  logs: {access: per_site}
  upstreams:
    - name: odoo
      servers: [{address: "::1"}]
      max_fails: 3
      fail_timeout: 10s
      keepalive: 16
  sites:
    - name: erp
      mode: http
      names: [erp.example.org]
      www: none
      redirect_http: true
      tls:
        certificate: erp
        hsts: {max_age: 31536000, subdomains: false, preload: false}
      max_body: 128M
      routes:
        - {path: /, to: {upstream: odoo, port: 8069}}
        - {path: /websocket, to: {upstream: odoo, port: 8072}, websocket: true}
        - {path: /longpolling, to: {upstream: odoo, port: 8072}, stream: true}
        - {path: /web/database, to: {upstream: odoo, port: 8069},
           allow: ["2001:db8:10::/48"]}
      protect: {waf: enforce, anubis: false}
      headers: {frame_options: SAMEORIGIN, referrer_policy: strict-origin-when-cross-origin}
      maintenance: {mode: auto}
tls:
  acme:
    enabled: true
    agree_tos: true
    challenge: http-01
    domains: [host1.example.org]
    certificates:
      - {name: erp, domains: [erp.example.org], challenge: http-01}
```

Odoo itself must run with `proxy_mode = True` to believe
`X-Forwarded-*`; that is the application's configuration, not the site's.
Anubis is off because a proof of work page in front of an ERP's JSON
calls breaks the client, which is the operator's call per site. The
database manager is reachable only from one prefix.

### A passthrough site

A service on another node that terminates its own TLS and accepts PROXY:

```yaml
web:
  upstreams:
    - name: git-node
      servers: [{address: "fd4b:7c1e:30a2::3"}]
  sites:
    - name: git
      mode: tls-passthrough
      names: [git.example.org]
      to: {upstream: git-node, port: 443}
      proxy_protocol: true
```

No certificate, no headers, no WAF, no Anubis, no maintenance page: Nginx
never sees inside the connection. Port 80 for `git.example.org` forwards
the ACME path to the backend and redirects the rest.

### A TCP stream (version 2)

PostgreSQL of a database set, published to the mesh through its VIP
(0029):

```yaml
web:
  upstreams:
    - name: db-vip
      servers: [{address: "fd4b:7c1e:30a2::100"}]
      check: {type: tcp}
  sites:
    - name: pg
      mode: tcp
      port: 5432
      expose: mesh
      to: {upstream: db-vip, port: 5432}
      proxy_protocol: false
```

The firewall opens 5432 on the WireGuard interface only. PostgreSQL would
see the Nginx node's address as its client, so its `pg_hba.conf` must
allow that node; a `tcp` site cannot pass the client's address to a
backend that does not speak PROXY.

### A site with two upstreams across the mesh

The application runs on two nodes; this node runs only Keel Web:

```yaml
web:
  upstreams:
    - name: app
      servers:
        - {address: "fd4b:7c1e:30a2::2"}
        - {address: "fd4b:7c1e:30a2::3", backup: true}
      max_fails: 2
      fail_timeout: 15s
      keepalive: 32
      check: {type: http, path: /health, expect: 200}
  sites:
    - name: social
      mode: http
      names: [social.example.org]
      www: to_apex
      redirect_from:
        - {names: [social.example.net, www.social.example.net], code: 301}
      tls: {certificate: social}
      max_body: 99M
      routes:
        - {path: /, to: {upstream: app, port: 3000}}
        - {path: /api/v1/streaming, to: {upstream: app, port: 4000}, websocket: true}
      maintenance: {mode: auto, retry_after: 120}
```

While `::2` answers, `::3` receives nothing. After two failures within 15
seconds `::2` is skipped for 15 seconds and `::3` takes the traffic; if
`::3` is a hot standby that has not been promoted (manual by default,
0020, 0031) it fails too, and visitors get the maintenance page with 503
and `Retry-After: 120` rather than a bare 502. Monit alerts on each server
it cannot reach. The certificate `social` must cover the canonical name,
`www.social.example.org` (for `to_apex`) and both old names.

## Certificates

**The rule: the site names a certificate, and the Certificate feature
issues and renews it.** keel does not talk to Let's Encrypt; it writes
dehydrated's files and runs confconsole's wrapper, as `apply` already does
for `tls.acme` today.

### How a certificate is named

`tls.acme` keeps its fields for the machine's certificate, now called
`default`, and gains a list of named ones:

```yaml
tls:
  acme:
    enabled: true
    agree_tos: true
    challenge: http-01              # the default certificate's, as today
    domains: [host1.example.org]    # the default certificate's, as today
    certificates:
      - name: erp
        domains: [erp.example.org]
        challenge: http-01
      - name: shop
        domains: ["*.shop.example.org", shop.example.org]
        challenge: dns-01
    dns:
      provider: cloudflare          # a lexicon provider name
      credentials: {file: /etc/dehydrated/lexicon_cloudflare.yml}
```

| Field | Notes |
| --- | --- |
| `certificates[].name` | `[a-z][a-z0-9-]*`, not `default`. It is the alias of its line in the domains file and so the directory `/var/lib/dehydrated/certs/<name>/` |
| `certificates[].domains` | One to 100 names (Let's Encrypt's limit per certificate). A wildcard requires `dns-01` |
| `certificates[].challenge` | `http-01` or `dns-01`, written into the certificate's own dehydrated `config` as `CHALLENGETYPE` |
| `dns.provider` | One provider per machine, as the screen already enforces |
| `dns.credentials` | A secret reference (docs/spec.md, "secrets"): the lexicon file, never its content |

What each name means to Nginx:

| `tls.certificate` | Nginx reads |
| --- | --- |
| `default` | `/usr/local/share/ca-certificates/cert.crt` and `/etc/ssl/private/cert.key`, the paths every service reads today; self-signed until `tls.acme` is enabled |
| `<name>` | `/var/lib/dehydrated/certs/<name>/fullchain.pem` and `privkey.pem`, the links dehydrated moves at each renewal |

Until a named certificate has been issued its files do not exist, and
`nginx -t` would fail. keel then renders the site with the `default`
certificate, the screen lists the site as "certificate pending", and
`keel diff` reports it, so a site can be created before DNS points at the
machine (the reason `--defer-certificate` exists).

**Which challenge.** HTTP-01 needs port 80 of this machine reachable from
the Internet under every name, over IPv6 when the name has an AAAA
record. DNS-01 is required for a wildcard and for a node behind NAT or a
firewall with no public port 80, which is the usual case of a node that
reaches the world only through the mesh. The screen asks "is port 80 of
this machine reachable from the Internet?" rather than guessing.

### The hand-off from a site to the Certificate screen

The site screen's certificate step lists the certificates whose names
cover every name the site needs (canonical, `www`, `redirect_from`; a
wildcard covers one label). The operator picks one, or chooses "request a
certificate for these names". That opens the Certificate screen as a
function call (confconsole plugins import each other with `impByPath`, as
`get_certificate.py` imports `dns_01.py`), pre-filled with the site's
names, the site's name as the certificate's, and `dns-01` preselected
when a name is a wildcard. The Certificate screen writes `tls.acme`,
applies, and returns the name, which the site screen writes as
`tls.certificate`. Cancelling leaves the site on `default`.

### Renewal reloads Nginx

The daily cron runs the wrapper **without `--force`**; dehydrated renews
each certificate within its own `RENEW_DAYS`. For each certificate it
renews, the `deploy_cert` hook:

1. for `default` only, writes the three fixed paths and restarts Webmin,
   as today;
2. runs every executable in `/etc/dehydrated/deploy.d/` with the
   certificate's name (taken from the directory dehydrated hands the
   hook). `keel-overlay-nginx` ships `50nginx`, which runs `nginx -t` and,
   when it passes, `systemctl reload nginx.service`. A reload keeps open
   connections and WebSockets; a failed test leaves the running Nginx on
   the old certificate and alerts through `keel notify`.

### What the Certificate feature must change

In `Keel-Linux/confconsole`, `plugins.d/Lets_Encrypt/` and
`share/letsencrypt/`:

1. **It becomes a writer of the spec.** The screen writes `tls.acme` (the
   default certificate and the list), validates, and runs `keel spec apply
   --system-only`, as the Instance screens do; keel writes the domains
   file, one line per certificate with ` > <name>`, and each named
   certificate's `config`. The screen stops writing the domains file
   itself, so the spec is the truth (0027).
2. **Several certificates.** A list screen (add, edit, remove, show
   expiry), each certificate edited with the existing form, its name, its
   challenge, and more than five names when needed.
3. **`deploy_cert` stops overwriting the fixed paths for every line**:
   only `default` goes there; every certificate runs `deploy.d`.
4. **HTTP-01 without stopping the web server.** When Keel Web's Nginx
   holds port 80 (the overlay leaves a marker the wrapper checks), the
   wrapper neither stops it nor starts `add-water`: dehydrated writes the
   token into `WELLKNOWN` (`/var/lib/dehydrated/acme-challenges`) and every
   port 80 server of Keel Web, the default one included, serves
   `/.well-known/acme-challenge/` from there. `add-water` stays for a
   machine without Keel Web.
5. **Reload, not restart**, after a certificate changes (`deploy.d`
   above), and the restart of whatever listens on 443 after DNS-01 goes.
6. **The cron without `--force`**, so one certificate due does not
   reissue all of them.
7. **The wildcard check fixed** (`invalid_domains`, above).
8. **lexicon packaged as a Keel `.deb`**, built in the Keel repository
   with the provider libraries it needs, never installed with pip at run
   time (0039, and 0013's "every image rebuilds from our own archive").
   `dns_01.py` stops installing anything; `turnkey-lexicon` runs the
   packaged lexicon. See "Resolved".

In `Keel-Linux/keel`: `tls.acme.certificates` and `tls.acme.dns`;
`apply` accepts `dns-01` once `dns` is present, and decides per
certificate, from its files, whether to ask for one, as it decides for
`default` today; `inspect` reads every line of the domains file and
reports lines without a name as not managed.

## Real client IP

| `web.real_ip.source` | Public listeners | What the template sets |
| --- | --- | --- |
| `direct` | plain | nothing: `$remote_addr` is the client |
| `proxy_protocol` | `proxy_protocol` on every listener, including the stream front | `set_real_ip_from` each trusted CIDR, `real_ip_header proxy_protocol` (http) and `set_real_ip_from` in `stream`, so the front passes the real client on |
| `header` | plain | `set_real_ip_from` each trusted CIDR, `real_ip_header X-Forwarded-For`, `real_ip_recursive on` |

Inside the machine: the hop from the stream front to `http` trusts
`unix:` and reads PROXY (above); the hop through Anubis, which is Nginx,
then Anubis, then Nginx again on `unix:/run/nginx/keel-app.sock`, sets
`X-Real-IP` on the way in and trusts it only from `unix:` on the way back.
So Coraza, `limit_req`, the allowlists and the logs see the client in
every topology.

Two limits, stated rather than hidden:

- **`header` with a passthrough site is refused.** Behind the stream
  front only the PROXY protocol is trusted: the `http` block must read the
  client from PROXY, and Nginx takes one `real_ip_header` per context;
  reading `X-Forwarded-For` after trusting `unix:` would let any direct
  client forge it. A machine behind a layer 7 proxy has no reason to pass
  TLS through anyway.
- **CrowdSec's firewall bouncer bans addresses at the packet level.**
  Behind a balancer or proxy the packets come from the balancer, so a ban
  decided from the (correct) logs cannot take effect here. keel adds
  `web.real_ip.trusted` to CrowdSec's whitelist so the balancer itself is
  never banned; banning at the front is the front's business.

## Redirects

- **HTTP to HTTPS**: every `http` site, unless `redirect_http: false`;
  the ACME path is always served first.
- **`www`**: `to_apex` and `to_www` render a second server that answers
  301 to the canonical name with the path and query; it needs the other
  name in the certificate.
- **Old domain to new**: `redirect_from` renders one server for the old
  names, 301 (or 308 when asked) to `https://<canonical><request_uri>`.
- No regular expression rewrites in version 1: a structured redirect can
  be validated; `rewrite` cannot.

## Maintenance page

`maintenance.mode`:

| Mode | What visitors get |
| --- | --- |
| `auto` (default) | The application, and when Nginx gets 502, 503 or 504 from every server of the upstream, the page, with status 503 and `Retry-After` (`retry_after`, default 60 seconds) |
| `on` | The page for everyone except `maintenance.bypass` (CIDRs), for planned work and for a promotion in progress |
| `off` | Nginx's own 502 |

The page is `/usr/share/keel-web/maintenance.html` from the overlay, or
`/var/www/keel/<site>/maintenance.html` when present. It is served by
Nginx from disk, so it works when every upstream is gone. A passthrough
site cannot have one: Nginx cannot answer inside a TLS session it does
not hold.

This is where hot standby meets the web: from the moment the primary
fails until the standby is promoted, `auto` answers 503 with a page and
a retry hint; setting `on` for the duration of a planned switchover is one
field and one apply.

## Protocols, cache and compression

- **HTTP/2** is on for every `http` site (`http2 on`, Nginx 1.25.1 and
  later syntax).
- **HTTP/3 and QUIC** (version 2, experimental): trixie's Nginx is built
  with `http_v3`, but Nginx 1.26 marks it experimental and, with
  OpenSSL 3, runs QUIC through its compatibility layer, without 0-RTT.
  `http3: true` adds a `quic` listener on UDP 443 and `Alt-Svc`; the
  `nginx` overlay manifest then needs `443/udp` declared (a manifest
  change, below).
- **WebSocket**: `websocket: true` on a route (Upgrade, Connection from a
  `map`, HTTP/1.1, 3600 s).
- **SSE and long polling**: `stream: true` (buffering off, 3600 s).
- **gRPC** (version 2): `protocol: grpc` renders `grpc_pass` on HTTP/2.
- **proxy_cache** (version 2): `cache: {size: 1g, paths: [/static],
  valid: 10m}`, one zone per site under `/var/cache/nginx/keel/<site>`,
  never for paths with `allow`, `basic_auth` or cookies by default.
- **gzip** (version 1): `gzip: true`, text types, off by default (BREACH,
  above).

## Logs

Every `http` site logs to `/var/log/nginx/keel-<site>.access.log` in
Nginx's `combined` format, which CrowdSec's `crowdsecurity/nginx-logs`
parser reads, and to `keel-<site>.error.log`. The site is in the file
name, not in the line, so the format stays the one the parser knows. The
overlay ships a CrowdSec acquisition for `/var/log/nginx/keel-*.access.log`
(`type: nginx`), and Debian's logrotate for `/var/log/nginx/*.log`
already rotates them. Stream sites log to `keel-stream.access.log` with
the client, the SNI name, the route and the bytes; CrowdSec does not
parse it in version 1.

## The `extra` allowlist

`extra` is a list of `[directive, arg, ...]`, at the server level
(`sites[].extra`) or the location level (`routes[].extra`). It is an
**allowlist**: a directive not in the table is refused by `keel spec
validate`, with the reason. Arguments are strings that keel quotes; a
`;`, `{`, `}`, `#`, quote, backslash or newline in one is refused, and `$`
only names a variable of a short list (`$host`, `$scheme`, `$request_uri`,
`$request_id`, `$remote_addr`, `$http_<name>`).

| Allowed | Where |
| --- | --- |
| `add_header` (not `Strict-Transport-Security`, `Content-Security-Policy` or `X-Frame-Options`, which are fields) | server, location |
| `proxy_set_header` (not `Host`, `X-Real-IP`, `X-Forwarded-*`, `Upgrade` or `Connection`, which the template owns), `proxy_hide_header`, `proxy_pass_header` | server, location |
| `proxy_read_timeout`, `proxy_send_timeout`, `proxy_connect_timeout`, `proxy_buffer_size`, `proxy_buffers`, `proxy_busy_buffers_size`, `proxy_max_temp_file_size`, `proxy_request_buffering` | server, location |
| `proxy_redirect`, `proxy_cookie_path`, `proxy_cookie_domain`, `proxy_cookie_flags` | server, location |
| `client_body_timeout`, `client_body_buffer_size`, `send_timeout`, `keepalive_timeout` | server, location |
| `expires`, `etag`, `if_modified_since`, `charset`, `default_type` | server, location |
| `sub_filter`, `sub_filter_once`, `sub_filter_types`, `sub_filter_last_modified` | server, location |
| `gzip_types`, `gzip_min_length` (with `gzip: true`) | server, location |
| `large_client_header_buffers`, `client_header_timeout`, `client_header_buffer_size`, `server_tokens`, `ignore_invalid_headers`, `underscores_in_headers`, `merge_slashes` | server |

**Never allowed**, each for a reason:

| Directive | Why |
| --- | --- |
| `include`, `load_module` | Pull in a file keel did not render or test |
| `root`, `alias` | Only through `to: {static: DIR}`, which confines `DIR` to `/var/www/keel/<site>/`; a free `root` serves `/etc` |
| `proxy_pass`, `fastcgi_pass`, `uwsgi_pass`, `scgi_pass`, `grpc_pass`, `memcached_pass` | A backend is an upstream group, so it is failed over, checked and visible in the spec |
| every `*_by_lua*`, `lua_*`, `perl`, `perl_set`, `perl_modules`, `perl_require`, `js_*` | Code in the web server; trixie's Nginx has the Perl module available |
| `ssl_*`, `proxy_ssl_*`, `http2`, `http3`, `quic_*`, `listen`, `server_name` | Owned by the mode, the certificate and the listeners |
| `location`, `if`, `set`, `map`, `geo`, `return`, `rewrite`, `error_page` | Change routing; routes, redirects and maintenance are fields |
| `allow`, `deny`, `satisfy`, `auth_*`, `limit_*` | Access control is a field, so it shows on the screen |
| `real_ip_*`, `set_real_ip_from` | `web.real_ip` |
| `access_log`, `error_log`, `log_format` | The CrowdSec format and files |
| `resolver`, `proxy_bind`, `mirror`, `internal`, `proxy_store`, `*_temp_path`, `client_max_body_size` | Side channels, disk writes, or a field already (`max_body`) |
| `dav_*`, `autoindex`, `ssi`, `xslt_*`, `image_filter*`, `secure_link*`, `modsecurity*`, Coraza's directives | Features Keel Web does not offer through a site |

`nginx -t` still runs on the result: the allowlist decides what may be
said, and the test catches a value Nginx refuses.

## What keel renders, and how it applies

**Nginx's standard Debian layout, and `nginx.conf` as Debian ships it.**
Debian's `nginx.conf` (a conffile of `nginx-common`) includes
`/etc/nginx/modules-enabled/*.conf` in the main context, and
`/etc/nginx/conf.d/*.conf` and `/etc/nginx/sites-enabled/*` inside `http`.
keel uses those include points and never edits the file, so an upgrade of
`nginx-common` never stops on a conffile question and needs no divert.

| Path | Owner | Content |
| --- | --- | --- |
| `/etc/nginx/nginx.conf` | `nginx-common`, unchanged | Debian's |
| `/etc/nginx/sites-available/keel-<site>.conf`, linked from `sites-enabled/keel-<site>.conf` | keel | One `http` site: its servers on 80 and 443, its redirects, its locations |
| `/etc/nginx/sites-available/keel-default.conf`, linked from `sites-enabled/` | keel | The `default_server` of 80 (444, and the ACME path) and of 443 (`ssl_reject_handshake`), while any `http` site exists; see "Debian's default site" |
| `/etc/nginx/conf.d/keel-web.conf` | keel | What the `http` sites share: the upstream groups, the `real_ip` settings of the public listeners, the `map` for `Connection`, the log format |
| `/etc/nginx/conf.d/keel-health.conf` | `keel-overlay-nginx` | `/keel-health` on the loopback addresses (0041) |
| `/etc/nginx/modules-enabled/90-keel-streams.conf` | `keel-overlay-nginx` | `stream { include /etc/nginx/streams-enabled/*; }` |
| `/etc/nginx/streams-available/keel-<site>.conf`, `keel-front.conf`, linked from `streams-enabled/` | keel | Stream sites, and the front while a passthrough site exists |
| `/etc/keel/monit/keel-web.conf` | keel | The upstream checks |
| `/etc/crowdsec/acquis.d/keel-web.yaml` | `keel-overlay-nginx` | The acquisition |

**Where `stream` goes, and why there.** Debian ships no `stream` include:
`libnginx-mod-stream` only links `modules-enabled/50-mod-stream.conf`,
which loads the module, and `conf.d` is inside `http`, where `stream {}`
is not allowed. The choices were to edit `nginx.conf`, a conffile, or to
use the one main-context drop-in Debian's layout has, `modules-enabled/`.
keel uses the drop-in: `90-keel-streams.conf` sorts after
`50-mod-stream.conf`, so the module is loaded before the block that needs
it, and it holds nothing but a `stream {}` that includes
`streams-enabled/*`. The two directories mirror `sites-available` and
`sites-enabled`, so an operator's hand-written stream servers have the
same obvious place and coexist the same way. An empty `stream {}` is
valid, so the file is always there and nothing moves when the first stream
site is added.

**Which files are keel's.** A file is keel's when its name starts with
`keel-` **and** its first line is keel's header:

```
# keel: rendered from /etc/keel/instance.yaml, web.sites.erp, spec digest <sha256>; do not edit
```

Both, because each alone is weak: a name can be chosen by hand, a header
can be copied. keel writes, replaces and removes only files that meet both
(and the links in `*-enabled/` that point to them). A file named `keel-*`
without the header is not overwritten: the step refuses and names it,
since it is the operator's work in keel's namespace. Every other file,
and every link that does not point to a keel file, is the operator's and
is never touched. Site names are therefore also file names, which rule 1
already constrains.

**Debian's default site.** `nginx-common` links
`sites-enabled/default` to `sites-available/default`, which takes
`default_server` on port 80 (`listen 80` and `[::]:80`). Nginx refuses two
`default_server` on the same address and port, so keel's
`keel-default.conf` and Debian's cannot both be enabled. keel removes the
**link** `sites-enabled/default`, and only the link, only when all of this
holds:

- `keel-default.conf` is being enabled and takes `default_server` on that
  port;
- the link points to `/etc/nginx/sites-available/default`;
- that file is still the one `nginx-common` shipped, by its conffile
  checksum (`dpkg-query -W -f='${Conffiles}' nginx-common`).

`sites-available/default` is left in place, and the removal is recorded in
`/var/lib/keel/web/`, so removing the last keel `http` site restores the
link. When Debian's file was edited, or another file of the operator's
takes `default_server` on 80 or 443, keel leaves it alone and renders
`keel-default.conf` without `default_server` on that port, and `diff` and
`inspect` say the default server is the operator's; unknown names then
reach the operator's default, not keel's refusal.

**Coexisting with hand-written sites.** `nginx -t` checks the whole
configuration, the operator's files included. When it fails in a file
keel does not own, the step fails without changing anything and says the
error is outside keel's files. A `server_name` of a keel site that a file
of the operator's also serves makes Nginx warn and ignore one of them;
keel treats that warning as a failure, naming both files.

`apply --system` gains a `web` step, after `tls.acme` (so a certificate
issued in the same run is used) and before `network`:

1. Render keel's files in memory. Identical to keel's files on disk:
   nothing more, the step says `unchanged`.
2. Test: copy `/etc/nginx` into a scratch directory, put the rendered
   files and links in it, and run `nginx -t` in a private mount namespace
   where the copy is bind-mounted over `/etc/nginx` (`unshare --mount`),
   because Debian's includes are absolute paths. The live tree is not
   touched. Refused: the step fails with Nginx's output.
3. Install: keel's current files and links are copied to
   `/var/lib/keel/web/previous/`, then the new ones are written (each by
   rename), the links made, and keel files no longer declared removed with
   their links. `nginx -t` on the live tree; refused: keel's previous
   files and links are put back, and the step fails.
4. `systemctl reload nginx.service` (a reload, never a restart). Failed:
   put the previous files back and reload them.
5. Write the Monit file and the firewall rules for `tcp` and `udp` sites,
   derived as 0041 derives them, the site's `port` and `expose` taking the
   place of a manifest `listen`.

Keel Web never changes the network: a site cannot bind a port of the
chain, and the firewall only gains the ports of stream sites, so 0018's
window does not apply (0019's rule holds the same way).

`keel web render [--spec FILE] [--site NAME] [--output DIR]` prints or
writes keel's files without applying them, and `keel web test [--spec
FILE]` runs step 2. They are the code `apply` uses, so the preview is what
will be applied.

`keel diff` compares the render of the spec with **keel's files only**:
a hand edit of a keel file, a keel file missing, or a keel file left for a
site no longer declared is drift; the operator's files are never drift.
`keel inspect` writes `web` from the copy of the last applied section that
`apply` keeps in `/var/lib/keel/web/applied.yaml`, reported as inferred
from that copy, and lists every enabled site and stream file that is not
keel's as **present, not declared**, with its file and the names it
serves (read from `nginx -T`), without writing it into `web.sites`.

## The console screens

A new top-level confconsole menu, **Keel Web**
(`plugins.d/Keel_Web/`), present when `keel-overlay-nginx` is installed.
Every screen edits a staged copy of the spec; nothing is written until
the last screen.

1. **Sites.** The list: name, mode, canonical name, certificate state
   (issued, expiring, pending, not needed), maintenance mode. Below it,
   read only, the sites Nginx serves from files that are not keel's
   (`inspect`'s "present, not declared"), with their file, so the
   operator sees the whole server; the screen never edits them. Entries:
   Add site, a site to edit, Upstreams, Settings, Apply.
2. **Add site: name and mode.** A name, then the mode from a menu. The
   version 2 modes are listed, and refused with "version 2" until then.
   Choosing `tls-passthrough` shows, and asks to acknowledge: "TLS reaches
   the backend intact. Coraza, Anubis, security headers, the maintenance
   page and per-path rules do not apply to this site. The backend must
   protect itself." When a file that is not keel's listens on TCP 443,
   the screen says the passthrough cannot be added until that site moves,
   and names the file.
3. **Names.** The canonical name and the others; for `http`, `www`
   handling and old names to redirect.
4. **Backend.** For `http`: the routes, one line each (path, upstream and
   port, WebSocket, stream, max body, allowlist), with "Add route" and a
   shortcut per common case (WebSocket path, long polling path). For a
   passthrough: the upstream and port, and "does the backend accept the
   PROXY protocol?". Each upstream can be picked or created in place
   (servers, backup, check).
5. **Certificate** (`http` only). The certificates that cover the names,
   "request a certificate for these names" (the hand-off above), or
   "self-signed for now".
6. **Protection** (`http` only). WAF `enforce`, `detect` or `off`, and
   Anubis on or off for this site under the machine's one Anubis policy,
   each shown only when its overlay is enabled and otherwise explained; HSTS; frame options; CSP; the maintenance mode and
   its bypass.
7. **Extra** (advanced, `http` only). The allowlisted directives, one per
   line, checked as they are typed against the same list keel uses.
8. **Review.** A summary of the site in words, the files it will write
   (`sites-available/keel-<site>.conf` and its link, and
   `conf.d/keel-web.conf` or the stream files when they change), then
   **the generated configuration** (`keel web render --spec <staged>
   --site <name>`), scrollable, with the lines that differ from what runs
   now marked. When enabling `keel-default.conf` will remove Debian's
   `sites-enabled/default` link, the review says so.
9. **Test.** `keel spec validate` on the staged spec, then `keel web test
   --spec <staged>`, and their output, `nginx -t` included. A failure
   returns to the review with the message; nothing has been written.
10. **Apply.** Commits the staged spec, runs `keel spec apply
    --system-only --non-interactive --skip-network`, and shows the web
    step's lines. If the step failed, keel has already kept the previous
    Nginx configuration; the screen restores the previous spec too and
    says so, so the file and the running server agree.

**Settings** holds `web.listen.ipv4` (on, with "IPv6 only" as the
opt-out), `web.real_ip` and `web.logs`, with the same review, test and
apply; `header` is not offered while a passthrough site exists. Removing a site asks, then goes through
review, test and apply like any change.

Headless equivalent: edit `web` in `/etc/keel/instance.yaml`, `keel web
test`, `keel spec apply --system-only`.

## Sites an application declares

The manifest format already has the application's `web` section
(docs/manifest-v1.md, appendix): `routes` with `to: php` or `to: {port:
N}` and `websocket: true`, `max_body` and `health`. This note makes it the
source of a site's routes:

```yaml
# spec, on a machine that runs the Odoo appliance
web:
  sites:
    - name: erp
      mode: http
      names: [erp.example.org]
      routes: manifest
      tls: {certificate: erp}
```

| Owner | Says |
| --- | --- |
| The manifest (fact) | The paths, which port each goes to, which are WebSockets or streams, the body size the application needs, its health path |
| The spec (choice) | That the application is served, under which names, with which certificate and protection, whether through an upstream on other nodes, and any extra routes |

`routes: manifest` resolves to the manifest's routes, each `to: {port:
N}` becoming the loopback upstream, or the upstream named by
`app_upstream: <group>` when the application runs on other nodes, and
`to: php` becoming the PHP-FPM pass of Keel PHP (a template, not an
`extra`). The spec may add routes after them; it cannot remove or change
one, for the reason 0041 gives for inheritance: the application was tested
with them. `max_body` is the larger of the two. The emitted spec writes
`routes: manifest`, not the routes, so nothing is declared twice; `keel
web render` shows them resolved.

A manifest route that needs a field the manifest format does not have
(`stream: true` for long polling) is a key for `manifest_version: 2`; in
version 1 the operator adds that route in the spec.

## Validation rules

`keel spec validate`, every error at once:

1. Site and upstream names match `[a-z][a-z0-9-]*`, at most 32, and are
   unique; unknown keys are errors at every level.
2. `mode` is one of the five; a version 2 mode, and every version 2
   field, is refused with "version 2" until the keel that implements it.
3. Every name is a valid host name or a leading-label wildcard, and
   belongs to exactly one site (including `www` and `redirect_from`
   names).
4. A stream site's `port` is not 80, not 443, not a `(port, protocol)` of
   the resolved manifest chain whatever the states (0041, rule 17), and
   unique among sites.
5. Every `to.upstream` names a group; every server address is a literal
   IPv6 or IPv4 address; a group does not mix a VIP of 0029 with real
   addresses of the same set.
6. `tls.certificate` is `default` or a name in `tls.acme.certificates`,
   and that certificate's domains cover every name the site answers
   under (warning only while it is pending).
7. A wildcard in `certificates[].domains` requires `dns-01`; `dns-01`
   requires `tls.acme.dns`.
8. `real_ip.trusted` is non-empty unless `direct`; `header` with a
   passthrough site is refused.
9. `protect.waf` other than `off` requires the `coraza` overlay enabled,
   `protect.anubis: true` the `anubis` overlay.
10. `static` directories are under `/var/www/keel/<site>/`; route paths
    start with `/` and carry no regular expression.
11. `extra` follows the allowlist and the argument rules.
12. `routes: manifest` requires an application manifest with a `web`
    section.

## Version 1 and version 2

| | Version 1 | Version 2 |
| --- | --- | --- |
| Modes | `http`, `tls-passthrough` (with the stream front) | `tls-terminate-tcp`, `tcp`, `udp` |
| Routing | routes, WebSocket, SSE and long polling, static directories, `routes: manifest` | gRPC |
| Upstreams | groups, loopback and mesh, `backup`, passive failover, Monit checks | the VIP for `tcp` sites (it arrives with them) |
| Real IP | `direct`, `proxy_protocol`, `header`, PROXY across every internal hop | |
| Redirects | HTTP to HTTPS, `www`, old names | |
| Certificates | named certificates through the Certificate feature, HTTP-01 and DNS-01, reload on renewal | mTLS (`client_certificates`) |
| Security | HSTS, CSP, frame options, nosniff, referrer policy, IP allowlist per path, WAF mode per site, Anubis per site, `default_server` refusal | `limit_req`, `basic_auth` |
| Other | maintenance page, gzip, per-site logs, IPv6 first with IPv4 on by default, `extra`, one global Anubis policy with a per-site opt-out | `proxy_cache`, HTTP/3, per-site Anubis policies |

Where the requirements named an item for a version, it is there. The
items they did not place: the IP allowlist, gzip, SSE, logs, `extra` and
`routes: manifest` are in version 1 because each is small and the
examples need them; gRPC waits for version 2 with the other protocols.

## First implementation

In order, in Phase 3 (tracker#46), after 0041's steps 5 and 6
(`keel-overlay-nginx` exists). Each step is done only when its criterion
holds on a built image or package, not on a machine assembled by hand.

| # | Repository | Work | Done when |
| --- | --- | --- | --- |
| 1 | keel | The `web` schema and rules 1 to 12, `tls.acme.certificates` and `tls.acme.dns`, with no renderer yet | Every example of this note validates as a fixture; each rule has a fixture it refuses; coverage per 0003 |
| 2 | keel | `keel web render` and `keel web test`: the templates for `http` sites (routes, WebSocket, SSE, upstreams, real IP, redirects, headers, maintenance, logs), `keel-default.conf`, `conf.d/keel-web.conf` and the stream front with passthrough, every listener on `[::]` then `0.0.0.0` | Golden files for each example, with `ipv4` on and off; `nginx -t` accepts every rendered set, laid into trixie's stock `/etc/nginx` (nginx 1.26.3, `libnginx-mod-stream`) beside a hand-written site, in CI; every rendered file carries the header; a set with an `extra` outside the list is never produced |
| 3 | common | `keel-overlay-nginx` gains `conf.d/keel-health.conf`, `modules-enabled/90-keel-streams.conf`, the `streams-available/` and `streams-enabled/` directories, the maintenance page, the CrowdSec acquisition, `deploy.d/50nginx`, the tmpfiles entry for `/run/nginx`, and `Depends: libnginx-mod-stream`; `nginx.conf` stays Debian's | On Core, installed over a stock nginx: `nginx.conf` is byte for byte `nginx-common`'s, `nginx -t` passes with the empty `stream {}`, Debian's default site still answers; `/keel-health` answers 204 on the loopback only; CrowdSec reads a `keel-*.access.log` line as an nginx event |
| 4 | keel | The `web` step of `apply --system`: ownership rule, test in a mount namespace, install and rollback, Debian's default link, `diff` and `inspect` | On a container with a hand-written site in `sites-enabled/`: the Odoo example applied against a stub backend proxies `/` and upgrades `/websocket` over IPv6 and IPv4; the hand-written site still answers and its file is unchanged; Debian's `default` link is removed and comes back when the last keel site is removed, and an edited Debian default is left in place; a second apply is `unchanged`; a spec whose render `nginx -t` refuses leaves every file and the served pages as they were; adding the passthrough example links the front, and the stub's log shows the client's address, not `unix:`; it is refused, naming the file, while the hand-written site listens on 443; `diff` reports a hand edit of a `keel-*` file and nothing for the operator's; `inspect` lists the hand-written site as present, not declared |
| 5 | confconsole | The Certificate changes 1 to 7 | With Let's Encrypt's staging CA: two named certificates and `default` issued on one machine, each with its own files; an HTTP-01 issuance while a site is served drops no request of a client polling it; a renewal forced by `RENEW_DAYS` reloads Nginx and a WebSocket open across it survives; a wildcard with `http-01` is refused on screen |
| 6 | new packaging repository, keel, confconsole | lexicon as a Keel `.deb` (change 8), built from source with the provider libraries it needs, into the testing track (0039); `dns_01.py` installs nothing; `apply` accepts DNS-01 through the spec | The package builds in the Keel repository; a wildcard certificate is issued from the staging CA through a test DNS provider, on a machine with no public port 80 and no route to PyPI, and no venv exists under `/usr/local/src` |
| 7 | confconsole | The Keel Web menu, screens 1 to 10, and the hand-off to the Certificate screen | Driven headless in the confconsole test harness: adding the Odoo site produces the same spec as the example; the list shows a hand-written site as not keel's and offers no edit of it; the review shows the render and the files it writes; a failing `nginx -t` is shown and writes nothing; a failed apply restores the previous spec |
| 8 | keel-web | The image | Phase 3's criterion of tracker#46 still holds, and on the built image the Odoo and two-upstream examples serve, fail over when the first server stops, and show the maintenance page with 503 when both do |
| 9 | keel, manifest | `routes: manifest`, with the first application built from a manifest (Phase 4) | On the Odoo or WordPress appliance, a site with `routes: manifest` renders the manifest's routes, and the spec that declared it contains none of them |

Version 2 follows as its own steps once version 1 has run on a real
machine.

## What this amends

- **0030**: Keel Web gains sites, the stream module and the `extra`
  allowlist, in Debian's standard Nginx layout beside any hand-written
  site; the pipeline order is unchanged, and Anubis stays behind Nginx
  (the internal unix hop), with one policy.
- **0041 and docs/manifest-v1.md**: the firewall and Monit derivations
  gain the spec's stream sites and upstream checks as inputs; the `nginx`
  overlay manifest declares `443/udp` when HTTP/3 lands (version 2); the
  application `web` section becomes the source of `routes: manifest`, and
  `stream: true` on a route is noted for `manifest_version: 2`.
- **0027**: the emitted spec carries `web` and the certificate list,
  written out.
- **docs/spec.md and docs/apply.md in keel**: `web`, `tls.acme.certificates`
  and `tls.acme.dns`; `dns-01` stops being refused once `dns` is set; the
  `web` step.
- **confconsole's Let's Encrypt documentation**: multiple certificates,
  Nginx not stopped, `deploy.d`, and the cron without `--force`.

## Resolved (maintainer, 2026-09-30)

The maintainer decided the note and agreed with the rest, with two
changes, and answered the open questions as recommended. The text above
already reflects all of it.

- **Nginx's standard layout, not `/etc/nginx/keel/`.** Sites are rendered
  to `sites-available/` with links in `sites-enabled/`; keel owns only its
  own files, named `keel-<site>.conf` and marked by a header, both
  required; hand-written sites coexist and are left alone; `diff` reports
  drift only on keel's files and `inspect` reports the others as present
  but not declared. The stream side uses `streams-available/` and
  `streams-enabled/`, included by a `stream {}` block in
  `modules-enabled/90-keel-streams.conf`, the only main-context drop-in
  Debian's layout has, so `nginx.conf` stays as `nginx-common` ships it.
  Debian's `sites-enabled/default` link is removed only when
  `keel-default.conf` takes `default_server` on the same port and Debian's
  file is unmodified, and it is restored with the last keel site. This
  replaces the proposal's `/etc/nginx/keel/`, owned whole by keel.
- **IPv4 on by default, IPv6 first.** Every listener is written on `[::]`
  first and `0.0.0.0` second; `web.listen.ipv4: false` is the operator's
  opt-out. This replaces the proposal's IPv4 off by default.
- **lexicon is packaged as a Keel `.deb`**, never installed with pip at
  run time.
- **The stream front runs only while a passthrough site exists.**
- **One global Anubis policy in version 1**, with `protect.anubis: false`
  as the per-site opt-out; per-site policies are version 2.
- **Header-based real IP is refused behind the stream front**; only the
  PROXY protocol is trusted there.
- **The items the requirements did not place** stay where the proposal
  put them: the IP allowlist, gzip, SSE, logs, `extra` and `routes:
  manifest` in version 1, gRPC in version 2.
