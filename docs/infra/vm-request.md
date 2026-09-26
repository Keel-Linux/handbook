# Request: VM for keellinux.org public services

From the Keel Linux project. The zone keellinux.org is delegated to ns1.pop.uy
and ns2.pop.uy.

## VM

- Debian 13 (trixie), 4 vCPU, 8 GB RAM, 250 GB disk (layer tarballs of 80 to
  330 MB, an APT repository, a Debian package mirror).
- One public routable IPv6 address; inbound 22, 80, 443 open. IPv4 optional.
- Hostname: releases.keellinux.org.
- Authorize this key for root:
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOfD05/bkJlVP/UVZPvoXudoFpk5SemdfQM7mj9lANdQ navigator@agent-democracia-social
- Install nothing else: nginx, ACME, repository tooling and the GitHub
  Actions runner will be set up by the project afterwards.

## DNS records in keellinux.org

- releases.keellinux.org  AAAA  <the VM address> (and A if it has IPv4)
- apt.keellinux.org       CNAME keel-linux.github.io
- www.keellinux.org       CNAME keel-linux.github.io
- keellinux.org (apex)    A     185.199.108.153, 185.199.109.153,
                                185.199.110.153, 185.199.111.153
                          AAAA  2606:50c0:8000::153, 2606:50c0:8001::153,
                                2606:50c0:8002::153, 2606:50c0:8003::153

## Reply with

The hostname, the IPv6 address, and confirmation of each DNS record. If any
item conflicts with how the cluster or the zone is managed, say what can be
done instead rather than adapting silently.
