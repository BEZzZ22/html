#!/usr/bin/env bash
# Держит Remote Control живым: упал или вышел — поднимаем снова.
cd /opt/server-ops
while true; do
  ~/.local/bin/claude remote-control \
    --name "hostvds" \
    --permission-mode bypassPermissions \
    --spawn same-dir
  echo "remote-control вышел ($?), перезапуск через 20 с"
  sleep 20
done
