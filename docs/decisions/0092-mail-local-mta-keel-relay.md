# 0092: Applications send mail to the local MTA, and Keel owns the relay

Date: 2026-11-14
Status: **proposed.** The maintainer decided the direction: each
application sends to the local MTA, and the Postfix of the node decides
where the mail goes. This note proposes how Keel owns that setting. The
test on BR1 is in `evidence/2026-11-14-mail-local-mta-relay.md`. Nothing
in this note is built.

## What was asked

Each application has its own mail settings today, or none. Loops writes
`MAIL_MAILER=log`, so it sends no mail and refuses each registration
(0086). The maintainer decided one setting for the node, for all
applications: each application sends to `127.0.0.1:25` with no password.
Postfix then does direct delivery, or sends to an external smart-host, or
to an internal relay. The plan: a key in the Keel spec for the relay, the
secret in `/etc/keel/secrets`, and the confconsole screen "Mail Relaying"
edits that key. A replica of a pair then gets the same setting.

## What is true today

Tested on BR1 on 2026-11-14 with WordPress 19.0-22, LNMP 19.0-7 and Core
19.0-13 (the evidence file):

- Each image has Postfix 3.10 active. It listens on `127.0.0.1:25` only.
  Another machine cannot connect to port 25. The node is not an open
  relay. Nothing listens on `::1:25`.
- A message to `127.0.0.1:25` with no authentication is accepted and
  delivered. WordPress uses `/usr/sbin/sendmail`, which also goes to
  Postfix.
- The confconsole script `mail_relay.sh` makes a working relay with SASL
  and STARTTLS. It has defects:
  - The xtrace of `bash -x` writes the password to standard error.
  - `smtp_tls_security_level = may` sends the password in clear text to a
    smart-host or a man in the middle that offers no STARTTLS (tested
    with `tcpdump`). `encrypt` keeps the message in the queue and sends no
    credential.
  - The relay with no password turns TLS off, also when the relay offers
    STARTTLS.
  - `deconfigure` deletes each line that holds the word `relayhost`, also
    `sender_dependent_relayhost_maps` and comments.
  - `deconfigure` leaves `sasl_passwd.db` with the password in it.
  - `deconfigure` does not reload Postfix, so the old relay stays in use.
- The script edits only local files. No manifest names `/etc/postfix` as
  state. A relay made on the primary is not on the replica (read in code,
  the pair was not tested).
- `keel spec apply` does not remove a relay. Keel writes `main.cf` only
  for a host name change, and changes only `myhostname` and
  `mydestination`.
- The spec has no mail relay key. It has `app.email` and
  `security.alerts` only.
- `myhostname` is the short host name. The HELO name and the sender
  domain of each message are thus not an FQDN.
- `smtp_tls_security_level` is empty on the image. Direct delivery uses
  no TLS, also when the receiving server offers STARTTLS.

## Decision

### 1. Applications send to the local MTA

Each application sends mail to the Postfix of its node, in one of 2 ways:

- SMTP to `127.0.0.1` port 25, with no user, no password and no TLS;
- `/usr/sbin/sendmail`, which is the way of PHP `mail()`.

Use the address `127.0.0.1`, not the name `localhost`. Postfix does not
listen on `::1`, and a client that resolves `localhost` to `::1` fails.

The application never gets the address or the credential of a smart-host.
An application manifest has no mailer option: no SMTP host, port, user or
password, and no choice between "log", "smtp" and "sendmail". The layer of
the application writes the local setting at build or at first boot.

### 2. Postfix listens on the loopback only

Keel keeps `inet_interfaces` on the loopback. Postfix accepts mail only
from the node itself. `mynetworks` stays the loopback. A node never
relays for another machine. A Keel node that must be a relay for other
machines is a separate appliance, out of this note.

### 3. Keel owns the relay through the spec

A new top-level key `mail` holds the relay. When it is absent, or when
`relay` is `skip`, Postfix does direct delivery. The proposed shape
follows the spec style of `monitor.notify`: a secret is a reference
mapping, `{file: PATH}`, which `validate_secret` checks.

```yaml
mail:
  relay:
    host: smtp.example.org        # a name or an IP address
    port: 587
    user: keel@example.org        # optional
    password:                     # a secret reference, with user only
      file: /etc/keel/secrets/mail_relay_password
    tls: verify                   # verify | encrypt | may
```

Rules that validation applies:

- `host` is required. `port` is 1 to 65535, default 587.
- `user` and `password` come together or not at all.
- If `password` is set, `tls` must be `verify` or `encrypt`. Validation
  refuses `may` with a password.
- `tls: verify` is the default. It checks the certificate of the
  smart-host against the system certificate authorities. Use it for a
  public smart-host.
- `tls: encrypt` requires TLS but does not check the certificate. Use it
  for an internal relay with its own certificate.
- `tls: may` uses TLS when the relay offers it, and goes on with no TLS
  when it does not. It is permitted only with no password, for an
  internal relay that permits the node by its address.

The change in the code: `mail` joins `TOP_LEVEL_KEYS`, a new
`validate_mail.py` checks the section, and the password is masked as the
other secrets are (`MASK`).

### 4. What Keel writes into Postfix

`keel spec apply --system` converges the `mail` section. It sets each
value with `postconf -e`, and removes a value with `postconf -X`. It
never deletes lines by a pattern. It writes only these settings:

| Setting | Relay with password | Relay with no password | No relay |
|---|---|---|---|
| `relayhost` | `[host]:port` | `[host]:port` | removed |
| `smtp_sasl_auth_enable` | `yes` | removed | removed |
| `smtp_sasl_password_maps` | `hash:/etc/postfix/keel_relay_passwd` | removed | removed |
| `smtp_sasl_security_options` | `noanonymous` | removed | removed |
| `smtp_sasl_tls_security_options` | `noanonymous` | removed | removed |
| `smtp_tls_security_level` | `secure` or `encrypt` | `secure`, `encrypt` or `may` | `may` |
| `smtp_tls_CAfile` | system bundle, with `verify` | system bundle, with `verify` | removed |

The script of today writes an empty level for a relay with no password,
which turns TLS off. Keel never writes an empty level. With no password,
`may` sends no credential.

Keel makes `/etc/postfix/keel_relay_passwd` from the secret file, mode
0600 from the first byte, then runs `postmap`. When the relay goes away,
keel removes the file and its `.db`. After each change keel runs
`postfix reload`. The password is never an argument of a command and is
never in a log.

### 5. The confconsole screen edits the spec

The screen "Mail Relaying" asks for the host, the port, the user, the
password and the TLS level. It tests the values with STARTTLS required,
and with the certificate check for `verify`. Then it writes the `mail`
section into `/etc/keel/instance.yaml` and the password into
`/etc/keel/secrets/mail_relay_password` (0600), and runs
`keel spec apply --system-only`. The screen does not edit `main.cf`.
"Deconfigure" removes the `mail` section and the secret file, and runs
the same apply. `mail_relay.sh` is removed. The TurnKey text, the hub URL
and the `SendinBlue`/`Brevo` preset go away.

### 6. The replica gets the same relay

A pair has one mail setting. The `mail` section and its secret go to the
replica by the same path as the other values that both nodes share. Item
2 of the open questions decides the path.

### 7. The host name of the mail

When the spec has `instance.fqdn`, keel sets `myhostname` to it. The HELO
name and the default sender domain are then an FQDN, which smart-hosts
require. Item 3 of the open questions decides this.

## What each application must do

Each layer writes the local setting below. The values for the
applications other than WordPress are read in code or come from the
upstream default. They are not tested.

| Application | Setting in the layer | State |
|---|---|---|
| WordPress | PHP `mail()` to `/usr/sbin/sendmail`, no change. When the host of `siteurl` has no dot, set the From address from `instance.fqdn` (a must-use plugin with `wp_mail_from`). | tested: with `siteurl` `http://localhost`, `wp_mail()` fails today |
| Loops | `MAIL_MAILER=smtp`, `MAIL_HOST=127.0.0.1`, `MAIL_PORT=25`, no user, no password, no encryption, `MAIL_FROM_ADDRESS` from `app.email` or `instance.fqdn`. Replace `MAIL_MAILER=log` in `loops.sh`. | not tested |
| Laravel (user application) | The same values in the default `.env` that the layer writes | not tested |
| Nextcloud | `mail_smtpmode` `smtp`, `mail_smtphost` `127.0.0.1`, `mail_smtpport` 25, no authentication, no TLS | not tested |
| Odoo | `smtp_server` `127.0.0.1`, `smtp_port` 25, no user, `smtp_ssl` off | not tested |
| NodeBB | SMTP transport to `127.0.0.1:25` with no authentication, or sendmail | not tested |
| OJS | `[email]` with `smtp = On`, `smtp_server = 127.0.0.1`, `smtp_port = 25`, no authentication, or the default sendmail | not tested |
| ntfy | `smtp-sender-addr: 127.0.0.1:25` when the e-mail notices are on | not tested |

0089 applies: the mail setting of an application is in the layer of that
application. The core holds the relay only.

## Consequences

- One relay for each node, for each application and for the alerts of
  `security.alerts` and monit. A change of smart-host is one screen.
- The application never holds the relay password. A defect in an
  application cannot show it.
- `keel diff` can report a relay that a person made by hand in `main.cf`
  and that the spec does not declare.
- `mail_relay.sh` and its defects go away. Until the new screen exists,
  the present screen keeps its defects on each published image.
- A node with no relay does direct delivery with opportunistic TLS. Many
  receivers refuse direct mail from a residential or a cloud address.
  The relay is then necessary in practice.

## Open questions for the maintainer

Each question has a yes or no answer.

1. Is the top-level key `mail.relay` with the shape of item 3 correct?
2. Does the replica get the `mail` section and its secret file from the
   primary automatically?
3. Does keel set `myhostname` from `instance.fqdn`?
4. Is `tls: verify` the default, with `encrypt` permitted for an internal
   relay?
5. Does keel set `smtp_tls_security_level = may` for direct delivery on
   each node, also with no `mail` section?
6. Can an application use `/usr/sbin/sendmail` as well as SMTP to
   `127.0.0.1:25`?
7. Does a confconsole build fix the 3 defects that show a password
   (xtrace, the `.db` file left behind, TLS `may`) before the new screen
   exists?

## Tests before a release

The release of the `mail` section passes these tests on BR1, with an
evidence file (0053):

1. A node from each published image: Postfix listens on `127.0.0.1:25`
   only, and port 25 is closed from another machine on IPv4 and IPv6.
2. SMTP to `127.0.0.1:25` and `/usr/sbin/sendmail` deliver with no
   `mail` section.
3. A relay with a password and `tls: verify` to a smart-host with a
   certificate of a public certificate authority delivers. The HELO name
   is the FQDN.
4. A relay with `tls: encrypt` to a smart-host with no STARTTLS keeps the
   message in the queue, and a capture shows no AUTH.
5. A spec with a password and `tls: may` fails validation.
6. A relay with no password to an internal relay delivers, and uses TLS
   when the relay offers it.
7. Removal of the `mail` section brings back direct delivery at once, with
   no reload by a person. No `keel_relay_passwd` file and no `.db` file
   stay. Other lines of `main.cf` stay the same.
8. The confconsole screen writes the spec and the secret file, and
   `main.cf` changes only through `keel spec apply`.
9. A pair: the relay set on the primary is on the replica, and a message
   from the replica goes through the relay.
10. A scan of the logs, of the output of each command and of
    `/proc/*/cmdline` during the apply finds no password.
11. Each application of the table above sends one message (a password
    reset or a registration) that arrives at the smart-host.
