"""Акк менеджера Dota Razbor онлайн 24/7: входящие в личку отвечает Claude Code."""
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
from telethon import TelegramClient, events, functions, utils
from telethon.sessions import StringSession

BASE = Path(__file__).resolve().parent
NAME = sys.argv[1] if len(sys.argv) > 1 else "manager"
ACC = BASE / "accounts" / NAME
ENV = dict(l.split("=", 1) for l in (BASE / ".env").read_text().split("\n") if "=" in l)
API_ID, API_HASH = int(ENV["API_ID"]), ENV["API_HASH"]
SESSION = (ACC / "session.txt").read_text().strip()
CFG = json.loads((ACC / "config.json").read_text())   # {"role": "...", "folder": "Админы Дота" | null}
SKIP = {u.strip().lower().lstrip("@") for u in (BASE / "skip.txt").read_text().split() if u.strip()} if (BASE / "skip.txt").exists() else set()
WAIT = 10          # ждём, пока человек допишет
LOG = ACC / "log.jsonl"
PAUSE = BASE / "PAUSE"  # создать файл = все акки молчат
folder_ids: set[int] = set()
folder_at = 0.0


def save_cfg():
    (ACC / "config.json").write_text(json.dumps(CFG, ensure_ascii=False, indent=1))


async def in_folder(chat_id: int, uname: str) -> bool:
    """Кому отвечаем: всем (all), или папка + ручной список allow. Управление — командами в Избранном."""
    global folder_ids, folder_at
    if CFG.get("all") or not CFG.get("folder"):
        return True
    if uname in CFG.get("allow", []) or str(chat_id) in CFG.get("allow", []):
        return True
    if time.time() - folder_at > 600:
        res = await client(functions.messages.GetDialogFiltersRequest())
        filters = getattr(res, "filters", res)
        ids = set()
        for f in filters:
            title = getattr(f, "title", "")
            title = getattr(title, "text", title)
            if title == CFG["folder"]:
                for p in list(getattr(f, "include_peers", [])) + list(getattr(f, "pinned_peers", [])):
                    ids.add(utils.get_peer_id(p))
        folder_ids, folder_at = ids, time.time()
    return chat_id in folder_ids

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, device_model="DotaRazbor " + NAME, system_version="Ubuntu")
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


async def answer(chat_id: int, who: str, uname: str = ""):
    await asyncio.sleep(WAIT)
    msgs = []
    async for m in client.iter_messages(chat_id, limit=30):
        if m.text:
            msgs.append(("МЫ" if m.out else who) + f" [{m.date:%d.%m %H:%M}]: " + m.text)
    history = "\n".join(reversed(msgs))
    personal = ""
    if CFG.get("folder") and (CFG.get("all") or uname in CFG.get("allow", []) or str(chat_id) in CFG.get("allow", [])):
        personal = ("ВАЖНО: Ярик сам разрешил отвечать в этом чате, это может быть личная переписка (друзья, близкие). "
                    "Отвечай как сам Ярик, живо и по-человечески, в его манере: коротко, просто, можно по-братски, "
                    "строчными буквами, без официоза и без рекламы бота. Не игнорь. SKIP только если реально нечего ответить.\n\n")
    prompt = (f"Ты пишешь с аккаунта: {CFG['role']}\n\n{personal}Переписка в Telegram с {who}. Последнее сообщение внизу.\n\n{history}\n\n"
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
    if personal and not CFG.get("auto_personal", True):
        # личные чаты: не шлём сами, кладём черновик Ярику в Избранное
        await client.send_message("me", f"✍️ Черновик для {who} (сам не отправил):\n\n{out}")
        log(chat=who, draft=out)
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
    if not await in_folder(event.chat_id, uname):
        return
    who = f"@{s.username}" if s.username else (s.first_name or str(s.id))
    log(chat=who, incoming=event.raw_text)
    await event.mark_read()
    t = pending.pop(event.chat_id, None)
    if t:
        t.cancel()
    pending[event.chat_id] = asyncio.create_task(answer(event.chat_id, who, uname))


HELP = ("Команды (пиши в Избранное этого акка):\n"
        "/allow @ник — отвечать ему тоже\n/deny @ник — не отвечать\n"
        "/all on — отвечать всем в личке, /all off — только папка и список\n"
        "/pause, /resume — выключить/включить ответы\n/status")


@client.on(events.NewMessage(outgoing=True, chats="me", pattern=r"^/(allow|deny|all|pause|resume|status|help)"))
async def on_cmd(event):
    cmd, *args = event.raw_text.split()
    arg = args[0].lower().lstrip("@") if args else ""
    cmd = cmd[1:]
    if cmd == "allow" and arg:
        CFG.setdefault("allow", []); arg in CFG["allow"] or CFG["allow"].append(arg); SKIP.discard(arg)
    elif cmd == "deny" and arg:
        CFG["allow"] = [a for a in CFG.get("allow", []) if a != arg]; SKIP.add(arg)
        (BASE / "skip.txt").write_text("\n".join(sorted(SKIP)) + "\n")
    elif cmd == "all":
        CFG["all"] = arg != "off"
    elif cmd == "pause":
        PAUSE.touch()
    elif cmd == "resume":
        PAUSE.unlink(missing_ok=True)
    elif cmd == "help":
        return await event.reply(HELP)
    save_cfg()
    await event.reply(f"✅ {NAME}: всем={'да' if CFG.get('all') or not CFG.get('folder') else 'нет'}, "
                      f"папка={CFG.get('folder') or '-'}, список={', '.join(CFG.get('allow', [])) or '-'}, "
                      f"пауза={'да' if PAUSE.exists() else 'нет'}")


async def main():
    await client.start()
    me = await client.get_me()
    log(started=f"{NAME}: {me.first_name} @{me.username}")
    print("Онлайн как", me.first_name, flush=True)
    await client.run_until_disconnected()

asyncio.run(main())
