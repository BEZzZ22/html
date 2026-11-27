"""Разовый вход в акк менеджера. Код придёт в Телегу на айфоне."""
import asyncio, sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

BASE = Path(__file__).resolve().parent
NAME = sys.argv[1] if len(sys.argv) > 1 else "manager"
ACC = BASE / "accounts" / NAME
ACC.mkdir(parents=True, exist_ok=True)
ENV = dict(l.split("=", 1) for l in (BASE / ".env").read_text().split("\n") if "=" in l)

async def main():
    c = TelegramClient(StringSession(), int(ENV["API_ID"]), ENV["API_HASH"], device_model="DotaRazbor " + NAME, system_version="Ubuntu")
    await c.start(phone=lambda: input(f"Номер акка {NAME} (+...): "),
                  code_callback=lambda: input("Код из Телеги: "),
                  password=lambda: input("Облачный пароль (если есть, иначе Enter): "))
    (ACC / "session.txt").write_text(c.session.save())
    (ACC / "session.txt").chmod(0o600)
    me = await c.get_me()
    print("✅ Вошли как", me.first_name, me.username)
    await c.disconnect()

asyncio.run(main())
