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

## Resolved (maintainer, 2026-09-30)

- **Coraza stays, as the Nginx module.** The decision stands. The risk
  that its Nginx connector is still experimental is recorded as an
  implementation task, not as a reason to change the decision: the
  connector is built, tested against the OWASP Core Rule Set in the Keel
  Web gate, and its maturity is watched. The fallbacks known today, if the
  task finds the connector unusable, are ModSecurity v3 with the same
  Rule Set (`libnginx-mod-http-modsecurity` 1.0.3 is in trixie) or Coraza
  run as a proxy (coraza-caddy, coraza-proxy); choosing one would be a new
  decision.

## Packages (checked 2026-09-30 against the Debian archive and WNPP)

| Piece | Debian | What Keel does |
| --- | --- | --- |
| nginx | in trixie | uses it |
| Coraza | no package and no ITP | packages it under 0039 |
| Anubis | not in Debian; ITP #1102132, being packaged; upstream publishes a `.deb` (v1.27.0) | packages it under 0039 |
| libnginx-mod-http-modsecurity | 1.0.3 in trixie | the fallback above, not used |
| crowdsec | 1.4.6-10 in trixie (upstream 1.8.1), with crowdsec-firewall-bouncer 0.0.25 | see 0029 |

Every Keel package is built and signed in the Keel repository like the
rest, which keeps 0013's claim that every image rebuilds from our own
archive. **Anubis is a candidate for Keel to contribute to Debian**,
through the existing Debian packaging effort (tracker#15), coordinating
with the owner of ITP #1102132 rather than packaging in parallel.
