#!/bin/bash
# Auto-pull the hermesagent repo on the VPS every 30s.
# Cron entry: * * * * * /opt/data/hermesagent/pipelines/ugc-ad/scripts/vps_autopull.sh  (cron-30s extended below)
set -e
cd /opt/data/hermesagent
# use token from env — must be set up in root's crontab or systemd env
OLD=$(git rev-parse HEAD 2>/dev/null || echo "")
git -c safe.directory=/opt/data/hermesagent fetch --quiet origin main
git -c safe.directory=/opt/data/hermesagent reset --hard --quiet origin/main
NEW=$(git rev-parse HEAD)
if [ "$OLD" != "$NEW" ]; then
  echo "$(date -u +%FT%TZ)  pulled $OLD → $NEW" >> /opt/data/hermesagent-autopull.log
fi
