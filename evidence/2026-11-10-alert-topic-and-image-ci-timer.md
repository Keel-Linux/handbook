# The alert topic `keel-alerts` and the state of the image CI timer

Date: 2026-11-10

This file is the evidence for the amendments of 2026-11-10 to decisions
0063 and 0061.

## 1. The topic `keel-alerts` on ntfy-br1 and ntfy-br2

### The servers

| Server | Container | Site | State |
|---|---|---|---|
| `ntfy-br1.pop.coop` | CT 9190 | BR1 | answers |
| `ntfy-br2.pop.coop` | CT 9191 | BR2 | answers |
| `ntfy-br3.pop.coop` | CT 9192 | BR3 | does not answer (the site is down) |

Read from the configuration of CT 9190, with no change:
`auth-default-access: deny-all`, `cache-duration: 12h`,
`enable-login: true`, `behind-proxy: true`.

The accounts on CT 9190:

| Account | Access |
|---|---|
| `admin` | administrator |
| `publisher` | write only, all topics |
| the maintainer's account | read only, `keel-*` |
| the account of the release test | read and write, its own prefix |
| anonymous | none |

### The test

One message was sent to `keel-alerts` on each server. It was sent from
inside the container of the server, with the token of `publisher` that
the container holds. The token was not printed. Then the message was
read from the workstation with the read-only account, through the public
name and HTTPS.

| Server | Publish | Message id | Time (UTC) | Kept until (UTC) |
|---|---|---|---|---|
| ntfy-br1 | HTTP 200 | `dScEYKirvGWm` | 2026-11-10 18:20:48 | 2026-11-11 06:20:48 |
| ntfy-br2 | HTTP 200 | `0Lp9LwpvkgwA` | 2026-11-10 18:20:50 | 2026-11-11 06:20:50 |

The message: title "Keel: test message", text "Test message from
ntfy-brN. The topic keel-alerts works. No action is necessary."

The access rules, tested at 18:25 UTC on each of the two servers:

| Act | Result |
|---|---|
| The read-only account reads `keel-alerts` | the message above |
| The read-only account publishes to `keel-alerts` | HTTP 403 |
| No account reads `keel-alerts` | HTTP 403 |

### What this does not show

- No Keel node sent this message. `keel notify` on a node of the
  migration is not configured for these servers yet (0063 step 4).
- The message was not seen on a phone in this test.
- ntfy-br3 was not tested.

No configuration of a server was changed.

## 2. `keel-image-ci.timer` on the build host

| Time (UTC) | Fact |
|---|---|
| 2026-11-06 23:55 to 2026-11-09 01:44 | The builds of this interval open issues 50 to 59 of `Keel-Linux/image-gate` (a build or a boot test that failed). All are open |
| 2026-11-07 01:00 | The last promoted build, `20261107T003855Z` (`latest-odoo`) |
| 2026-11-09 02:03:36 | The timer is stopped (journal: "Stopped keel-image-ci.timer") |
| 2026-11-09 01:39:41 | The run `20261109T012840Z` ends: the build of odoo failed (`keel-release` exit 6) |
| 2026-11-09 02:10:33 | The last run, `20261109T014455Z`, ends: "No appliance was built. Failed: web lnmp lnpp wordpress odoo ntfy" (`keel-release` exit 6, and exit 5 for ntfy) |
| 2026-11-10 18:19:52 | `systemctl disable keel-image-ci.timer` |

The unit was a link to `/srv/keel-apt/apt/systemd/keel-image-ci.timer`.
`systemctl disable` removed that link also. After it:

```
# systemctl is-enabled keel-image-ci.timer
not-found
# systemctl is-active keel-image-ci.timer
inactive
```

The link of `keel-image-ci.service` stays. The file of the timer in the
checkout of `Keel-Linux/apt` is not changed. `keel-channel-refresh.timer`
is not changed and stays on.

The cause of the failed runs was not examined on this day.
