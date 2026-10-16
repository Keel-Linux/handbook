# Evidence: the GitHub bridge, part 1 (2026-10-16)

Decision: 0056, amendment of 2026-10-16 ("contributions on GitHub and on
git.pop.coop").

| Item | Result | Detail |
| --- | --- | --- |
| 1. Existing tool | None fits | `eleboucher/forgesync` copies GitHub issues to Forgejo only, no pull requests. Others found are one-shot migrators or pull-mirror helpers. |
| 2. keel-bridge | Merged | keel-bridge#1, 109 tests, 99 percent branch coverage, security scan green. A security review found 4 HIGH and 8 MEDIUM items; all HIGH and 7 MEDIUM are fixed in the same pull request; the others are known gaps in the README. |
| 3. Forgejo bot | Done | user `keel-bridge`, not an administrator; team `bridge`: issues and pulls write, code read, Actions none, on the 51 bridged repositories and `keel-bridge`. As the bot: `admin=False push=False pull=True` on keel-keys. |
| 4. Bridge container | Done | `keel-bridge` on Keel-Linux-Runner, unprivileged (idmap 2000000), no nesting, own bridge `kbr0`. |
| 5. Isolation | PASS | section 1: runner users 9 to 16, a probe on `lxcbr0`, a rootless podman container of runner15 |
| 6. Fork PR of the bot waits for approval | PASS | keel-bridge#2, keel-keys#5 (sections 2 and 3) |
| 7. Host runners refuse a bridged PR | PASS | keel-keys#5, tasks 8575 to 8578 (section 3) |
| 8. Light GitHub CI | 46 of 51 merged | the list in section 4 |
| 9. GitHub settings | Done | section 5 |
| 10. inithooks archive | Unlocked, no copies yet | GitHub inithooks#13, 15, 17, 21, 22, 23, 24, 26, 31, 40: `locked=false`. The copies of 21, 26, 31 and 40 wait for the bridge start. |
| 11. GitHub App | Waits for the maintainer | a browser step (section 6) |
| 12. End-to-end test | Not run | needs item 11 |

The Forgejo token of the bot went from the API straight into the
container through a pipe. It was not printed and is not in a file
outside the container.

## 1. Isolation of the bridge container

    2026-10-16 ~08:00 UTC, Keel-Linux-Runner (keel-lxc-2). Temporary listener python3 -m http.server 8080 in keel-bridge.
    CT to itself http://[::1]:8080/ -> 200
    host root -> 10.0.9.2:8080 and [fd4b:6b65:6c09::2]:8080: curl (7) Could not connect (after 0 ms, TCP reset)
    runner9, runner14 (runuser) -> 10.0.9.2:8080, [fd4b:6b65:6c09::2]:8080, 10.0.9.2:22: curl (7) Could not connect (after 0 ms)
    probe container kb-probe on lxcbr0 (10.0.3.189, same bridge and default.conf as job containers):
      -> 10.0.9.2:8080, [fd4b:6b65:6c09::2]:8080: curl (7) Could not connect (after 0 ms)
      -> 10.0.9.1:22 (host via kbr0 address): timeout (inet filter input drops lxcbr0)
      -> https://deb.debian.org/: 200 (the probe has normal Internet access; only the CT is closed)
    keel-bridge egress: https://api.github.com/ 200, https://git.pop.coop/api/v1/version 200, http://example.com blocked (port 80)
    nft counters after the test:
      forward oifname kbr0 tcp reject: 2 packets (probe container)
      output skuid 1100-1199 tcp reject: 6 packets (runner9, runner14)
      output tcp reject (other host processes): 2 packets (root)
      forward iifname kbr0 final drop: 154 packets (apt over http before the switch to https)

Second probe, after the fork rule (handbook#95), 12:45 UTC, with the
same temporary listener:

    runner15 (uid 1115), runner16 (uid 1116) on the host -> 10.0.9.2:8080, [fd4b:6b65:6c09::2]:8080:
      curl (7) Could not connect (after 0 ms)
    podman run --rm localhost/keel-ci:trixie as runner15 (container 60e8a4927035, rootless):
      -> 10.0.9.2:8080, [fd4b:6b65:6c09::2]:8080: curl (7) Could not connect; https://deb.debian.org/ 200
    counter of "meta skuid 1100-1199 ... reject with tcp reset": 6 -> 12 packets

## 2. The fork pull request of the bot waits

    2026-10-16 ~08:40 UTC. Bot keel-bridge forked Keel-Linux/keel-bridge (fork Actions off: GET /repos/keel-bridge/keel-bridge/actions/runs -> 404),
    pushed test/approval (head of feat/bridge, with .forgejo/workflows) and opened keel-bridge#2 from keel-bridge:test/approval.
    Runs: 2899, 2900 (keel-bridge#1, trigger navigator, a writer): need_approval=False, ran.
          2901, 2902 (keel-bridge#2, trigger keel-bridge): status waiting, need_approval=True. No job started.
    Bot permission on Keel-Linux repos (GET /repos/Keel-Linux/keel-keys as the bot): admin=False push=False pull=True.
    keel-bridge#2 closed, branch deleted.

## 3. The host runners refuse a bridged pull request

    2026-10-16 ~09:55-10:35 UTC. keel-keys#5: opened by the bot keel-bridge from keel-bridge:gh-pr/test (head 143632e8aa95),
    with the bridge code path (Forgejo.ensure_fork, git push with the credential helper scoped to git.pop.coop, Forgejo.create_pull).
    Before approval: package/build, security, tests/tests, tests/package = pending "Blocked by required conditions" (runs 17, 18, 19; need approval).
    Approval: "approve once" (POST /Keel-Linux/keel-keys/pulls/5/action-user-trust trust=once) by a throwaway user keel-bridge-approver,
    write collaborator on keel-keys only during the approval, deleted after. "Always trust" not selected.
    After approval: "Waiting to run" (queue of 33 keel-host jobs), then each job on a host runner (v13.2.0+keel1):
      received task 8575 of job build ... refused by the Keel trust gate: event pull_request: the pull request is from keel-bridge/keel-keys,
      not from Keel-Linux/keel-keys; a pull request from a fork runs only on a container runner (runs-on: keel-container)
      same for tasks 8576 (security), 8577 (tests), 8578 (package). Combined status: failure. No step ran.
    keel-keys#5 closed, branch gh-pr/test deleted from the fork. Fork keel-bridge/keel-keys has has_actions=false.

## 4. Light GitHub CI

Reusable workflows added to Keel-Linux/.github (.github#27):
`github-test-shell.yml`, `github-test-python.yml`,
`github-security-scan.yml`, `github-require-changelog.yml`,
`github-debian-build.yml`, `github-lint.yml`. They use `ubuntu-latest` or
a `debian:trixie` container, pinned GitHub-owned actions, no secret and
`contents: read`.

Merged callers (`pull_request` only): .github#27, anubis#6, bootstrap#3,
buildtasks#25, common#57, confconsole#34, coreruleset#4, fab#14,
handbook#94, inithooks#51, keel-core#33, keel-ejabberd#3, keel-keys#4,
keel-linux.github.io#9, keel-mariadb#36, keel-moodle#4,
keel-nginx-php-fastcgi#5, keel-odoo#3, keel-pve#6, keel-redis#19,
keel-transition#12, keel-web#14, libcoraza#4,
libnginx-mod-http-coraza#7, tkl-dhcpcd-ifupdown-glue#4,
tkl-installer#4, tklbam#4, tklbam-profiles#5, tklbam-python-boto#4,
tkldev#7, turnkey-chroot#6, turnkey-conffile#4, turnkey-netinfo#4,
turnkey-pylib#4, turnkey-ssl#4, turnkey-sysinfo#5, turnkey-version#5,
unit-mariadb#7, unit-postgresql#6, unit-redis#11, webmin#5. No
`.github/workflows`: cdroots, keel-cloud, keel-lnmp, keel-lnpp, tracker.

Open and red on Forgejo for other reasons (Actions stays off on GitHub
there): keel#184 (netem tests flaky), keel-nodejs-nginx#6, keel-nodebb#21
and keel-wordpress#20 (the boot test needs a layer that was never
published), keel-postgresql#20 (35pgsqlpass and 36pgsqlverify fail after
the upgrade to keel 0.23.29).

Jobs that need systemd or network namespaces stay on Forgejo only (a
Docker container cannot run them): anubis and libnginx-mod-http-coraza
`autopkgtest`, common `install` and `web`, keel-web `site`, and keel
`mesh`, `etcd`, `vip`, `vip-upgrade`, `etcd-auth`, `mariadb`,
`mariadb-simple`, `postgres`.

Validation on GitHub-hosted runners in `Keel-Linux/demo-repository`
(private): fixture pull request #3, runs 38871172102, 38871172077,
38871171951, 38871172400 green; a failing test fails the job. Pull
requests #4 to #12 ran the light CI of anubis, common, keel, keel-core,
keel-mariadb, confconsole, turnkey-netinfo, keel-pve and
keel-linux.github.io: 20 runs, all green (for example runs 38872677714
and 38872684127). Actions and pull requests are off there again.

A scan of every GitHub copy after the mirror push (`.github/workflows`
of each repository, the triggers and the `runs-on` lines): the callers
of 46 repositories have `pull_request` triggers only and no self-hosted
label. Keel-Linux/.github also keeps the reusable workflows of the
Forgejo CI, with `keel-host` and `[self-hosted, keel-lxc]`: they are
`workflow_call` only, no GitHub caller uses them, and the organization
allows no self-hosted runner. The 5 above still have `push`; their
Actions stays off.

After the merge of handbook#96, .github#28 and keel-bridge#3 at
12:40 UTC, the push mirror updated GitHub (`main` the same on both
sides: handbook 055614224d85, .github e45369050989, keel-bridge
a6e3f1273ba6). GitHub Actions is on in the three repositories, and
`actions/runs?created>=2026-10-16T12:00:00Z` is 0 for each: a mirror
push starts no run.

## 5. GitHub settings

Organization:

    PUT orgs/Keel-Linux/actions/permissions/self-hosted-runners  enabled_repositories=none
    PUT orgs/Keel-Linux/actions/permissions  allowed_actions=selected
    PUT orgs/Keel-Linux/actions/permissions/selected-actions  github_owned_allowed=true verified_allowed=false patterns_allowed=[]
    default_workflow_permissions=read, can_approve_pull_request_reviews=false (unchanged)

Each repository (output of the script, `issues+prs on; actions on; fork
approval all; token read`, 0 failures):

    .github issues+prs on; actions on; fork approval all; token read
    anubis issues+prs on; actions on; fork approval all; token read
    bootstrap issues+prs on; actions on; fork approval all; token read
    buildtasks issues+prs on; actions on; fork approval all; token read
    cdroots issues+prs on; actions on; fork approval all; token read
    common issues+prs on; actions on; fork approval all; token read
    confconsole issues+prs on; actions on; fork approval all; token read
    coreruleset issues+prs on; actions on; fork approval all; token read
    fab issues+prs on; actions on; fork approval all; token read
    handbook issues+prs on; actions on; fork approval all; token read
    inithooks issues+prs on; actions on; fork approval all; token read
    keel issues+prs on; actions kept off (light CI PR not merged)
    keel-cloud issues+prs on; actions on; fork approval all; token read
    keel-core issues+prs on; actions on; fork approval all; token read
    keel-ejabberd issues+prs on; actions on; fork approval all; token read
    keel-keys issues+prs on; actions on; fork approval all; token read
    keel-linux.github.io issues+prs on; actions unchanged (Pages); fork approval all; token read
    keel-lnmp issues+prs on; actions on; fork approval all; token read
    keel-lnpp issues+prs on; actions on; fork approval all; token read
    keel-mariadb issues+prs on; actions on; fork approval all; token read
    keel-moodle issues+prs on; actions on; fork approval all; token read
    keel-nginx-php-fastcgi issues+prs on; actions on; fork approval all; token read
    keel-nodebb issues+prs on; actions kept off (light CI PR not merged)
    keel-nodejs-nginx issues+prs on; actions kept off (light CI PR not merged)
    keel-odoo issues+prs on; actions on; fork approval all; token read
    keel-postgresql issues+prs on; actions kept off (light CI PR not merged)
    keel-pve issues+prs on; actions on; fork approval all; token read
    keel-redis issues+prs on; actions on; fork approval all; token read
    keel-transition issues+prs on; actions on; fork approval all; token read
    keel-web issues+prs on; actions on; fork approval all; token read
    keel-wordpress issues+prs on; actions kept off (light CI PR not merged)
    libcoraza issues+prs on; actions on; fork approval all; token read
    libnginx-mod-http-coraza issues+prs on; actions on; fork approval all; token read
    tkl-dhcpcd-ifupdown-glue issues+prs on; actions on; fork approval all; token read
    tkl-installer issues+prs on; actions on; fork approval all; token read
    tklbam issues+prs on; actions on; fork approval all; token read
    tklbam-profiles issues+prs on; actions on; fork approval all; token read
    tklbam-python-boto issues+prs on; actions on; fork approval all; token read
    tkldev issues+prs on; actions on; fork approval all; token read
    tracker issues+prs on; actions on; fork approval all; token read
    turnkey-chroot issues+prs on; actions on; fork approval all; token read
    turnkey-conffile issues+prs on; actions on; fork approval all; token read
    turnkey-netinfo issues+prs on; actions on; fork approval all; token read
    turnkey-pylib issues+prs on; actions on; fork approval all; token read
    turnkey-ssl issues+prs on; actions on; fork approval all; token read
    turnkey-sysinfo issues+prs on; actions on; fork approval all; token read
    turnkey-version issues+prs on; actions on; fork approval all; token read
    unit-mariadb issues+prs on; actions on; fork approval all; token read
    unit-postgresql issues+prs on; actions on; fork approval all; token read
    unit-redis issues+prs on; actions on; fork approval all; token read
    webmin issues+prs on; actions on; fork approval all; token read
    keel-bridge issues+prs on; actions on; fork approval all; token read

## 6. The GitHub App: what the maintainer does

1. Open `deploy/github-app-manifest.html` of Keel-Linux/keel-bridge in a
   browser that is signed in to GitHub as an owner of Keel-Linux.
2. Push "Create the App on GitHub", then "Create GitHub App".
3. Copy the `code` from the address of the page that opens. It is valid
   for 1 hour.
4. Install the App on Keel-Linux, "Only select repositories", for
   example keel-keys. The operator adds the other repositories.

The operator then runs `deploy/github-app-convert CODE` as root in the
container. The key goes from GitHub into the container only.

## 7. Files on the VM

    #!/usr/sbin/nft -f
    # keel-bridge: the network of the bridge container on keel-lxc-2
    # (handbook decision 0056, amendment of 2026-10-16).
    #
    # The container keel-bridge holds the tokens of the GitHub/Forgejo bridge.
    # It is on its own bridge kbr0, not on lxcbr0. It may open outbound HTTPS
    # (and DNS to the uplink resolvers) and nothing else. Nothing may open a
    # connection to it: not the CI containers on lxcbr0, not the runner users
    # on this host, not the LAN. keel-bridge-net.service loads this file after
    # nftables.service and lxc-net.service, and again on each reload.
    
    table inet keel_bridge
    delete table inet keel_bridge
    
    table inet keel_bridge {
    	set private4 {
    		type ipv4_addr; flags interval
    		elements = { 0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8,
    			     169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16,
    			     224.0.0.0/3 }
    	}
    	set resolvers4 {
    		type ipv4_addr
    		elements = { 10.88.16.53, 10.88.16.54, 1.1.1.1 }
    	}
    
    	chain forward {
    		type filter hook forward priority filter - 10; policy accept;
    		oifname "kbr0" ct state established,related accept
    		oifname "kbr0" meta l4proto tcp counter reject with tcp reset comment "nothing opens a connection to the bridge container"
    		oifname "kbr0" counter reject comment "nothing opens a connection to the bridge container"
    		iifname "kbr0" oifname != "eth0" counter drop comment "the bridge container reaches the uplink only, never lxcbr0"
    		iifname "kbr0" ct state established,related accept
    		iifname "kbr0" ip daddr @resolvers4 meta l4proto { tcp, udp } th dport 53 accept comment "DNS to the uplink resolvers"
    		iifname "kbr0" ip6 daddr 2804:710:d0:5::20 tcp dport 443 accept comment "git.pop.coop HTTPS"
    		iifname "kbr0" ip daddr @private4 counter drop comment "no private IPv4 range"
    		iifname "kbr0" ip6 daddr { 2804:710:d0:5::/64, fc00::/7, fe80::/10, ff00::/8 } counter drop comment "no LAN, ULA or link local"
    		iifname "kbr0" tcp dport 443 accept comment "outbound HTTPS"
    		iifname "kbr0" counter drop comment "all other traffic of the bridge container"
    	}
    
    	chain input {
    		type filter hook input priority filter - 10; policy accept;
    		iifname "kbr0" ct state established,related accept
    		iifname "kbr0" icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert, nd-router-solicit } accept
    		iifname "kbr0" counter drop comment "the bridge container reaches nothing on this host"
    	}
    
    	chain output {
    		type filter hook output priority filter - 10; policy accept;
    		oifname "kbr0" ct state established,related accept
    		oifname "kbr0" icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert, nd-router-advert } accept
    		oifname "kbr0" meta skuid 1100-1199 meta l4proto tcp counter reject with tcp reset comment "runner users never reach the bridge container"
    		oifname "kbr0" meta skuid 1100-1199 counter reject comment "runner users never reach the bridge container"
    		oifname "kbr0" meta l4proto tcp counter reject with tcp reset comment "no host process opens a connection to the bridge container"
    		oifname "kbr0" counter reject comment "no host process opens a connection to the bridge container"
    	}
    
    	chain postrouting {
    		type nat hook postrouting priority srcnat; policy accept;
    		ip saddr 10.0.9.0/30 oifname "eth0" masquerade
    		ip6 saddr fd4b:6b65:6c09::/64 oifname "eth0" masquerade
    	}
    }
    
    # The base chains of inet filter (nftables.conf) drop forwarded traffic by
    # policy, so they need these two accepts. The chain above has already
    # dropped all that is not allowed.
    add rule inet filter forward iifname "kbr0" oifname "eth0" accept comment "keel-bridge: outbound, filtered by inet keel_bridge"
    add rule inet filter forward oifname "kbr0" ct state established,related accept comment "keel-bridge: replies"
    ----
    #!/bin/sh
    # keel-bridge-net up|down: kbr0 and /etc/keel-bridge/keel-bridge.nft.
    set -eu
    case "${1:-}" in
    up)
    	ip link show kbr0 >/dev/null 2>&1 || ip link add kbr0 type bridge
    	ip addr replace 10.0.9.1/30 dev kbr0
    	ip -6 addr replace fd4b:6b65:6c09::1/64 dev kbr0 nodad
    	ip link set kbr0 up
    	# Remove the accepts of an earlier load from inet filter, then load.
    	for h in $(nft -a list chain inet filter forward 2>/dev/null |
    		sed -n 's/.*"keel-bridge: .*# handle \([0-9]*\)$/\1/p'); do
    		nft delete rule inet filter forward handle "$h"
    	done
    	nft -f /etc/keel-bridge/keel-bridge.nft
    	;;
    down)
    	nft delete table inet keel_bridge 2>/dev/null || true
    	for h in $(nft -a list chain inet filter forward 2>/dev/null |
    		sed -n 's/.*"keel-bridge: .*# handle \([0-9]*\)$/\1/p'); do
    		nft delete rule inet filter forward handle "$h"
    	done
    	ip link del kbr0 2>/dev/null || true
    	;;
    *) echo "usage: $0 up|down" >&2; exit 2 ;;
    esac
    ----
    # keel-bridge: the bridge kbr0 and the firewall of the bridge container
    # (handbook decision 0056, amendment of 2026-10-16). Not a runner part:
    # the forgejo-runner units do not use it.
    [Unit]
    Description=Network of the keel-bridge container (kbr0 and nft rules)
    After=nftables.service lxc-net.service network-online.target
    Wants=network-online.target
    PartOf=nftables.service
    ReloadPropagatedFrom=nftables.service
    Before=lxc.service
    
    [Service]
    Type=oneshot
    RemainAfterExit=yes
    ExecStart=/usr/local/sbin/keel-bridge-net up
    ExecReload=/usr/local/sbin/keel-bridge-net up
    ExecStop=/usr/local/sbin/keel-bridge-net down
    
    [Install]
    WantedBy=multi-user.target
    ----
    lxc.idmap = u 0 2000000 65536
    lxc.idmap = g 0 2000000 65536
    lxc.net.0.type = veth
    lxc.net.0.link = kbr0
    lxc.net.0.flags = up
    lxc.net.0.name = eth0
    lxc.net.0.ipv4.address = 10.0.9.2/30
    lxc.net.0.ipv4.gateway = 10.0.9.1
    lxc.net.0.ipv6.address = fd4b:6b65:6c09::2/64
    lxc.net.0.ipv6.gateway = fd4b:6b65:6c09::1
    ----
    lxc.include = /usr/share/lxc/config/common.conf
    lxc.include = /usr/share/lxc/config/userns.conf
    lxc.arch = linux64
    lxc.idmap = u 0 2000000 65536
    lxc.idmap = g 0 2000000 65536
    lxc.rootfs.path = dir:/var/lib/lxc/keel-bridge/rootfs
    lxc.uts.name = keel-bridge
    lxc.net.0.type = veth
    lxc.net.0.link = kbr0
    lxc.net.0.flags = up
    lxc.net.0.name = eth0
    lxc.net.0.ipv4.address = 10.0.9.2/30
    lxc.net.0.ipv4.gateway = 10.0.9.1
    lxc.net.0.ipv6.address = fd4b:6b65:6c09::2/64
    lxc.net.0.ipv6.gateway = fd4b:6b65:6c09::1
    lxc.start.auto = 1
    lxc.cgroup2.memory.max = 512M
    lxc.cgroup2.pids.max = 512
    lxc.apparmor.profile = generated
    lxc.apparmor.allow_nesting = 0
    ----
    /etc/subuid:root:2000000:65536
    /etc/subgid:root:2000000:65536
    enabled
    Name:           keel-bridge
    State:          RUNNING
    PID:            973075
