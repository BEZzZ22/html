"""Разовый вход в акк. По умолчанию — QR (сканируешь с телефона), либо по номеру и коду."""
import asyncio, sys
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

BASE = Path(__file__).resolve().parent


def ask(prompt: str) -> str:
    """input(), который не падает на русских буквах при кривой локали сервера."""
    raw = input(prompt)
    try:
        return raw.encode("utf-8", "surrogateescape").decode("utf-8").strip()
    except UnicodeError:
        return raw.encode("latin-1", "surrogateescape").decode("utf-8", "replace").strip()

NAME = sys.argv[1] if len(sys.argv) > 1 else "manager"
ACC = BASE / "accounts" / NAME
ACC.mkdir(parents=True, exist_ok=True)
ENV = dict(l.split("=", 1) for l in (BASE / ".env").read_text().split("\n") if "=" in l)


async def qr_login(c):
    import qrcode
    while True:
        qr = await c.qr_login()
        q = qrcode.QRCode(border=2)
        q.add_data(qr.url)
        q.print_ascii(invert=True)
        print("\n📱 Телега на телефоне → Настройки → Устройства → Подключить устройство → наведи на QR выше.")
        try:
            await qr.wait(timeout=60)
            return
        except asyncio.TimeoutError:
            print("QR устарел, показываю новый...\n")
        except SessionPasswordNeededError:
            await c.sign_in(password=ask("Облачный пароль (2FA): "))
            return


async def main():
    c = TelegramClient(StringSession(), int(ENV["API_ID"]), ENV["API_HASH"], device_model="DotaRazbor " + NAME, system_version="Ubuntu")
    await c.connect()
    phone = ask(f"Акк {NAME}: просто Enter = вход по QR, или введи номер (+...): ").strip()
    if not phone:
        await qr_login(c)
    else:
        await c.send_code_request(phone)
        try:
            await c.sign_in(phone, ask("Код из Телеги: ").strip())
        except SessionPasswordNeededError:
            await c.sign_in(password=ask("Облачный пароль (2FA): "))
    (ACC / "session.txt").write_text(c.session.save())
    (ACC / "session.txt").chmod(0o600)
    me = await c.get_me()
    print("✅ Вошли как", me.first_name, me.username)
    await c.disconnect()

asyncio.run(main())
