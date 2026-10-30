# Step 12 boot checks — hw12-br1 (2026-10-13)

Appliance images: step 12 of 2026-10-12, decision 0052 lean core (no boot set
in the container template). Staged in /srv/keel-release/2026-10-12 on the
build host, published as UNSIGNED GitHub pre-releases (testing-*-step12-20261012).

Host: hw12-br1 (Proxmox pve-manager/9.2.11, kernel 7.0.14-12-pve).
Templates verified byte-identical to the build host (sha256 match) before use;
stale Oct-10 copies in /var/lib/vz/template/cache were replaced.

CT pattern (matches production CTs 124/125/9003): unprivileged, nesting=1,
rootfs local-lvm:8, net0 name=eth0,bridge=vtnet88,firewall=1,ip=dhcp,
ip6=dhcp,tag=5,type=veth.

First boot preseed: /etc/inithooks.conf written on the host-mounted rootfs
before start (ROOT_PASS, FQDN, HUB_APIKEY/SEC_ALERTS/SEC_UPDATES/REBOOT=SKIP,
DB_PASS on the engines). Traps found while tuning the pattern:
- bridge=vmbr0 (untagged) has no DHCP server; the working network is
  vtnet88 VLAN 5 (10.88.5.0/24). Image defect candidates first suspected,
  cause was the test harness network.
- nesting=1 is required: without it dev-mqueue/run-lock/tmp mounts fail
  and the system boots degraded.
- confconsole dialog tracebacks on a console with no attached terminal are
  benign; journal shows Confconsole started and running.

## CT 9051 — keel-core 19.0-10 (template debian-13-keel-core_19.0-10+step12)

- created from local:vztmpl/debian-13-keel-core_19.0-10+step12_amd64.tar.zst
- first boot: inithooks "Inithooks run completed" (journal), FQDN
  core.step12.test applied from preseed
- network: eth0 10.88.5.207/24 (dhcp), global IPv6 2804:710:d0:5:3a98:7f6d:5fdd:f3c1/64
- systemctl is-system-running: degraded (only systemd-modules-load failed —
  expected in an unprivileged LXC)
- listening: 22 (sshd), 25 (postfix, localhost), 12321 (confconsole web)
- keel firstboot: "no terminal to ask on: this node stays standalone" —
  expected unattended; role chosen later in confconsole
- versions: keel 0.23.13, keel-core 0.1.3, keel-overlay-vip 0.2.0,
  inithooks 2.3.6+keel23, confconsole 2.2.3+keel15
- verdict: PASS

## CT 9052 — keel-web 19.0-5 (template debian-13-keel-web_19.0-5+step12)

- first boot: inithooks completed (INITDONE=1), FQDN web.step12.test
- network: eth0 10.88.5.214/24, global IPv6 2804:710:d0:5:aa9f:5057:23aa:fa05/64
- running: degraded (only systemd-modules-load, expected in LXC)
- listening: 22, 25, 80, 443, 12321; :80 and :443 served by nginx
  (keel-web is nginx-based; an apache2 unit check is the wrong probe)
- verdict: PASS

## CT 9053 — keel-mariadb 19.0-9 (template debian-13-keel-mariadb_19.0-9+step12)

- first boot: inithooks completed, FQDN mariadb.step12.test
- mariadb service active; `mariadb-admin -uroot -p<DB_PASS> ping` -> "mysqld is alive"
- 3306 listening
- verdict: PASS

## CT 9054 — keel-postgresql 19.0-6 (template debian-13-keel-postgresql_19.0-6+step12)

- first boot: inithooks completed, FQDN postgres.step12.test
- postgresql service active; `pg_isready` -> "accepting connections"
- 5432 listening
- verdict: PASS

## CT 9055 — keel-redis 19.0-9 (template debian-13-keel-redis_19.0-9+step12)

- first boot: inithooks completed, FQDN redis.step12.test
- redis-server active; 6379 listening
- auth by design: no requirepass; default user has no permissions; ACL user
  `admin` in /etc/redis/redis.conf.d/20-keel-acl.conf with the SHA-256 of the
  preseeded DB_PASS. `redis-cli --user admin -a $DB_PASS ping` -> PONG.
  (A plain `redis-cli -a $DB_PASS ping` failing is the intended state.)
- verdict: PASS

## Summary

All five step-12 appliances boot clean on hw12-br1 Proxmox CTs: inithooks
complete unattended from the preseed, DHCPv4+v6 on vtnet88 VLAN 5, ssh up,
every application engine answers with the preseeded credentials, and the only
failed unit is systemd-modules-load (expected in an unprivileged LXC).
CTs 9051-9055 left running for inspection.
