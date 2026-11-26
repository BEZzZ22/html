"""Разовый вход в акк менеджера. Код придёт в Телегу на айфоне."""
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

BASE = Path(__file__).resolve().parent
ENV = dict(l.split("=", 1) for l in (BASE / ".env").read_text().split("\n") if "=" in l)

async def main():
    c = TelegramClient(StringSession(), int(ENV["API_ID"]), ENV["API_HASH"], device_model="DotaRazbor manager", system_version="Ubuntu")
    await c.start(phone=lambda: input("Номер акка менеджера (+1...): "),
                  code_callback=lambda: input("Код из Телеги: "),
                  password=lambda: input("Облачный пароль (если есть, иначе Enter): "))
    (BASE / "session.txt").write_text(c.session.save())
    (BASE / "session.txt").chmod(0o600)
    me = await c.get_me()
    print("✅ Вошли как", me.first_name, me.username)
    await c.disconnect()

asyncio.run(main())
