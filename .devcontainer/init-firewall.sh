#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# ---------------------------------------------------------------------------
# ORDER MATTERS. This script runs in three phases:
#
#   PHASE 1  build a complete allowlist in a scratch ipset, touching nothing
#   PHASE 2  swap it into place atomically; build the iptables rules on the
#            first run only, leave them alone on a re-run
#   PHASE 3  verify
#
# Upstream does the reverse - flush first, build second - which means any
# failure between the two leaves the container with no working firewall AND no
# network. Two real incidents came out of that ordering:
#
#   2026-09-16  statsig.anthropic.com went NXDOMAIN; `exit 1` fired after the
#               flush and two sandboxes ran completely unrestricted (fail OPEN)
#   2026-09-17  a re-run inside a live container destroyed the live ipset and
#               flushed the rules, so the GitHub fetch had no route, hung for
#               two minutes, and `set -e` killed the script before
#               api.anthropic.com was re-added (fail CLOSED, container
#               stranded, presented as the model looping)
#
# With build-then-swap, every failure in phase 1 is harmless: the previous
# rules stay in force and the container keeps working.
#
# On a RE-RUN the iptables rules are not rebuilt at all. Rebuilding means
# policies at ACCEPT with the rules flushed for the span of the rebuild, and
# during that span anything in the container can reach any host. Nothing the
# rules depend on changes inside a running container - the extra ports are
# baked into the image, the host network is fixed - so only the resolved IPs
# go stale, and the atomic ipset swap has already refreshed those. Skipping
# the rebuild is what makes a re-run safe to invoke at any time.
# ---------------------------------------------------------------------------

NEW_SET="allowed-domains-new"
LIVE_SET="allowed-domains"

cleanup_scratch() {
    ipset destroy "$NEW_SET" 2>/dev/null || true
}
trap cleanup_scratch EXIT

# True when a previous run finished phase 2. Every rule is appended in a fixed
# order and the REJECT is last, so its presence alongside DROP policies means
# the rule set is complete, not a partial one from a run that died mid-flight.
rules_in_place() {
    iptables -S INPUT  | grep -q '^-P INPUT DROP$'  || return 1
    iptables -S OUTPUT | grep -q '^-P OUTPUT DROP$' || return 1
    iptables -C OUTPUT -m set --match-set "$LIVE_SET" dst -j ACCEPT 2>/dev/null || return 1
    iptables -C OUTPUT -j REJECT --reject-with icmp-admin-prohibited 2>/dev/null || return 1
}

# ===========================================================================
# PHASE 1 - build the new allowlist. Nothing here touches the live firewall.
# ===========================================================================

cleanup_scratch                       # in case a previous run died mid-flight
ipset create "$NEW_SET" hash:net

# Per-project additions, baked into the image at build time (NOT bind-mounted:
# a writable allowlist could be edited by an agent running in this container,
# which has passwordless sudo for this script). Adding a domain therefore
# requires a container rebuild, deliberately.
#
# firewall-extras.conf may define:
#   EXTRA_DOMAINS=( "pypi.org" "files.pythonhosted.org" )
#   EXTRA_INBOUND_TCP_PORTS=( 8100 4200 )
EXTRA_DOMAINS=()
EXTRA_INBOUND_TCP_PORTS=()
EXTRAS_FILE="/usr/local/bin/firewall-extras.conf"
if [ -f "$EXTRAS_FILE" ]; then
    echo "Loading project extras from $EXTRAS_FILE"
    # shellcheck source=/dev/null
    source "$EXTRAS_FILE"
else
    echo "No firewall-extras.conf; using the common allowlist only"
fi

# --- GitHub ranges ---------------------------------------------------------
# --max-time matters: without it a blocked connection hangs silently until the
# TCP timeout, which is what made the 2026-09-17 failure so opaque.
echo "Fetching GitHub IP ranges..."
gh_ranges=$(curl -s --max-time 30 https://api.github.com/meta)
if [ -z "$gh_ranges" ]; then
    echo "ERROR: Failed to fetch GitHub IP ranges"
    exit 1
fi

if ! echo "$gh_ranges" | jq -e '.web and .api and .git' >/dev/null; then
    echo "ERROR: GitHub API response missing required fields"
    exit 1
fi

echo "Processing GitHub IPs..."
while read -r cidr; do
    if [[ ! "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "ERROR: Invalid CIDR range from GitHub meta: $cidr"
        exit 1
    fi
    echo "Adding GitHub range $cidr"
    ipset add "$NEW_SET" "$cidr" -exist
done < <(echo "$gh_ranges" | jq -r '(.web + .api + .git)[]' | aggregate -q)

# --- Named domains ---------------------------------------------------------
for domain in \
    "registry.npmjs.org" \
    "api.anthropic.com" \
    "sentry.io" \
    "statsig.com" \
    "marketplace.visualstudio.com" \
    "vscode.blob.core.windows.net" \
    "update.code.visualstudio.com" \
    ${EXTRA_DOMAINS[@]+"${EXTRA_DOMAINS[@]}"}; do
    echo "Resolving $domain..."
    ips=$(dig +noall +answer A "$domain" | awk '$4 == "A" {print $5}')
    if [ -z "$ips" ]; then
        # A domain that no longer resolves must not abort the run. Harmless in
        # phase 1 - the live rules are untouched - but skipping keeps a dead
        # entry from blocking every other domain behind it.
        echo "WARNING: Failed to resolve $domain - skipping"
        continue
    fi

    while read -r ip; do
        if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "ERROR: Invalid IP from DNS for $domain: $ip"
            exit 1
        fi
        echo "Adding $ip for $domain"
        ipset add "$NEW_SET" "$ip" -exist
    done < <(echo "$ips")
done

# --- Host network ----------------------------------------------------------
HOST_IP=$(ip route | grep default | cut -d" " -f3)
if [ -z "$HOST_IP" ]; then
    echo "ERROR: Failed to detect host IP"
    exit 1
fi
HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
echo "Host network detected as: $HOST_NETWORK"

# Sanity check before committing: an allowlist this small means something went
# wrong upstream of here, and applying it would break the container.
NEW_COUNT=$(ipset list "$NEW_SET" | awk '/Number of entries/ {print $4}')
echo "New allowlist holds $NEW_COUNT entries"
if [ "$NEW_COUNT" -lt 10 ]; then
    echo "ERROR: new allowlist has only $NEW_COUNT entries - refusing to apply"
    exit 1
fi

# ===========================================================================
# PHASE 2 - commit. From here on the live firewall is being modified.
# ===========================================================================

# Capture Docker's internal DNS rules BEFORE flushing so they can be restored.
DOCKER_DNS_RULES=$(iptables-save -t nat | grep "127\.0\.0\.11" || true)

# Swap the new set into place. `ipset swap` is atomic and needs both sets to
# exist, so create an empty live set on the very first run.
ipset create "$LIVE_SET" hash:net -exist
ipset swap "$NEW_SET" "$LIVE_SET"
echo "Allowlist swapped into place ($NEW_COUNT entries)"

if rules_in_place; then
    echo "Rules already in place from a previous run - allowlist refreshed, rules untouched"
else

    # Reset policies to ACCEPT BEFORE flushing. `iptables -F` flushes RULES but
    # not POLICIES; without this a rebuild over a partial previous run leaves
    # OUTPUT at DROP with no ACCEPT rules, blocking everything until the rules
    # below are rebuilt.
    iptables -P INPUT ACCEPT
    iptables -P FORWARD ACCEPT
    iptables -P OUTPUT ACCEPT

    iptables -F
    iptables -X
    iptables -t nat -F
    iptables -t nat -X
    iptables -t mangle -F
    iptables -t mangle -X

    # Selectively restore ONLY internal Docker DNS resolution
    if [ -n "$DOCKER_DNS_RULES" ]; then
        echo "Restoring Docker DNS rules..."
        iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
        iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
        echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
    else
        echo "No Docker DNS rules to restore"
    fi

    # DNS, SSH and loopback
    iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
    # TCP DNS as well: large responses exceed the UDP limit and trigger a retry
    iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
    iptables -A INPUT  -p udp --sport 53 -j ACCEPT
    iptables -A OUTPUT -p tcp --dport 22 -j ACCEPT
    iptables -A INPUT  -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT
    iptables -A INPUT  -i lo -j ACCEPT
    iptables -A OUTPUT -o lo -j ACCEPT

    # Host network
    iptables -A INPUT  -s "$HOST_NETWORK" -j ACCEPT
    iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT

    # Per-project inbound TCP (dev servers reached from the host)
    for port in ${EXTRA_INBOUND_TCP_PORTS[@]+"${EXTRA_INBOUND_TCP_PORTS[@]}"}; do
        echo "Allowing inbound TCP $port"
        iptables -A INPUT -p tcp --dport "$port" -j ACCEPT
    done

    # Default deny
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT DROP

    iptables -A INPUT  -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    iptables -A OUTPUT -m set --match-set "$LIVE_SET" dst -j ACCEPT

    # REJECT rather than DROP so blocked calls fail fast instead of hanging
    iptables -A OUTPUT -j REJECT --reject-with icmp-admin-prohibited
fi

# ===========================================================================
# PHASE 3 - verify. Without these a partially applied firewall looks exactly
# like a working one.
# ===========================================================================

echo "Firewall configuration complete"
echo "Verifying firewall rules..."
if curl --connect-timeout 5 https://example.com >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - was able to reach https://example.com"
    exit 1
else
    echo "Firewall verification passed - unable to reach https://example.com as expected"
fi

if ! curl --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - unable to reach https://api.github.com"
    exit 1
else
    echo "Firewall verification passed - able to reach https://api.github.com as expected"
fi
