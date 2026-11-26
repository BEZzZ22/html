"""Акк менеджера Dota Razbor онлайн 24/7: входящие в личку отвечает Claude Code."""
import asyncio, json, os, subprocess, time
from pathlib import Path
from telethon import TelegramClient, events
from telethon.sessions import StringSession

BASE = Path(__file__).resolve().parent
ENV = dict(l.split("=", 1) for l in (BASE / ".env").read_text().split("\n") if "=" in l)
API_ID, API_HASH = int(ENV["API_ID"]), ENV["API_HASH"]
SESSION = (BASE / "session.txt").read_text().strip()
SKIP = {u.strip().lower().lstrip("@") for u in (BASE / "skip.txt").read_text().split() if u.strip()} if (BASE / "skip.txt").exists() else set()
WAIT = 25          # ждём, пока человек допишет
LOG = BASE / "log.jsonl"
PAUSE = BASE / "PAUSE"  # создать файл = бот молчит

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, device_model="DotaRazbor manager", system_version="Ubuntu")
pending: dict[int, asyncio.Task] = {}


def log(**kw):
    kw["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def ask_claude(prompt: str) -> str:
    env = dict(os.environ, CLAUDE_CODE_OAUTH_TOKEN=ENV["CLAUDE_TOKEN"])
    r = subprocess.run(
        [str(Path.home() / ".local/bin/claude"), "-p", prompt, "--output-format", "text", "--max-turns", "2",
         "--disallowedTools", "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"],
        cwd=BASE, env=env, capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])
    return r.stdout.strip()


async def answer(chat_id: int, who: str):
    await asyncio.sleep(WAIT)
    msgs = []
    async for m in client.iter_messages(chat_id, limit=30):
        if m.text:
            msgs.append(("МЫ" if m.out else who) + f" [{m.date:%d.%m %H:%M}]: " + m.text)
    history = "\n".join(reversed(msgs))
    prompt = (f"Переписка в Telegram с {who}. Последнее сообщение внизу.\n\n{history}\n\n"
              "Напиши ответ от менеджера по правилам из CLAUDE.md. Выведи только текст ответа, "
              "или SKIP, или строку ESCALATE: <что спросить у Ярика> и с новой строки ответ человеку.")
    try:
        async with client.action(chat_id, "typing"):
            out = await asyncio.to_thread(ask_claude, prompt)
    except Exception as e:
        log(chat=who, error=str(e))
        await client.send_message("me", f"⚠️ Не смог ответить {who}: {e}")
        return
    if out.startswith("ESCALATE:"):
        q, _, out = out.partition("\n")
        await client.send_message("me", f"❓ {who}: {q[9:].strip()}")
    out = out.strip()
    if not out or out == "SKIP":
        log(chat=who, skip=True)
        return
    await client.send_message(chat_id, out)
    log(chat=who, reply=out)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def on_msg(event):
    if PAUSE.exists():
        return
    s = await event.get_sender()
    if s is None or getattr(s, "bot", False) or getattr(s, "is_self", False) or s.id == 777000:
        return
    uname = (s.username or "").lower()
    if uname in SKIP or str(s.id) in SKIP:
        return
    who = f"@{s.username}" if s.username else (s.first_name or str(s.id))
    log(chat=who, incoming=event.raw_text)
    await event.mark_read()
    t = pending.pop(event.chat_id, None)
    if t:
        t.cancel()
    pending[event.chat_id] = asyncio.create_task(answer(event.chat_id, who))


async def main():
    await client.start()
    me = await client.get_me()
    log(started=f"{me.first_name} @{me.username}")
    print("Онлайн как", me.first_name, flush=True)
    await client.run_until_disconnected()

asyncio.run(main())
