import html


def esc(x, default="—"):
    return html.escape(str(x)) if x not in (None, "") else default


def extract_video(msg):
    """Xabardan video yoki video-hujjat file_id va turini qaytaradi."""
    if msg.video:
        return msg.video.file_id, "video"
    if msg.document and (msg.document.mime_type or "").startswith("video"):
        return msg.document.file_id, "document"
    return None, None


async def resolve_chat(bot, msg):
    """Forward qilingan kanal xabari, @username, t.me/link yoki -100... ID dan chat obyektini topadi."""
    fo = getattr(msg, "forward_origin", None)
    if fo is not None and getattr(fo, "chat", None):
        return await bot.get_chat(fo.chat.id)
    if msg.text:
        t = msg.text.strip()
        if t.lstrip("-").isdigit():
            t = int(t)
        else:
            t = "@" + t.split("/")[-1].lstrip("@")
        return await bot.get_chat(t)
    return None


async def chat_link(bot, chat):
    if chat.username:
        return f"https://t.me/{chat.username}"
    try:
        return (await bot.create_chat_invite_link(chat.id)).invite_link
    except Exception:
        return ""
