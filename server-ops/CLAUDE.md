# Сервер HostVDS (обслуживает Claude)

Ты на сервере Ярика, пользователь `claudeops`, есть `sudo` без пароля. Задачи приходят из проекта «Дота разбор бот» на claude.ai.

## Что тут крутится

- `tgmanager@main` и `tgmanager@manager` (systemd): акки Телеги, код в `/opt/tgmanager`.
  Обновить: скачать файлы из `https://raw.githubusercontent.com/BEZzZ22/html/<ветка>/tg-manager/`, затем `sudo systemctl restart tgmanager@main tgmanager@manager`.
  Логи: `sudo journalctl -u tgmanager@main -n 100`, `sudo tail /opt/tgmanager/accounts/*/log.jsonl`.
  Пауза всем: `sudo touch /opt/tgmanager/PAUSE`, снять: `sudo rm /opt/tgmanager/PAUSE`.
- `claude-rc` (systemd + tmux `rc`): этот самый Remote Control. Не останавливать, иначе связь пропадёт.
- Рендер видеоразбора (по очереди, по одному ролику), если уже установлен.

Железо слабое: 1 vCPU, 2 ГБ RAM, 20 ГБ диск. Тяжёлое запускать по одному, следить за `free -h` и `df -h`.

## Правила

- Секреты не выводить и не копировать никуда: `/opt/tgmanager/.env`, `accounts/*/session.txt`, токены, ключи. Проверять их наличие можно (`test -s`), печатать содержимое нельзя.
- Не трогать без прямого «да» Ярика: вход в Телегу и сессии акков, удаление файлов роликов, настройки SSH, firewall, пароли, перезагрузку всего сервера.
- Наружу ничего не открывать (порты, root по паролю, туннели).
- Перед правкой системного файла сделать копию `*.bak`.
- После обновления проверить: `systemctl is-active` и последние строки лога.
