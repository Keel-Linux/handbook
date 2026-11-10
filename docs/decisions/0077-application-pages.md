# 0077: A documentation page for each application, at keellinux.org/apps/NAME/

Date: 2026-11-05
Status: **decided by the maintainer, 2026-11-05** (each application has a page
on the site with its documentation, published "as a git pages", one for each
application; the Applications page links to it; the address
`keellinux.org/apps/NAME/`).

## Decided

- Each appliance repository on git.pop.coop has a branch `pages`: the
  static HTML of its documentation page. git.pop.coop is the source; the
  GitHub mirror is not used for it. Forgejo 14 has no Pages service, so
  the site serves the branch itself.
- The public services VM keeps one checkout of each `pages` branch under
  `/srv/apps/NAME` and updates it with a timer, `git pull --ff-only`, as
  `keel-site-pull` does for the site. nginx serves it at
  `https://keellinux.org/apps/NAME/`.
- The Applications page of the site (`appliances.html`) links each
  application to its page.

## What a page holds

- What the application is, and its versions.
- How to install it: the LXC template and the ISO.
- The guide of each installation mode that the appliance allows (0076): one
  column for each node, the screenshot of each screen in order, and what the
  operator types or chooses under it.
- The screenshots of the web side, as the TurnKey Linux galleries have them:
  the application's front page, its back end before and after the login,
  Webmin before and after the login, the confconsole services screen, and
  the other web interfaces the appliance ships.
- The passwords the first boot asks, the services and the ports.
- The commissioning result (0075) of the image the page describes.

## How a page is made

The `pages` branch is generated from the appliance repository and from the
screenshots and records of a passing commissioning run (0075). A page never
shows an image that did not pass, and it names the sha256 of the template
and the ISO it describes. No secret is ever written to a page: the
commissioning run masks them.
