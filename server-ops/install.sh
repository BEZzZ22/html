#!/usr/bin/env bash
# Claude сам обслуживает сервер: Claude Code в режиме Remote Control работает
# тут 24/7 и принимает задачи из проекта на claude.ai. Наружу ничего не
# открывается: только исходящее соединение к Anthropic, SSH и пароли не трогаем.
# Повторный запуск безопасен.
set -e
[ "$(id -u)" = 0 ] || { echo "Запусти от root"; exit 1; }
U=claudeops
D=/opt/server-ops
RAW=https://raw.githubusercontent.com/BEZzZ22/html/claude/project-thread-yh9ooj/server-ops

echo "== 1/5 Пакеты"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tmux git curl python3 unattended-upgrades >/dev/null
# Автоматические обновления безопасности (без перезагрузок)
echo 'APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";' > /etc/apt/apt.conf.d/20auto-upgrades

echo "== 2/5 Пользователь $U"
id $U >/dev/null 2>&1 || useradd -m -s /bin/bash $U
passwd -l $U >/dev/null            # без пароля: войти по паролю нельзя
echo "$U ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$U
chmod 440 /etc/sudoers.d/$U
mkdir -p $D
curl -fsSL $RAW/CLAUDE.md -o $D/CLAUDE.md
curl -fsSL $RAW/run.sh -o $D/run.sh
chmod 755 $D/run.sh
chown -R $U:$U $D
chmod 700 $D

echo "== 3/5 Claude Code"
H=$(getent passwd $U | cut -d: -f6)
[ -x $H/.local/bin/claude ] || sudo -u $U -H bash -c 'curl -fsSL https://claude.ai/install.sh | bash' >/dev/null
if ! sudo -u $U -H $H/.local/bin/claude auth status 2>/dev/null | grep -qi '"loggedIn": *true'; then
  echo "Сейчас вход в Claude: открой ссылку на телефоне, войди тем же аккаунтом, скопируй код и вставь сюда."
  sudo -u $U -H $H/.local/bin/claude auth login --claudeai </dev/tty
fi
# Папка доверенная, онбординг пройден: без вопросов в терминале
sudo -u $U -H python3 - "$D" <<'PY'
import json, os, sys
p = os.path.expanduser("~/.claude.json")
c = json.load(open(p)) if os.path.exists(p) else {}
c["hasCompletedOnboarding"] = True
c["remoteDialogSeen"] = True
c.setdefault("projects", {}).setdefault(sys.argv[1], {})["hasTrustDialogAccepted"] = True
json.dump(c, open(p, "w"), indent=2)
PY

echo "== 4/5 Служба"
cat > /etc/systemd/system/claude-rc.service <<UNIT
[Unit]
Description=Claude Remote Control (server-ops)
After=network-online.target
Wants=network-online.target
[Service]
Type=forking
User=$U
WorkingDirectory=$D
Environment=HOME=$H
ExecStart=/usr/bin/tmux new-session -d -s rc $D/run.sh
ExecStop=/usr/bin/tmux kill-session -t rc
Restart=on-failure
RestartSec=30
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable -q claude-rc
systemctl restart claude-rc

echo "== 5/5 Проверка"
sleep 15
echo "claude-rc: $(systemctl is-active claude-rc)"
sudo -u $U tmux capture-pane -pt rc 2>/dev/null | tail -15 || true
echo "✅ Готово. Напиши Клодику «сервер готов». Посмотреть вживую: sudo -u $U tmux attach -t rc (выйти: Ctrl+B, потом D)"
