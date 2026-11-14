# Evidence: the local MTA of a Keel image, and the confconsole mail relay

Date: 2026-11-14. Site: BR1 (hw12-br1). Status: draft. For decision 0092.

## Question

The maintainer decided the direction: each application sends mail to the
local MTA on `127.0.0.1:25` with no password. Postfix on the node then does
direct delivery, or sends to an external smart-host, or to an internal
relay. This test answers 8 questions on published images before the
decision note:

1. Is Postfix installed and active, on which addresses does it listen, and
   is port 25 closed to other machines?
2. Does Postfix accept a message on `127.0.0.1:25` with no authentication?
   Does WordPress reach Postfix with its default settings?
3. Does the confconsole script `mail_relay.sh` make a working relay to a
   smart-host with SASL and STARTTLS?
4. With `smtp_tls_security_level = may`, does the client send the password
   in clear text when the smart-host has no STARTTLS? With `encrypt`, does
   the client keep the message and send no credential?
5. Does a relay with no password work (internal relay, permitted by
   `mynetworks` on the relay)?
6. Does `mail_relay.sh deconfigure` bring back direct delivery, and does
   its loose `sed` remove other lines?
7. Is a relay that is made on the primary of a pair also on the replica?
8. Does `keel spec apply` or a keel step write `/etc/postfix/main.cf` and
   remove a relay that a person made?

Each result below says if it was **tested** on BR1, **read in code**, or
**not tested**.

## Machines

All CTs are on BR1: unprivileged, `nesting=1`, 2 cores, bridge `vtnet88`
tag 5, nameserver `2606:4700:4700::1111`, rootfs on `local-lvm`. Each CT
got an instance description in `/etc/keel/instance.yaml` and fresh secret
files before its first boot (the method of the 2026-11-13 upgrade test).
Each first boot completed with `0 failed` (log 02). The template sha512 was
not compared with the mirror in this test.

| CT | Template on BR1 | Mode | Role in the test |
|---|---|---|---|
| 9470 | `debian-13-keel-wordpress_19.0-22` | simple | client, WordPress checks, internal relay client |
| 9471 | `debian-13-keel-lnmp_19.0-7` | simple | client of the smart-host, deconfigure, keel spec apply |
| 9472 | `debian-13-keel-core_19.0-13` | simple | Q1 checks, then the test smart-host |

Versions on the images: `postfix` 3.10.13-0+deb13u1,
`libsasl2-modules` 2.1.28, `keel` 0.23.96 (9471). The script
`/usr/lib/confconsole/plugins.d/Mail_Relaying/mail_relay.sh` on the image
has the same sha256 as `Keel-Linux/confconsole` `plugins.d/Mail_Relaying/`
(log 10).

The test smart-host (9472, after the Q1 checks): `dovecot-core` 2.4.1 for
SASL only (no IMAP or POP3), one account `relayuser` with a SHA512-CRYPT
hash, Postfix on 25 and 587 on all addresses, a self-signed certificate,
the submission service with `permit_sasl_authenticated,reject`, local
mailbox `/var/mail/mailtest` for `mailtest@mr-relay.example.test`
(script `smarthost_setup.sh`, log 30).

Secret handling: the relay password was made on 9472 and copied to 9471
by a pipe on the BR1 host. No command printed it. Each script output was
masked before it went to a log. A scan of all logs and scripts with each
test password and each `/etc/keel/secrets` file found 0 matches (log 90).

## Results

### Q1. Postfix on a published image (tested, logs 10, 11, 12)

The same result on WordPress 19.0-22, LNMP 19.0-7 and Core 19.0-13:

- Postfix is installed and active. The master process belongs to
  `postfix.service`. `postfix@-.service` is inactive, although
  `common/conf/turnkey.d/postfix-local` enables it.
- `ss -ltnp`: one socket, `127.0.0.1:25`. Nothing on `::1:25`, and a
  connection to `::1` port 25 is refused. `/etc/hosts` maps `localhost` to
  `127.0.0.1` only, so a client that resolves `localhost` gets
  `127.0.0.1`.
- `postconf`:

  | Setting | Value |
  |---|---|
  | `inet_interfaces` | `localhost` |
  | `inet_protocols` | `all` |
  | `mynetworks` | `127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128` |
  | `myhostname` | the short host name (`mr-wp`), not the FQDN |
  | `myorigin` | `$myhostname` |
  | `mydestination` | `$myhostname, localdomain, localhost, localhost.localdomain, localhost` |
  | `relayhost` | empty |
  | `smtpd_relay_restrictions` | `permit_mynetworks permit_sasl_authenticated defer_unauth_destination` |
  | `smtp_tls_security_level` | empty (no TLS on direct delivery) |
  | `smtpd_tls_auth_only` | `yes` |

- From 9472, a TCP connection to port 25 of 9470 and 9471, on IPv4 and
  on IPv6, is refused. The node is not an open relay, because no other
  machine can connect.
- The nftables rule set of the image is empty (policy accept). Port 25 is
  closed only because Postfix listens on the loopback.

### Q2. Local submission with no authentication (tested, logs 20, 21)

- SMTP to `127.0.0.1:25` with no AUTH: `250 2.0.0 Ok: queued`. The server
  offers no STARTTLS and no AUTH on this port. Postfix delivered at once:
  to `root@localhost` through the alias `root: admin@example.org`
  (`security.alerts`), and to `someone@example.net` by direct delivery.
  Both bounced with `nullMX`, which is correct for the example domains.
- WordPress does not use SMTP. PHP has
  `sendmail_path = /usr/sbin/sendmail -t -i`, so `wp_mail()` goes to
  Postfix through `pickup`. PHP `mail()` returns `true` and Postfix logs
  the message.
- **Defect, tested:** with the default settings of a simple-mode node,
  `wp_mail()` returns `false` and Postfix gets nothing. The error is
  `Invalid address: (From): wordpress@localhost`. The cause is the
  `siteurl` `http://localhost` (no `app.domain` in the description).
  WordPress makes its From address from the host of `siteurl`, and
  PHPMailer refuses a domain with no dot. With a From address that has a
  real domain (filter `wp_mail_from`), `wp_mail()` returns `true` and
  Postfix logs the message.

### Q3. `mail_relay.sh` to a smart-host with SASL and STARTTLS (tested, logs 30, 31, 32)

Command, as confconsole runs it:
`mail_relay.sh 2804:710:d0:5:be24:11ff:febb:74fe 587 relayuser PASSWORD`.

- The script ended with exit 0. It added these lines at the end of
  `main.cf`:

  ```
  relayhost = [2804:710:d0:5:be24:11ff:febb:74fe]:587
  smtp_sasl_auth_enable = yes
  smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
  smtp_sasl_security_options = noanonymous
  smtp_tls_security_level = may
  header_size_limit = 4096000
  ```

  `sasl_passwd` and `sasl_passwd.db` are `0600 root`. A bracketed IPv6
  address works as `relayhost`.
- A message to `127.0.0.1:25` went to the smart-host:
  `status=sent (250 2.0.0 Ok: queued as A03FD833)`. The smart-host log
  shows `Anonymous TLS connection established ... TLSv1.3` and
  `sasl_method=PLAIN, sasl_username=relayuser`. The message is in
  `/var/mail/mailtest`. Headers:

  ```
  Return-Path: <app@mr-lnmp.example.org>
  Delivered-To: mailtest@mr-relay.example.test
  Received: from mr-lnmp (unknown [IPv6:2804:710:d0:5:be24:11ff:fe04:e547])
  	by mr-relay (Postfix) with ESMTPSA id A03FD833
  Received: from mr-lnmp.example.org (localhost [127.0.0.1])
  	by mr-lnmp (Postfix) with ESMTP id 3341EA64
  From: app@mr-lnmp.example.org
  Subject: q3 via smart-host TLS+SASL
  Message-Id: <20261114121346.3341EA64@mr-lnmp>
  ```

  The HELO name and the Message-Id domain are the short host name
  `mr-lnmp`. Many public smart-hosts refuse a HELO name that is not an
  FQDN. This test did not try a public smart-host.
- **Defect, tested:** the script starts with `#!/bin/bash -ex`. The xtrace
  output has the password in clear text in 4 lines of standard error, for
  example `+ configure_postfix HOST 587 relayuser [masked]` and
  `+ password=[masked]` (log 31, masked). `mail_relay.py` captures standard
  error and shows it in a message box when the script fails.

### Q4. TLS `may` against a smart-host with no STARTTLS, then `encrypt` (tested, logs 40, 41)

Step a. The smart-host submission service got
`smtpd_tls_security_level=none` and `smtpd_tls_auth_only=no`. Thus it
offers AUTH and no STARTTLS, which is what a man in the middle that
removes STARTTLS shows. The client kept `smtp_tls_security_level = may`.

- The client delivered the message: `status=sent`.
- Primary proof, the smart-host log:
  `sasl_method=PLAIN, sasl_username=relayuser` and
  `disconnect ... ehlo=1 auth=1 mail=1 rcpt=1 data=1 quit=1`. There is no
  `starttls=1`.
- Second proof, `tcpdump` on port 587 of the smart-host, read by
  `pcap_auth.py`. The script prints no credential, only a yes or no. The
  client sent `AUTH PLAIN` with 48 characters of base64. The base64 holds
  the test password in clear text: `True`. The capture has no TLS
  handshake record. Two lines of the script output are not client
  commands: the 5-character `AUTH PLAIN` match is the
  `250-AUTH PLAIN LOGIN` line of the server, and `STARTTLS` is a word in
  the Subject line of the test message.
- Result: with `may`, a smart-host or a man in the middle that does not
  offer STARTTLS gets the password in clear text.

Step b. Same smart-host, client `smtp_tls_security_level = encrypt`:

- The message stays in the queue:
  `status=deferred (TLS is required, but was not offered by host ...)`,
  `dsn=4.7.4`.
- The smart-host log: `ehlo=1 quit=1 commands=2`. The capture has no AUTH
  from the client. No credential left the client.
- After STARTTLS came back on the smart-host, `postqueue -f` delivered the
  message with TLS 1.3 and SASL.
- `encrypt` accepted the self-signed certificate. `encrypt` stops a
  passive reader. It does not stop an active man in the middle with its
  own certificate. Only `secure` or `verify` checks the certificate.

Read in code: `testsettings()` in `mail_relay.py` calls `starttls()`
before `login()`, so the confconsole screen refuses a smart-host that has
no STARTTLS at the time of the setup. The setting that it writes (`may`)
does not keep this rule after the setup.

### Q5. Relay with no password (tested, log 50)

The smart-host got the address of 9470 in `mynetworks`. On 9470:
`mail_relay.sh HOST 25 "" ""`, as confconsole runs it after "no login".

- The script prints `Configuring unauthenticated, unencrypted relay`. It
  writes `relayhost = [HOST]:25`, `smtp_sasl_auth_enable = no` and an
  empty `smtp_sasl_password_maps`, `smtp_sasl_security_options` and
  `smtp_tls_security_level`. It also writes `sasl_passwd` with the line
  `[HOST]:25 :`.
- A message to `someone@example.net` and a message to the relay mailbox
  went through the relay: `status=sent`. The relay accepted the external
  recipient because of `permit_mynetworks`, then bounced it (`nullMX`).
  The relay mailbox has the second message.
- The relay offers STARTTLS on port 25 (`smtpd_tls_security_level=may`).
  The client did not use it: the relay log has 0 `TLS connection
  established` lines for these 2 connections. The empty level means no
  TLS.
- Negative check: 9471 is not in `mynetworks`. A message from 9471 to
  `someone@example.net` on port 25 of the relay got
  `454 4.7.1 Relay access denied`.

### Q6. `deconfigure` (tested, logs 60, 61)

Before the run, 2 lines were added to `main.cf` of 9471:
`# admin note: the relayhost of this site is set by keel` and
`sender_dependent_relayhost_maps = hash:/etc/postfix/sender_relay`.

- `deconfigure` removed the 6 relay lines. It also removed the 2 added
  lines, because they hold the word `relayhost`. **Defect, tested.**
- The configure step already removed the 4 comment lines `#relayhost = ...`
  and the empty `relayhost =` of the Debian file. The `deconfigure` step
  does not put them back. After `deconfigure`, `postconf` shows the same
  values as the image: `relayhost` and `smtp_tls_security_level` empty.
- `deconfigure` shreds `sasl_passwd` but leaves `sasl_passwd.db`. The
  `.db` file still holds the test password in clear text (1 match).
  **Defect, tested.**
- `deconfigure` does not reload Postfix (read in code, and tested).
  Log 61: configure, send one message (sent through the relay), then
  `deconfigure`, then send again at once. The second message also went to
  the relay (`relay=...:587, status=sent`), through the same `smtp`
  process 4814. The old relay stays in use until Postfix reloads or its
  processes end. The first run (log 60) showed direct delivery after
  `deconfigure`, because the test itself ran `postfix reload` just before.
  Log 61 replaces that result.

### Q7. Relay on a pair (not tested, read in code and on the image)

No pair was made. The script edits only the local `main.cf` and
`sasl_passwd`. The appliance manifests on the WordPress image
(`/usr/share/keel/appliances/*.yaml`) name no `/etc/postfix` path in their
`state` (log 70). Thus Syncthing (0050) does not copy the relay to the
replica, and the database replication does not hold it. A relay that a
person makes on the primary is not on the replica.

### Q8. `keel spec apply` and `main.cf` (tested, log 80)

On 9471 with the relay set:

- `keel spec apply --system-only`: `2 change(s), 0 failed` (database
  settings). `main.cf` has the same sha256 before and after.
- `keel spec apply --system`: `0 change(s)`. `main.cf` has no change.
- A host name change in the spec (`mr-lnmp` to `mr-lnmp2`), then
  `keel spec apply --system-only`: keel writes `main.cf` and changes only
  `myhostname`. The 6 relay lines stay. Keel reloads Postfix.

Read in code: `keel/system/hostname.py` renames the host only in
`myhostname` and `mydestination`. `keel/system/security.py` writes
`/etc/aliases` and the cron-apt mail settings, not `main.cf`. Other
writers of `main.cf`: `inithooks/lib/hostname.sh`,
`confconsole/plugins.d/System_Settings/hostname.py` (host name) and
`common/conf/turnkey.d/zz-ssl-ciphers` (build time). No keel step writes
`relayhost` or a `smtp_sasl_*` setting.

## Other findings

- Read in code: the password is an argument of `mail_relay.sh`, so it is
  in `/proc/PID/cmdline` while the script runs, about 10 s
  (`sleep 10` at the end).
- Read in code: the script writes `sasl_passwd` first and runs
  `chmod 600` after it. The file has the default mode for a short time.
- Read in code: the confconsole menu item is `SendinBlue`, but the code
  tests `choice == "Brevo"`. The preset host and port never apply. The
  screen text points to `hub.turnkeylinux.org/email`.
- Tested: `mydestination` names `localhost` 2 times. No effect.
- Tested, not about mail: the first `keel spec apply --system-only` after
  the first boot of LNMP wrote
  `/etc/mysql/mariadb.conf.d/99-keel-database.cnf` and restarted MariaDB.
  The second run made 0 changes.

## Not tested

- A pair (Q7).
- A public smart-host (Brevo or other) and its HELO and sender rules.
- `smtp_tls_security_level = secure` or `verify` with a certificate of a
  public certificate authority.
- An application other than WordPress: Loops, Laravel, Nextcloud, Odoo,
  NodeBB, OJS, ntfy.
- The confconsole screen itself. The test ran the script that the screen
  runs.
- A cloud mode with the firewall overlays.

## Logs

All logs are in `repos/mail-relay-test-2026-11-14/logs/`, numbered:
01 create, 02 first boot, 10 Q1 Postfix state, 11 Q1 port 25 from another
CT, 12 Q1 loopback and unit, 20 Q2 local submission, 21 Q2 WordPress,
30 smart-host setup, 31 Q3 client relay, 32 Q3 smart-host mailbox,
40 Q4 `may`, 41 Q4 `encrypt`, 50 Q5 no password, 60 Q6 deconfigure,
61 Q6 deconfigure with no reload, 70 Q7 manifests, 80 Q8 keel spec apply,
90 secret scan, 99 cleanup. Scripts: `x.sh`, `create_ct.sh`,
`make_preseed.py`, `smtp_send.py`, `smarthost_setup.sh`, `pcap_auth.py`.
Descriptions in `preseed/`.

## Cleanup

CTs 9470, 9471 and 9472 were stopped and destroyed with
`pct destroy --purge 1` (log 99). CTs 9473 and 9474 were not made.
