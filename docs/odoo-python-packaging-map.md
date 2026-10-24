# Odoo 18.0 + OCA: Python libraries to package for Debian 13

Measured 2026-09-30 on a Debian 13 (trixie) host with `trixie`,
`trixie-updates`, `trixie-security` and `trixie-backports` (main only).
Goal: run Odoo 18.0 plus the OCA catalogue of decision 0022 using only
trixie packages plus packages in Keel's archive, packaged the Debian Python
Team way so they can later go to Debian.

Inputs, all at branch 18.0: `odoo/odoo` at `87872ab5f9` (requirements.txt,
debian/control) and 54 OCA repositories (commits listed under Sources).

## Method

- Odoo core: `requirements.txt` lines whose markers match Linux and Python
  3.13 (trixie's Python), plus `debian/control` Depends.
- OCA: `requirements.txt` of each repo, and the `external_dependencies`
  of every `__manifest__.py` (all 1,903 manifests parsed with
  `ast.literal_eval`, not sampled).
- **OCA's requirements.txt is generated from the manifests, and it holds.**
  Every file starts with `# generated from manifests external_dependencies`;
  for all 32 repos that have one, its set equals the union of the manifests'
  `external_dependencies.python` exactly. The 22 repos without the file have
  no Python external dependency in any manifest. `test-requirements.txt`
  (odoo_test_helper, vcrpy, xmlunittest, signxml, ...) is CI only and is
  left out.
- PyPI name to Debian package: dh-python's `cpython3_fallback` map (from
  trixie's dh-python 6.20250414), then `python3-<name>`, then
  `apt-cache policy`. Where the PyPI and Debian names differ, the `.deb` was
  downloaded and its `*.dist-info`/`*.egg-info` name checked, because that
  is what Odoo checks (below).
- Missing libraries: PyPI JSON API (latest version, license, wheel tags,
  `requires_dist` evaluated for Linux/CPython 3.13, upload date), resolved
  recursively to a closure against trixie. Other Debian suites via the
  ftp-master madison API; WNPP via the open ITP/RFP lists on
  debian.org/devel/wnpp; upstream liveness via GitHub `pushed_at`.

**Why names and versions matter.** Odoo 18 installs a module only if
`importlib.metadata.version(<name>)` finds the distribution named in the
manifest and the version satisfies its specifier; otherwise it falls back to
`importlib.import_module(<name>)` (`odoo/modules/module.py`,
`check_python_external_dependency`). So a trixie package with a different
distribution name, or a version outside the manifest's range, blocks the
module even if the code would run.

## 1. Summary

| Measure | Count |
|---|---|
| Distinct runtime libraries (Odoo core + catalogue) | **96** (Odoo core 44, OCA 65, 13 shared) |
| Odoo core libraries missing from trixie | **0** (confirms decision 0022; `python3-renderpm` is provided by `python3-reportlab`) |
| In trixie by name | 65 |
| In trixie but unusable as is | 2: `pycryptodome` (Debian ships the `Cryptodome` namespace only) and `deepdiff<8` (trixie has 8.1.1) |
| Missing from trixie by name | 31 |
| Missing that need no package | 1: `dataclasses` (stdlib since 3.7; Odoo's import fallback accepts it with a warning) |
| **Missing roots to package** | **30** |
| Extra missing in the transitive closure | 4: `xsdata`, `requests-pkcs12`, `pyjon.utils`, `zplgrf` (plus `narwhals` only if bokeh moves past the pinned 3.6.3) |
| **Missing incl. closure** | **34** (36 if the two unusable ones are packaged rather than patched in OCA) |
| Pure Python / compiled (the 34, at the versions needed) | 34 pure / 0 compiled. `pyzbar` is arch-all but loads `libzbar0t64` via ctypes; `numpy-financial` 1.1.0 is compiled but the manifest pins `<=1.0.0`, which is pure |
| Already in Debian testing/sid, not in trixie | 2: `pyzbar` 0.1.9-3, `xsdata` 26.2-1 (nfelib needs `<26`) |
| Was in Debian, removed | 1: `workalendar` (removed from unstable 2024-04-26, "Abandoned upstream; leaf-package") |
| Licenses that block Debian main | **none**. All are MIT, BSD, ISC, LGPL, GPL or AGPL. Caveats in section 4 (conflicting license metadata, missing license files, minified JS, government XSDs) |

Repositories whose modules need nothing outside trixie: queue,
partner-contact, l10n-portugal, l10n-germany, l10n-netherlands, l10n-mexico,
l10n-ecuador, stock-logistics-tracking, stock-logistics-barcode,
stock-logistics-reporting, e-commerce, sale-reporting, crm,
purchase-workflow, account-financial-reporting, account-payment,
bank-payment, account-reconcile, field-service, helpdesk, project,
timesheet, hr, hr-attendance, hr-holidays, payroll, manufacture, pos,
contract, dms. l10n-chile, l10n-peru and l10n-canada have **no modules** at
18.0 (not verified whether they live elsewhere).

## 2. What is missing, by group

Columns: version needed (manifest specifier; "any" if none), latest on
PyPI, license (PyPI metadata; GitHub SPDX when it differs), wheel type,
missing transitive deps, date of the latest PyPI release, Debian/WNPP status.
"none" in WNPP means no open ITP/RFP found (best effort, open lists only).

### Odoo core

Nothing missing. All 44 requirements (Python 3.13 lines) map to trixie
packages. Odoo's pins are not enforced at runtime and trixie differs on
several (section 4); decision 0022 already measured Odoo running on them.

### Base (server-tools, server-ux, web, reporting-engine, queue, partner-contact, product-attribute)

| Library | Needed by | Version needed | PyPI latest | License | Wheel | Missing deps | Last release | Debian / WNPP |
|---|---|---|---|---|---|---|---|---|
| openupgradelib | server-tools, product-attribute (and 7 verticals, l10n-italy) | any | 3.13.7 | AGPL-3.0 | pure | none (lxml, cssselect in trixie) | 2026-08-25 | none |
| odoo-test-helper | server-tools (`base_sequence_option`, runtime) | any | 2.1.3 | LGPLv3+ (no license file in repo) | pure | none | 2026-02-20 | none |
| pygount | server-tools (`module_analysis`) | any | 3.2.0 | BSD-3-Clause | pure | none if 3.1.0 (3.1.1+ needs rich>=14, trixie 13.9.4) | 2026-04-08 | none |
| pysftp | server-tools (`auto_backup`) | any | 0.2.9 | BSD | sdist only | none (paramiko) | 2016-07-06 | none; upstream repo gone |
| dataclasses | server-tools (`upgrade_analysis`) | any | 0.8 | Apache | pure | none | 2020-11-13 | not needed (stdlib) |
| pdf2image | server-ux (2 modules) | any | 1.17.0 | MIT | pure | none (needs poppler-utils) | 2024-01-07 | **ITP #1087742** (681 days, idle 304 days) |
| pyzbar | server-ux (2 modules) | any | 0.1.9 | MIT | pure + ctypes (libzbar0t64) | none | 2022-03-15 | in testing/sid 0.1.9-3; backport |
| bokeh | web (`web_widget_bokeh_chart`) | ==3.6.3 | 3.10.0 | BSD-3-Clause | pure, ships compiled BokehJS | none at 3.6.3 (contourpy etc. in trixie); `narwhals` from 3.7 | 2026-08-18 | **RFP #756017** (4,449 days) |
| mpld3 | web (`web_widget_mpld3_chart`) | ==0.5.10 | 0.5.12 | BSD-3-Clause | pure, vendors d3 v3+v5 minified | none (matplotlib in trixie) | 2025-11-05 | none |
| py3o.template | reporting-engine (2 modules) | any | 0.10.0 | MIT (no license file in wheel) | pure | **pyjon.utils** | 2019-03-15 | none; OCA/py3o.template fork active, no release since 0.10.0 |
| py3o.formats | reporting-engine (2 modules) | any | 0.3 | MIT | py2 wheel, sdist | none | 2015-06-02 | none |
| pyjon.utils (dep) | py3o.template | >0.6 | 0.7 | MIT | pure | none | 2014-10-10 | none |

### Verticals

| Library | Needed by | Version needed | PyPI latest | License | Wheel | Missing deps | Last release | Debian / WNPP |
|---|---|---|---|---|---|---|---|---|
| openupgradelib | stock-logistics-warehouse, stock-logistics-workflow, delivery-carrier, sale-workflow, account-invoicing, mis-builder | any | see Base | | | | | |
| easypost | delivery-carrier (`delivery_easypost_oca`) | ==7.15.0 | 10.7.0 | MIT | pure | none | 7.15.0: 2024-01-08 | none |
| roulier | delivery-carrier (`delivery_roulier`) | any | 1.1.1 | AGPL-3.0 | pure | **zplgrf** | 2024-04-17 | none |
| zplgrf (dep) | roulier | any | 1.6.0 | GPL-3.0 | sdist only | none (pillow) | 2019-10-08 | none |
| altcha | website (`website_altcha`) | any | 2.1.0 | MIT | pure | none | 2026-07-27 | none |
| numpy-financial | account-financial-tools (`account_loan`) | <=1.0.0 | 1.1.0 | BSD-3-Clause | 1.0.0 pure; 1.1.0 compiled | none | 1.0.0: 2019-10-18; 1.1.0: 2026-09-15 | none |

### Localizations

| Library | Needed by | Version needed | PyPI latest | License | Wheel | Missing deps | Last release | Debian / WNPP |
|---|---|---|---|---|---|---|---|---|
| erpbrasil.base | l10n-brazil (17 modules) | >=2.4.2 | 2.4.2 | MIT | pure | none (declares `wheel` at runtime) | 2026-07-04 | none |
| erpbrasil.assinatura | l10n-brazil | any | 1.8.0 | MIT | pure, nspkg | none (signxml, cryptography in trixie) | 2025-08-12 | none |
| erpbrasil.transmissao | l10n-brazil | any | 1.1.0 | MIT | pure, nspkg | erpbrasil.assinatura | 2023-08-30 | none |
| erpbrasil.edoc | l10n-brazil | any | 3.1.1 | MIT | pure, nspkg | the three erpbrasil above | 2026-01-08 | none |
| nfelib | l10n-brazil (nfe, mdfe, nfe_dfe) | >=2.6.0 | 2.6.0 | MIT | pure, ships 237 XSDs | **xsdata** (`>=24.3,<26`) | 2026-09-26 | none |
| nfselib.paulistana | l10n-brazil | any | 0.3.0 | MIT | pure, nspkg | none | 2026-01-11 | none |
| brazil-fiscal-client | l10n-brazil (`l10n_br_nfe_dfe`) | any | 0.3.0 | MIT | pure | **xsdata**, **requests-pkcs12** | 2025-11-26 | none |
| brazilcep | l10n-brazil (`l10n_br_zip`) | any | 7.0.1 | MIT | pure | none (aiohttp in trixie) | 2025-08-16 | none |
| brazilfiscalreport | l10n-brazil (nfe, mdfe, nfe_dfe) | >=1.1.0 | 1.1.1 | PyPI: AGPLv3; GitHub: LGPL-3.0 | pure | none if 1.1.0 (1.1.1 needs fpdf2>=2.8.6, trixie 2.8.3) | 2026-09-29 | none |
| workalendar | l10n-brazil (`l10n_br_resource`) | any | 17.0.0 | MIT | pure | none (convertdate, lunardate, pyluach in trixie) | 2023-01-01 | was in bookworm; **removed as abandoned**; stale ITP #886223 |
| xsdata (dep) | nfelib, brazil-fiscal-client | >=24.3,<26 | 26.2 | MIT | pure | none | 25.7: 2025-07-06 | sid 26.2-1 (too new for nfelib) |
| requests-pkcs12 (dep) | brazil-fiscal-client | any | 1.27 | ISC | pure | none if <=1.25 (1.26+ needs requests>=2.32.5, trixie 2.32.3) | 2025-09-07 | none |
| suds-py3 | l10n-spain (`delivery_gls_asm`) | any | 1.4.5.0 | LGPL-3.0 | pure (wheel ships .pyc) | none | 2021-11-15 | none; clashes with `python3-suds` (see 4) |
| xmlsig | l10n-spain (`l10n_es_facturae`), l10n-colombia | any | 1.0.1 | LGPL-3.0 | pure | none | 2023-05-10 | none |
| pycryptodome (`Crypto` namespace) | l10n-spain (`payment_redsys`) | any | 3.23.0 | BSD / Public Domain | compiled | none | n/a | trixie ships only pycryptodomex (see 4) |
| deepdiff <8 | l10n-spain (`l10n_es_aeat_sii_match`) | <8 | 9.1.0 (7.0.1 last 7.x) | MIT | pure | none (ordered-set 4.1.0 in trixie) | 7.0.1: 2024-04-08 | trixie 8.1.1 conflicts (see 4) |
| openupgradelib | l10n-italy (11 modules) | any | see Base | | | | | |
| pyfrdas2 | l10n-france (`l10n_fr_das2`) | >=0.10 | 0.10 | LGPLv2+ (no license file) | pure | none (python-gnupg in trixie) | 2025-11-19 | none |
| pycoda | l10n-belgium (`account_statement_import_coda`) | any | 1.1.0 | GPL-3.0+ | pure | none | 2022-05-19 | none |
| ebilling-postfinance | l10n-switzerland (`ebill_postfinance`) | any | 0.1.1 | PyPI: AGPLv3+; GitHub: MIT | pure, ships .cer files | none | 2023-12-01 | none |
| ach | l10n-usa (`account_banking_ach_base`) | any | 0.2 | MIT | sdist only | none | 2014-08-05 | none |

Portugal, Germany, Netherlands, Mexico, Ecuador: nothing missing. Chile,
Peru, Canada: no modules at 18.0.

## 3. Proposed packaging order

Dependencies first inside each step. Versions are the ones that fit trixie.

1. **Base**: openupgradelib, pdf2image, pyzbar (backport of sid 0.1.9-3),
   pygount 3.1.0, odoo-test-helper, pyjon.utils, py3o.formats,
   py3o.template, pysftp, mpld3 0.5.10, bokeh 3.6.3. Leave bokeh and mpld3
   last: they carry built/minified JS (section 4) and serve one widget
   each.
2. **Brazil** (12 packages): xsdata 25.7, requests-pkcs12 1.25,
   erpbrasil.base, erpbrasil.assinatura, erpbrasil.transmissao,
   erpbrasil.edoc, nfelib, nfselib.paulistana, brazil-fiscal-client,
   brazilcep, brazilfiscalreport 1.1.0, workalendar.
3. **Spain**: xmlsig, then resolve suds-py3, pycryptodome and deepdiff<8
   (preferably by OCA patches, section 4; otherwise Keel packages).
4. **Portugal**: nothing to package.
5. **Rest of localizations**: pyfrdas2 (France), pycoda (Belgium),
   ebilling-postfinance (Switzerland), ach (USA); Colombia reuses xmlsig;
   Italy reuses openupgradelib.
6. **Verticals**: altcha (website), numpy-financial 1.0.0
   (account-financial-tools), zplgrf + roulier and easypost 7.15.0
   (delivery-carrier).

**Best first candidates for Debian** (generic, useful beyond Odoo, pure
Python, DFSG-free, alive upstream):

| Library | Why |
|---|---|
| pdf2image | widely used, MIT, pure; an ITP already exists (#1087742), so offer help to its owner rather than filing a new one |
| pyzbar | already in sid; only a trixie-backports upload is needed |
| xsdata | already in sid (26.2); a Keel 25.7 is needed for nfelib, but sid's package is the base |
| altcha | small, MIT, active (2026-07), generic web CAPTCHA library |
| numpy-financial | NumPy project, BSD, active (2026-09) |
| requests-pkcs12 | ISC, tiny, generic requests add-on |
| brazilcep | MIT, active, generic Brazilian postal-code client |
| xmlsig | LGPL-3.0, generic XML-DSig in pure Python; last release 2023 but repo active 2026 |
| pygount | BSD, active, generic SLOC counter |
| openupgradelib | AGPL, active (OCA), but Odoo-specific; good fit if Debian ever ships Odoo |

Keep in Keel only (low value for Debian or weak upstream): ach, pysftp,
zplgrf, pyjon.utils, py3o.formats, suds-py3, workalendar (Debian removed it
as abandoned), odoo-test-helper, and pinned-old versions (easypost 7.15.0,
bokeh 3.6.3, mpld3 0.5.10, deepdiff 7).

## 4. Problems found

**Present in trixie but blocking a module**

- `pycryptodome` (l10n-spain `payment_redsys`, `from Crypto.Cipher import
  DES3`): trixie's `python3-pycryptodome` ships only `Cryptodome/` with
  metadata `pycryptodomex-3.20.0`. Both Odoo's metadata lookup and the
  import fail. Fix: OCA patch to `Cryptodome` + `pycryptodomex`, or a Keel
  package providing `Crypto` (compiled, and Debian deliberately avoids that
  namespace).
- `deepdiff<8` (l10n-spain `l10n_es_aeat_sii_match`): trixie has 8.1.1, so
  the manifest check fails. A Keel deepdiff 7 would replace a trixie
  package that `python3-trx-python` and `sublime-music` depend on. Prefer an
  OCA patch lifting the cap (not verified that the module works with 8.x).
- `suds-py3` (l10n-spain `delivery_gls_asm`): trixie's `python3-suds` is
  suds-community 1.2.0 (metadata `suds_community`), same `suds` module
  name. Packaging suds-py3 would file-conflict with `python3-suds`. Prefer an
  OCA manifest change to `suds-community` (not verified that the module
  works with it).
- `pyzbar` is not `python3-zbar`: trixie's `python3-zbar` is zbar's own
  binding (different API, metadata `zbar`).

**Version conflicts with trixie (use the older upstream)**

- nfelib 2.6.0 needs `xsdata<26`; sid has 26.2. Package xsdata 25.7.
- brazilfiscalreport 1.1.1 (2026-09-29) needs `fpdf2>=2.8.6`; trixie has
  2.8.3. Use 1.1.0 (OCA needs `>=1.1.0`).
- requests-pkcs12 1.26+ needs `requests>=2.32.5`; trixie has 2.32.3. Use
  1.25 (needs cryptography>=42; trixie 43.0.0). OCA's own CI pins `<1.23`.
- pygount 3.1.1+ needs `rich>=14`; trixie has 13.9.4. Use 3.1.0.
- Odoo core pins differ from trixie on cbor2, cryptography, decorator,
  docutils, greenlet, idna, jinja2, libsass, num2words, openpyxl, polib,
  psutil, pyopenssl, python-dateutil, python-stdnum, qrcode, reportlab,
  requests, urllib3, vobject, werkzeug. These are pip pins, not runtime
  checks; Odoo's debian/control is unversioned.
- `python3-phonenumbers` in trixie is 8.12.57 (2022); PyPI is 9.0.40. No
  manifest caps it, but its number metadata is stale (affects
  partner-contact and l10n-brazil validation; impact not measured).

**Abandoned or weak upstreams**

- workalendar: last release 2023-01-01; Debian removed it 2024-04-26 as
  abandoned. l10n-brazil `l10n_br_resource` depends on it.
- pysftp: last release 2016; the Bitbucket repo is gone.
- ach (2014), pyjon.utils (2014), py3o.formats (2015), py3o.template (2019;
  original Bitbucket gone, OCA/py3o.template is active but has not
  released), zplgrf (2019), suds-py3 (2021), pycoda (2022),
  erpbrasil.transmissao (2023), ebilling-postfinance (2023).
- `dataclasses` in server-tools `upgrade_analysis` is a Python 3.6 backport;
  it should be dropped from the manifest.

**Licensing and DFSG points to check before Debian**

- No license blocks main. To clarify with upstream: brazilfiscalreport
  (PyPI AGPLv3 vs GitHub LGPL-3.0), ebilling-postfinance (PyPI AGPLv3+ vs
  GitHub MIT), pyfrdas2 and odoo-test-helper (no license file in repo),
  py3o.template (no license file in wheel).
- nfelib ships 237 Brazilian tax-authority XSD schemas; their copyright and
  licence status is not verified. xsdata and xmlsig ship W3C/SOAP schemas
  (usually fine).
- bokeh ships BokehJS built from TypeScript (the 12-year-old RFP is
  presumably stuck on this); mpld3 vendors minified d3 v3 and v5. Debian
  needs these rebuilt from source or replaced by `libjs-d3`.
- ebilling-postfinance ships PostFinance `.cer` certificates; pyfrdas2
  ships DGFiP PGP keys (`.asc`). Data files, acceptable, but document them.

**Packaging oddities**

- erpbrasil.assinatura, .transmissao, .edoc and nfselib.paulistana use
  pkg_resources-style namespace packages (`*-nspkg.pth`); Debian packages
  must share `erpbrasil/__init__.py` / `nfselib/__init__.py` cleanly.
- roulier installs a top-level `tests` package and odoo-test-helper a
  top-level `test_addons`; both must be kept out of `dist-packages`.
- suds-py3's wheel contains `.pyc` files; build from the sdist.
- erpbrasil.base declares `wheel` as a runtime dependency (harmless;
  `python3-wheel` is in trixie).
- odoo-test-helper is a runtime dependency of server-tools
  `base_sequence_option` (a test helper at runtime).

**Non-Python system dependencies named in manifests** (outside this map,
noted because they fail on trixie main): `openjdk-8-jdk` (not in trixie)
and `ttf-mscorefonts-installer` (contrib) for three l10n-spain ATC modules;
`libatlas-base-dev` (not in trixie) for account-financial-tools
`account_loan`; `libzbar0` is `libzbar0t64` in trixie.

**Not verified**: WNPP closed bugs and ITPs filed under other names;
whether the four "prefer an OCA patch" cases work with trixie's versions;
licence of nfelib's XSDs; actual runtime of any module (this map is
metadata only).

## Sources

- Odoo: github.com/odoo/odoo 18.0 `requirements.txt`, `debian/control`,
  `odoo/modules/module.py` (`check_python_external_dependency`), commit
  `87872ab5f9`.
- OCA 18.0 heads used: server-tools 88d1919, server-ux 3f3b8df, web
  73d2c93, reporting-engine 7a156ca, queue d3ce20a, partner-contact 78a933a,
  product-attribute 0842235, l10n-brazil edd68ed, l10n-spain c60280b,
  l10n-portugal f2aa401, l10n-italy f3e2cf6, l10n-france 24a6969,
  l10n-germany 83e8d6a, l10n-netherlands d8606ef, l10n-belgium ea13ac6,
  l10n-switzerland f3f39f8, l10n-mexico 0d4b530, l10n-colombia fbaf04a,
  l10n-chile 1bf1935, l10n-peru e13f594, l10n-ecuador 3315e32, l10n-usa
  c06ce9e, l10n-canada f5a0496, stock-logistics-warehouse ef117ac,
  stock-logistics-workflow feb31da, stock-logistics-tracking 0392600,
  stock-logistics-barcode d81c596, stock-logistics-reporting 32b3e60,
  delivery-carrier 3952543, website 7e44dc3, e-commerce 5afd694,
  sale-workflow 2eaec1c, sale-reporting 5ea7741, crm 07c2485,
  purchase-workflow 82455ea, account-financial-tools 06d13e3,
  account-financial-reporting 6843f6a, account-invoicing 9d59553,
  account-payment 8de2cff, bank-payment acbe217, account-reconcile bfc46f8,
  mis-builder 4f9eef0, field-service d6b4391, helpdesk 04bae4f, project
  0160470, timesheet 7dbc804, hr 33ad2e2, hr-attendance a8f2e4b,
  hr-holidays 94154c8, payroll 4c71cd4, manufacture 75d07dc, pos 5b5ad48,
  contract 104db60, dms 2d803cc.
- Debian: `apt-cache policy` on trixie; dh-python 6.20250414
  `cpython3_fallback`; api.ftp-master.debian.org/madison;
  tracker.debian.org (pyzbar, python-xsdata, python-workalendar);
  ftp-master.debian.org/removals-2024.txt; debian.org/devel/wnpp
  `being_packaged` and `requested`.
- PyPI JSON API (`pypi.org/pypi/<name>/json` and `/<version>/json`);
  wheel contents inspected for vendored files; GitHub API for upstream
  activity and SPDX licence.
