# 0001: Name, domains and hosting: options for the maintainer

Date: 2026-09-24
Status: options prepared, decision pending (brief section 11)

The agent does not decide this. What follows is what was checked, on 2026-09-24,
so the decision can be made with facts.

## Existing projects called Keel

- `keel.sh` resolves and serves a site titled "Keel". It is an existing
  open-source tool for automated deployments of Kubernetes workloads. The name
  collision sits in the same broad space (container tooling), which matters both
  for search and for the project's stated non-goals: our first public page would
  have to say what we are not.
- No Debian package named `keel` exists in Trixie (the packages.debian.org page
  returns its error body with HTTP 200, which is easy to misread as a hit).

## Names checked

| Name | github.com org | Notes |
| --- | --- | --- |
| keel | free | collides with keel.sh |
| keel-linux | free | domain keel-linux.org has no DNS record |
| keelos | free | keelos.org resolves, so the domain is taken |
| keel-project | free | keelproject.org has no DNS record |
| keel-appliances | free | describes the product, long |
| keelsys | free | |

## Domains

Resolving today (taken, or at least parked): keel.org, keel.dev, keel.io,
keelos.org, keel.sh. No DNS record today: keel-linux.org, keelproject.org.
DNS resolution is a signal, not a registry check; a registrar lookup is still
needed before anything is announced.

## Package namespaces

PyPI `keel` and `keel-cli` are both taken; `keelctl` is free. This matters only
if the CLI is ever published to PyPI; inside Debian packaging the binary name is
ours to choose.

## What the agent suggests deciding first

1. Whether the CLI binary is `keel` regardless of the project name. The brief
   already reserves this (section 11), and the spec path `/etc/keel/` and the
   package prefixes `keel-archive-keyring` and `keel-transition` all depend on it.
2. The GitHub organization name, because every fork and every URL in the docs
   depends on it, and renaming an org later leaves redirects but breaks pinned
   references in manifests.
3. Trademark review for the chosen name before any public announcement, given
   the keel.sh collision.

Nothing in the code needs the final name yet: the working name can stay in prose
and the packages can keep the `keel-` prefix, since the prefix is cheap to
rename before the first public repository is published.

## Decision (2026-09-24, maintainer)

The project and the GitHub organization are **KeelLinux**. Checked the same day,
all free: the GitHub organization `KeelLinux` (and the `keellinux` and
`keel-linux` spellings), the domains keellinux.org, keellinux.com,
keellinux.dev, keellinux.io and keellinux.net (no DNS record on any of them),
and the PyPI names `keellinux` and `keel-linux`.

Consequences, and what is still open:

- The keel.sh collision no longer applies to the project name. It still applies
  to the CLI if the binary is called `keel`, which is a separate decision
  (brief section 11). The `keel-` package prefix and the `/etc/keel/` spec path
  in the brief are unaffected by the organization name and can stay until that
  decision is made.
- DNS resolution was the only check run. A registrar lookup and the trademark
  review are still needed before any public announcement, and no domain has been
  registered by the agent.
- Repository URLs will read github.com/KeelLinux/<repo>. Manifests that pin
  source URLs should use that spelling from the start, since an organization
  rename leaves redirects but breaks pinned references.
