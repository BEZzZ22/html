#!/usr/bin/env bash
# Установка: акки Telegram онлайн 24/7 + ответы через Claude Code.
# Повторный запуск безопасен: уже сделанные шаги пропускаются.
set -e
D=/opt/tgmanager
RAW=https://raw.githubusercontent.com/BEZzZ22/html/claude/project-thread-895m8n/tg-manager
echo "== 1/5 Пакеты"
apt-get update -qq && apt-get install -y -qq python3-venv curl >/dev/null
mkdir -p $D/accounts && cd $D
for f in bot.py login.py CLAUDE.md; do curl -fsSL $RAW/$f -o $f; done
[ -f skip.txt ] || curl -fsSL $RAW/skip.txt -o skip.txt
[ -d venv ] || python3 -m venv venv
venv/bin/pip -q install -U telethon qrcode
echo "== 2/5 Claude Code"
[ -x ~/.local/bin/claude ] || curl -fsSL https://claude.ai/install.sh | bash
if ! grep -q CLAUDE_TOKEN .env 2>/dev/null; then
  echo "Сейчас будет вход в Claude. Открой ссылку, войди, скопируй код и вставь сюда."
  ~/.local/bin/claude setup-token </dev/tty
  read -rp "Вставь токен, который показался выше (sk-ant-oat...): " TOK </dev/tty
  echo "CLAUDE_TOKEN=$TOK" >> .env
fi
echo "== 3/5 Ключи Телеги"
if ! grep -q API_ID .env 2>/dev/null; then
  echo "Зайди на https://my.telegram.org → API development tools → создай приложение (любое название)."
  read -rp "api_id: " AID </dev/tty; read -rp "api_hash: " AH </dev/tty
  printf 'API_ID=%s\nAPI_HASH=%s\n' "$AID" "$AH" >> .env
fi
chmod 600 .env
echo "== 4/5 Вход в акки"
mkdir -p accounts/manager accounts/main
[ -f accounts/manager/config.json ] || echo '{"role": "менеджер проекта Dota Razbor (отвечай от лица менеджера)", "folder": null}' > accounts/manager/config.json
[ -f accounts/main/config.json ] || echo '{"role": "Ярослав, основатель Dota Razbor (отвечай от первого лица, как Ярослав)", "folder": "Админы Дота"}' > accounts/main/config.json
for A in manager main; do
  if [ ! -s accounts/$A/session.txt ]; then
    echo "--- Акк: $A ($( [ $A = main ] && echo 'твой основной' || echo 'менеджер +1 906...' ))"
    PYTHONIOENCODING=utf-8:surrogateescape venv/bin/python -X utf8 login.py $A </dev/tty
  fi
done
chmod -R go-rwx $D
echo "== 5/5 Службы"
cat > /etc/systemd/system/tgmanager@.service <<UNIT
[Unit]
Description=Telegram %i (Dota Razbor)
After=network-online.target
[Service]
WorkingDirectory=$D
Environment=HOME=/root
ExecStart=$D/venv/bin/python $D/bot.py %i
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
for A in manager main; do systemctl enable -q tgmanager@$A; systemctl restart tgmanager@$A; done
sleep 10
for A in manager main; do echo "$A: $(systemctl is-active tgmanager@$A)"; done
echo "✅ Готово. Логи: tail $D/accounts/*/log.jsonl   Пауза всем: touch $D/PAUSE   Снять: rm $D/PAUSE"
