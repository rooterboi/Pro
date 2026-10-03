import aiosqlite
from config import DB_PATH

_conn: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS bots(
    bot_id INTEGER PRIMARY KEY, token TEXT NOT NULL, username TEXT,
    owner_id INTEGER DEFAULT 0, is_parent INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1, created_at INTEGER);
CREATE TABLE IF NOT EXISTS users(
    bot_id INTEGER, user_id INTEGER, full_name TEXT, username TEXT,
    joined_at INTEGER, blocked INTEGER DEFAULT 0, PRIMARY KEY(bot_id, user_id));
CREATE TABLE IF NOT EXISTS settings(
    bot_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(bot_id, key));
CREATE TABLE IF NOT EXISTS channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, chat_id INTEGER,
    title TEXT, link TEXT);
CREATE TABLE IF NOT EXISTS series(
    id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, code TEXT, title TEXT,
    genre TEXT, year TEXT, description TEXT, poster_file_id TEXT, created_at INTEGER);
CREATE TABLE IF NOT EXISTS movies(
    id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, code TEXT, title TEXT,
    genre TEXT, language TEXT, quality TEXT, year TEXT, description TEXT,
    poster_file_id TEXT, video_file_id TEXT, video_kind TEXT DEFAULT 'video',
    series_id INTEGER, season INTEGER, episode INTEGER,
    views INTEGER DEFAULT 0, created_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_movies_code ON movies(bot_id, code);
CREATE INDEX IF NOT EXISTS ix_movies_series ON movies(series_id);
CREATE TABLE IF NOT EXISTS favorites(
    bot_id INTEGER, user_id INTEGER, movie_id INTEGER,
    PRIMARY KEY(bot_id, user_id, movie_id));
CREATE TABLE IF NOT EXISTS ratings(
    bot_id INTEGER, user_id INTEGER, movie_id INTEGER, score INTEGER,
    PRIMARY KEY(bot_id, user_id, movie_id));
"""


async def init():
    global _conn
    _conn = await aiosqlite.connect(DB_PATH)
    _conn.row_factory = aiosqlite.Row
    await _conn.execute("PRAGMA journal_mode=WAL")
    # Unicode (kirill/lotin) uchun katta-kichik harfga befarq qidiruv
    await _conn.create_function("pylower", 1, lambda s: s.lower() if isinstance(s, str) else s)
    await _conn.executescript(SCHEMA)
    await _conn.commit()


async def close():
    if _conn:
        await _conn.close()


async def fetchone(q, args=()):
    async with _conn.execute(q, args) as cur:
        return await cur.fetchone()


async def fetchall(q, args=()):
    async with _conn.execute(q, args) as cur:
        return await cur.fetchall()


async def execute(q, args=()):
    cur = await _conn.execute(q, args)
    await _conn.commit()
    return cur.lastrowid
