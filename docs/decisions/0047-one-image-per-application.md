# 0047: One image per application

Date: 2026-10-02
Status: **decided by the maintainer, 2026-10-02**. It is the basis of
Phase 4 of the roadmap (Keel PHP and WordPress, tracker#46). Nothing here
is built yet.

## Decision

- **An application appliance ships as one image**, for example
  `debian-13-keel-wordpress`. There is no separate standalone image and no
  separate cloud image. The installation mode chosen at first boot (0028)
  decides what runs, as 0041 (decision 3) has it for every overlay: the
  image content is the same in every mode, and only the states differ.
- **The WordPress chain is Keel Core, Keel Web, Keel PHP (php-fpm), then
  WordPress.** WordPress is the application, its manifest (0041) and its
  first boot hook, plus a MariaDB overlay as the embedded data service
  (0033). Apache is not part of it (0023, 0030).
- **Keel Cloud is in no application image.** It is its own service on its
  own appliances (0046). An application image carries at most the small
  node side client that talks to it when a key is configured.

## WordPress per mode

| | simple | cloud simple | cloud advanced |
| --- | --- | --- | --- |
| MariaDB | local, enabled | local: primary on node A, replica on node B | installed and **disabled**; WordPress consumes Keel MariaDB appliances discovered on the mesh (0026, 0033) |
| wp-content | local | in one LXC (0028) | replicated through Syncthing (0032) |
| Web tier | Nginx only | Nginx, the WAF (Coraza) and Anubis | as cloud simple |
| CrowdSec | disabled | enabled | enabled |
| WireGuard | disabled | enabled | enabled |
| etcd | disabled | disabled | enabled |

The Core and Web rows are the tables of 0041, inherited unchanged; what
WordPress adds is the MariaDB and wp-content rows.

## Why one image

- **Layers are content addressed and shared.** Core, Web and PHP are
  downloaded once per host and reused by every application on it, and an
  update downloads only the layer that changed.
- **Two images per application would share about 90% of their bytes**
  while doubling the builds, the tests, the releases and the
  documentation.
- **Sizes.** Measured: the Core layer `.tar.zst` is about 386 MB (step 8),
  and the old WordPress B4 image, which carried Apache and MariaDB, was
  411 MB. Estimated: WordPress on Keel PHP with the embedded MariaDB at
  450 to 600 MB, to be measured in Phase 4.

## When to revisit

An application only variant, without the embedded database, may be added
later if cloud advanced is deployed at a scale where the disabled MariaDB
(about 150 MB of disk) matters.

## What this amends

- **0013, "The catalog shape"** and **0041, decision 3**: confirmed for
  applications. An image is not split by topology, so not by installation
  mode either.
- **0033**: "embedded in a simple installation" is read as embedded in the
  image in every mode, enabled in simple and cloud simple and disabled in
  cloud advanced.
- **0043**: one image per application means one `.tar.zst` and one ISO
  per application release, under the names of section 4.
