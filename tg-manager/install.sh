#!/usr/bin/env bash
# Установка: акк менеджера онлайн 24/7 + ответы через Claude Code.
set -e
D=/opt/tgmanager
RAW=https://raw.githubusercontent.com/BEZzZ22/html/claude/project-thread-895m8n/tg-manager
echo "== 1/5 Пакеты"
apt-get update -qq && apt-get install -y -qq python3-venv curl >/dev/null
mkdir -p $D && cd $D
for f in bot.py login.py CLAUDE.md skip.txt; do [ -f $f ] && [ $f = skip.txt ] || curl -fsSL $RAW/$f -o $f; done
python3 -m venv venv && venv/bin/pip -q install telethon
echo "== 2/5 Claude Code"
command -v ~/.local/bin/claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash
if ! grep -q CLAUDE_TOKEN .env 2>/dev/null; then
  echo "Сейчас откроется вход в Claude. Открой ссылку на телефоне, войди, скопируй код и вставь сюда."
  ~/.local/bin/claude setup-token
  read -rp "Вставь токен, который показался выше (sk-ant-oat...): " TOK
  echo "CLAUDE_TOKEN=$TOK" >> .env
fi
echo "== 3/5 Ключи Телеги"
if ! grep -q API_ID .env 2>/dev/null; then
  echo "Зайди на https://my.telegram.org с номером менеджера → API development tools → создай приложение."
  read -rp "api_id: " AID; read -rp "api_hash: " AH
  printf 'API_ID=%s\nAPI_HASH=%s\n' "$AID" "$AH" >> .env
fi
chmod 600 .env
echo "== 4/5 Вход в акк менеджера"
[ -s session.txt ] || venv/bin/python login.py
echo "== 5/5 Служба"
cat > /etc/systemd/system/tgmanager.service <<UNIT
[Unit]
Description=DotaRazbor manager in Telegram
After=network-online.target
[Service]
WorkingDirectory=$D
Environment=HOME=/root
ExecStart=$D/venv/bin/python $D/bot.py
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now tgmanager
sleep 8; systemctl --no-pager status tgmanager | head -5
echo "✅ Готово. Логи: tail -f $D/log.jsonl   Пауза: touch $D/PAUSE   Снять: rm $D/PAUSE"
