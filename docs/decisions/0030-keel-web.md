# 0030: Keel Web: Nginx, Coraza and Anubis

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-008).

## Decision

**Keel Web** is an appliance of its own, useful alone and the base of
every web appliance: Nginx, Coraza (a WAF as an Nginx module) and Anubis
(proof of work).

- **Simple installation:** Nginx only.
- **Advanced installation:** Coraza and Anubis configured.
- **The pipeline, in order:** CrowdSec bans first; Nginx terminates TLS,
  serves static files and runs Coraza inline; Anubis sits behind Nginx;
  then the application.
- **Anubis is never at the edge.** Googlebot and Bingbot (and Yandex where
  relevant) are exempt.
- **Apache is retired** as the default web server, and migrated appliance
  by appliance.

## What this amends

- **0013, "The catalog shape"**: the `apache-php` layer under LAMP and LAPP
  is superseded; Keel PHP is Keel Web plus PHP-FPM (0036).
- **0022** (open, handbook#23): its LNPP already puts nginx in front of
  Odoo; that nginx is now Keel Web.
- **0019** is unaffected (Webmin and the network).

## Review notes (open points for the maintainer)

- [ ] **The Coraza Nginx connector is still experimental.** The mature
  alternative with the same OWASP Core Rule Set is ModSecurity v3 with the
  Nginx connector, which Debian 13 ships: `libmodsecurity3t64
  3.0.14-1+deb13u1`, `libnginx-mod-http-modsecurity 1.0.3-2+b2`,
  `modsecurity-crs 3.3.7-1+deb13u2` (CRS 3.3; Coraza is usually run with
  CRS 4). The other way to keep Coraza is as a proxy in front of the
  application (coraza-caddy or coraza-proxy); Debian's `caddy 2.6.2` does
  not include the Coraza module, so that too would be a build of ours.
- [ ] **Not in Debian 13 at usable versions**, measured with
  `apt-cache policy` on this Debian 13.7 machine, 2026-09-30: Anubis
  (absent), Coraza (absent), Garage (absent, see 0038), CrowdSec
  (`1.4.6-10+b4`, well behind upstream). Each needs a Keel package in the
  Keel repository under 0039, built and signed like the rest, which keeps
  0013's claim that every image rebuilds from our own archive.
