# 0036: What lives in common, and what is an appliance

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-013).

## Decision

**The rule:** what two or more images use is an overlay in `common`, with
its conf and inithook scripts. A named combination with an identity is an
appliance.

**Overlays in common:**

| Group | Overlays | Default |
| --- | --- | --- |
| Mesh | wireguard, etcd, vip, syncthing | etcd stopped |
| Protection | crowdsec, coraza, anubis | disabled |
| Web | nginx | |
| Runtimes | php-fpm, python, ruby, nodejs, go | |
| Data | postgresql, mariadb, redis, elasticsearch or opensearch | |
| Installer | extensions in confconsole and inithooks: simple and advanced, cloud simple and cloud advanced, discovery, YAML emission and consumption | |

**Appliances:**

| Appliance | Composition |
| --- | --- |
| Keel Core | Debian, wireguard, etcd, crowdsec, the installer |
| Keel Web | Core, nginx, coraza, anubis |
| Keel PostgreSQL, Keel MariaDB | Core, the database, vip, syncthing |
| Keel Redis | Core, redis |
| Keel Elasticsearch | Core, the search engine |
| Keel PHP | Web, php-fpm; replaces LAMP and LAPP |
| Keel Python, Keel Ruby, Keel Node | Web and the runtime |

**Applications:**

| Application | Consumes | Replicated state, workers |
| --- | --- | --- |
| WordPress | PHP, MariaDB | wp-content |
| Nextcloud | PHP, MariaDB, Redis, optionally search | data |
| Odoo | Python, PostgreSQL, optionally Redis | filestore and addons; cron and queue workers |
| Mastodon | Ruby, PostgreSQL, Redis, optionally search | media; Sidekiq |
| Ghost | Node, MariaDB | |
| Discourse | Ruby, PostgreSQL, Redis | Sidekiq |
| Gitea or Forgejo | Web, go, PostgreSQL | repositories |

**Not in common: Apache**, which is retired (0030).

## What this amends

- **0010, "The three levels"**: a component was to be one repository
  each, shipped as a fab unit. Here a component is an overlay in `common`,
  and under 0039 every overlay is also a `.deb`. Content addressed layers
  and the recipe level are unchanged.
- **0013, "The catalog shape"**: the `apache-php`, `lamp` and `lapp` rows
  are superseded by Keel Web and Keel PHP.
- **0022** (open, handbook#23): the LNPP stack is Keel Python plus
  PostgreSQL; Odoo's row above is its application.
- **0006, item 2**: the appliance list changes as above.

## Review notes (open points for the maintainer)

- [ ] **The unit repositories that already exist** under 0010
  (`unit-redis`, and the mariadb and postgresql extractions in
  keel-mariadb#14 and keel-postgresql#10) either fold back into `common`
  as overlays or become the source of the overlay's `.deb`. To be decided
  before those PRs are rebased.
