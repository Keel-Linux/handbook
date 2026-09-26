#!/bin/bash
set -euo pipefail

ORG="${ORG:-KeelLinux}"
ACCOUNT="${ACCOUNT:-marcos-mendez}"

info() { echo "INFO: $*"; }
warn() { echo "WARN: $*" >&2; }

if ! gh api "orgs/$ORG" --silent 2>/dev/null; then
    echo "FATAL: organization $ORG does not exist yet (create it at https://github.com/organizations/plan)" >&2
    exit 1
fi

TRANSFER="fab buildtasks tklbam tklbam-python-boto turnkey-pylib cdroots webmin \
lapp nginx-php-fastcgi wordpress redis ejabberd tkldev common confconsole \
inithooks turnkey-chroot tklbam-profiles moodle lamp"

FORK_INTO_ORG="turnkeylinux-apps/core turnkeylinux-apps/odoo"

for repo in $TRANSFER; do
    if gh api "repos/$ORG/$repo" --silent 2>/dev/null; then
        info "$ORG/$repo already there, skipping"
        continue
    fi
    if ! gh api "repos/$ACCOUNT/$repo" --silent 2>/dev/null; then
        warn "$ACCOUNT/$repo not found, skipping"
        continue
    fi
    info "transferring $ACCOUNT/$repo to $ORG"
    gh api -X POST "repos/$ACCOUNT/$repo/transfer" -f new_owner="$ORG" --silent
    sleep 2
done

for upstream in $FORK_INTO_ORG; do
    name="${upstream#*/}"
    if gh api "repos/$ORG/$name" --silent 2>/dev/null; then
        info "$ORG/$name already there, skipping"
        continue
    fi
    info "forking $upstream into $ORG"
    gh repo fork "$upstream" --org "$ORG" --clone=false
    sleep 2
done

info "repositories in $ORG:"
gh repo list "$ORG" --limit 100 --json name,isFork,parent \
    --template '{{range .}}{{.name}}{{"\t"}}{{if .parent}}{{.parent.nameWithOwner}}{{else}}-{{end}}{{"\n"}}{{end}}'
