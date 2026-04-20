#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
NETOPEER_SCRIPTS_DIR=/usr/local/share/netopeer2/scripts
PIDFILE=/tmp/netopeer2-server.pid

if ! command -v netopeer2-server >/dev/null 2>&1; then
    echo "netopeer2-server not found in PATH" >&2
    exit 1
fi

if ! command -v sysrepocfg >/dev/null 2>&1; then
    echo "sysrepocfg not found in PATH" >&2
    exit 1
fi

if [[ ! -d "$NETOPEER_SCRIPTS_DIR" ]]; then
    echo "Missing netopeer2 helper scripts: $NETOPEER_SCRIPTS_DIR" >&2
    exit 1
fi

current_unprivileged_port=$(cat /proc/sys/net/ipv4/ip_unprivileged_port_start)
if (( current_unprivileged_port > 830 )); then
    echo "Port 830 is still privileged on this machine." >&2
    echo "Run once per boot:" >&2
    echo "  sudo sysctl -w net.ipv4.ip_unprivileged_port_start=830" >&2
    exit 1
fi

pushd "$NETOPEER_SCRIPTS_DIR" >/dev/null
bash merge_hostkey.sh
bash merge_config.sh || true
popd >/dev/null

existing_pid=$(pgrep -a -f "netopeer2-server" | awk 'NR == 1 { print $1 }')
if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "netopeer2-server already running with pid $existing_pid"
    exit 0
fi

if [[ -f "$PIDFILE" ]]; then
    old_pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
        echo "netopeer2-server already running with pid $old_pid"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

exec netopeer2-server -d -v2 -p "$PIDFILE"
