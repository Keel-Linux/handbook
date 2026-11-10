# 0079: Port 80 is the application's until a certificate authority's certificate

Date: 2026-11-06
Status: **decided by the maintainer, 2026-11-06** ("if there is an app on
top, port 80 used by keel-web must be used by the app; for apps that do
not control the domain it is a way to see that everything works, and
sometimes only the certificate is missing"). The redirect after ACME and
the Anubis cookie rule are decided by the coordinator under the
maintainer's delegation. Implemented in keel-web 0.4.0 (keel-web#26).

## What was found

On a WordPress node (2026-11-06): in the cloud modes port 80 answered 301
to HTTPS for every path, where the first boot's certificate is
self-signed, so a browser showed a warning and not the site. On the
loopback, port 80 belonged to keel-health.conf, which answers
`/keel-health` and 404 for every other path: keel-laravel's first boot
waited on `http://127.0.0.1/` and failed on BR1 and BR2.

## Decided

1. Port 80 of Keel Web's default site serves the application on top, or
   keel-web's placeholder when there is none. While the machine's
   certificate is self-signed (the certificate of the first boot, or no
   certificate for a domain yet), port 80 serves the same content as 443:
   the routes of `/etc/nginx/keel-default.d/`, and in the cloud modes
   Anubis and Coraza. There is no redirect. An application that does not
   control its domain name can so be seen to work before the name points
   to the machine.
2. When the certificate is one that a certificate authority issued
   (ACME), port 80 answers 301 to the same URL on HTTPS, in the simple
   mode and in the cloud modes. `/.well-known/acme-challenge/` stays on
   port 80, so that the certificate can be renewed. No password of a
   login goes over plain HTTP once real HTTPS exists.
3. A certificate is self-signed when its subject is its issuer and its
   authority key identifier is absent or is its own subject key
   identifier, the rule of keel's `inspect/certificate.py`.
4. The switch is automatic: `keel-web-http.path` watches
   `/usr/local/share/ca-certificates/cert.crt`, and `keel-web-http.service`
   runs `/usr/lib/keel-web/http-mode` at boot, at each start of nginx and
   when the certificate changes. It links or removes
   `/etc/nginx/keel-web/http-redirect.conf`, tests with `nginx -t`,
   reloads nginx, and puts the link back on a failure.
5. While the certificate is self-signed, Anubis sets its cookies without
   `Secure` (`COOKIE_SECURE=false`, `COOKIE_SAME_SITE=Lax`). A browser does
   not keep a `Secure` cookie from a plain HTTP page, so it would never
   pass the challenge. The Anubis pass cookie is not a credential: it
   only says that the browser solved a challenge. When the certificate
   authority's certificate is in place, the cookies are `Secure` again.
6. The loopback addresses of port 80 belong to the default site and never
   redirect: `http://127.0.0.1/` reaches the application for checks on
   the machine, and `/keel-health` answers 204 there for the monitor.
7. Every commissioning contract (0075) of an application on Keel Web
   checks that `http://127.0.0.1/` answers the application and that
   `/keel-health` answers 204.

## What it amends

- 0042, "Redirects", "HTTP to HTTPS", and the field `redirect_http`: for
  Keel Web's default site the redirect applies only once a certificate
  authority's certificate is in place.
- The simple mode now redirects port 80 after ACME, which it did not do
  before.

## Not decided here

- HSTS stays off until a certificate authority's certificate is in place
  (0042 tls.hsts, tracker#51).
- Sites that keel renders from `web.sites` (0042) do not change.
- A real browser on `http://<address>/` of a cloud node through Anubis is
  still to be proven in a commissioning run: CI uses stand-ins.

## Amendment 2026-11-10: keel-ntfy keeps the redirect on port 80

Decided by the maintainer, 2026-11-10 ("sim tudo", question a).

**The exception.** keel-ntfy does not follow items 1, 6 and 7. Port 80
never serves ntfy, also on the loopback and with the self-signed
certificate. Every request on port 80 gets a 301 to the same URL on
HTTPS, except on two paths that stay on port 80:

- `/.well-known/acme-challenge/`, which keel-web serves for ACME HTTP-01
  (keel-ntfy 19.0-6).
- `/keel-health`, which answers 204 on port 80 and on port 443 for the
  monitor.

**The reason.** The clients of ntfy are the phone application and keel,
not browsers (0063). Access is closed by default, so a publish or a
subscription sends a credential: a password or a token. An answer in
clear text must not exist, also with the self-signed certificate.
keel-ntfy 19.0-2 closed port 80 for this reason: the API was open in
clear text on the external address. Item 1 shows the application before
the name points to the machine, but a client shows no page.

**The contract.** The commissioning contract of keel-ntfy (0075) checks
that `http://127.0.0.1/v1/health` answers 301 and that
`https://127.0.0.1/v1/health` answers 200, in place of item 7. It
checks `/keel-health` 204 on port 80 and on port 443.

Every other application on Keel Web follows 0079 with no change.
