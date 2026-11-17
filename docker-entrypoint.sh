#!/bin/sh
# A volume is mounted root-owned, and the agent runs as an unprivileged user: hand the
# data directory over, then drop privileges for good.
set -eu
DATA_DIR="${DATA_DIR:-/data}"
mkdir -p "$DATA_DIR"
chown -R agent:agent "$DATA_DIR"
exec setpriv --reuid=agent --regid=agent --init-groups "$@"
