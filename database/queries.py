import time
from . import db

MOVIE_FIELDS = {"code", "title", "genre", "language", "quality", "year", "description",
                "poster_file_id", "video_file_id", "video_kind", "series_id", "season", "episode"}


def now():
    return int(time.time())


# ---------- bots ----------
async def add_bot(bot_id, token, username, owner_id=0, is_parent=0):
    await db.execute(
        "INSERT OR REPLACE INTO bots(bot_id,token,username,owner_id,is_parent,active,created_at) "
        "VALUES(?,?,?,?,?,1,?)", (bot_id, token, username, owner_id, is_parent, now()))


async def get_bot(bot_id):
    return await db.fetchone("SELECT * FROM bots WHERE bot_id=?", (bot_id,))


async def get_bots(active_only=False, children_only=False):
    q = "SELECT * FROM bots WHERE 1=1"
    if active_only:
        q += " AND active=1"
    if children_only:
        q += " AND is_parent=0"
    return await db.fetchall(q + " ORDER BY created_at")


async def set_bot_active(bot_id, active):
    await db.execute("UPDATE bots SET active=? WHERE bot_id=?", (int(active), bot_id))


async def purge_bot(bot_id):
    for t in ("bots", "users", "settings", "channels", "series", "movies", "favorites", "ratings"):
        await db.execute(f"DELETE FROM {t} WHERE bot_id=?", (bot_id,))


# ---------- users ----------
async def add_user(bot_id, user):
    await db.execute("INSERT OR IGNORE INTO users(bot_id,user_id,full_name,username,joined_at) VALUES(?,?,?,?,?)",
                     (bot_id, user.id, user.full_name, user.username, now()))
    await db.execute("UPDATE users SET blocked=0 WHERE bot_id=? AND user_id=?", (bot_id, user.id))


async def user_ids(bot_id):
    rows = await db.fetchall("SELECT user_id FROM users WHERE bot_id=? AND blocked=0", (bot_id,))
    return [r["user_id"] for r in rows]


async def mark_blocked(bot_id, user_id):
    await db.execute("UPDATE users SET blocked=1 WHERE bot_id=? AND user_id=?", (bot_id, user_id))


# ---------- settings ----------
async def get_setting(bot_id, key, default=""):
    r = await db.fetchone("SELECT value FROM settings WHERE bot_id=? AND key=?", (bot_id, key))
    return r["value"] if r else default


async def set_setting(bot_id, key, value):
    await db.execute("INSERT OR REPLACE INTO settings(bot_id,key,value) VALUES(?,?,?)", (bot_id, key, str(value)))


# ---------- force-sub channels ----------
async def add_channel(bot_id, chat_id, title, link):
    await db.execute("DELETE FROM channels WHERE bot_id=? AND chat_id=?", (bot_id, chat_id))
    await db.execute("INSERT INTO channels(bot_id,chat_id,title,link) VALUES(?,?,?,?)", (bot_id, chat_id, title, link))


async def get_channels(bot_id):
    return await db.fetchall("SELECT * FROM channels WHERE bot_id=?", (bot_id,))


async def del_channel(bot_id, cid):
    await db.execute("DELETE FROM channels WHERE bot_id=? AND id=?", (bot_id, cid))


# ---------- movies ----------
async def code_exists(bot_id, code):
    a = await db.fetchone("SELECT 1 FROM movies WHERE bot_id=? AND code=?", (bot_id, code))
    b = await db.fetchone("SELECT 1 FROM series WHERE bot_id=? AND code=?", (bot_id, code))
    return bool(a or b)


async def add_movie(bot_id, **f):
    f = {k: v for k, v in f.items() if k in MOVIE_FIELDS}
    cols = ",".join(["bot_id", "created_at", *f])
    ph = ",".join("?" * (len(f) + 2))
    return await db.execute(f"INSERT INTO movies({cols}) VALUES({ph})", (bot_id, now(), *f.values()))


async def update_movie(mid, **f):
    f = {k: v for k, v in f.items() if k in MOVIE_FIELDS}
    if not f:
        return
    sets = ",".join(f"{k}=?" for k in f)
    await db.execute(f"UPDATE movies SET {sets} WHERE id=?", (*f.values(), mid))


async def get_movie(mid):
    return await db.fetchone("SELECT * FROM movies WHERE id=?", (mid,))


async def get_movie_by_code(bot_id, code):
    return await db.fetchone("SELECT * FROM movies WHERE bot_id=? AND code=?", (bot_id, code))


async def delete_movie(mid):
    await db.execute("DELETE FROM movies WHERE id=?", (mid,))
    await db.execute("DELETE FROM favorites WHERE movie_id=?", (mid,))
    await db.execute("DELETE FROM ratings WHERE movie_id=?", (mid,))


async def inc_views(mid):
    await db.execute("UPDATE movies SET views=views+1 WHERE id=?", (mid,))


async def search(bot_id, text, limit=20):
    like = f"%{text.lower()}%"
    movies = await db.fetchall(
        "SELECT * FROM movies WHERE bot_id=? AND series_id IS NULL AND "
        "(pylower(title) LIKE ? OR pylower(genre) LIKE ? OR year LIKE ?) ORDER BY views DESC LIMIT ?",
        (bot_id, like, like, like, limit))
    series = await db.fetchall(
        "SELECT * FROM series WHERE bot_id=? AND "
        "(pylower(title) LIKE ? OR pylower(genre) LIKE ? OR year LIKE ?) LIMIT ?",
        (bot_id, like, like, like, limit))
    return movies, series


async def by_year(bot_id, year):
    movies = await db.fetchall("SELECT * FROM movies WHERE bot_id=? AND series_id IS NULL AND year=? LIMIT 30", (bot_id, year))
    series = await db.fetchall("SELECT * FROM series WHERE bot_id=? AND year=? LIMIT 30", (bot_id, year))
    return movies, series


async def genres(bot_id):
    rows = await db.fetchall(
        "SELECT genre FROM movies WHERE bot_id=? AND genre IS NOT NULL AND series_id IS NULL UNION "
        "SELECT genre FROM series WHERE bot_id=? AND genre IS NOT NULL", (bot_id, bot_id))
    out = set()
    for r in rows:
        for g in r["genre"].split(","):
            if g.strip():
                out.add(g.strip().capitalize())
    return sorted(out)


async def years(bot_id):
    rows = await db.fetchall(
        "SELECT year FROM movies WHERE bot_id=? AND year IS NOT NULL AND series_id IS NULL UNION "
        "SELECT year FROM series WHERE bot_id=? AND year IS NOT NULL", (bot_id, bot_id))
    return sorted({r["year"] for r in rows}, reverse=True)


async def top_movies(bot_id, limit=15):
    return await db.fetchall("SELECT * FROM movies WHERE bot_id=? AND series_id IS NULL ORDER BY views DESC LIMIT ?", (bot_id, limit))


async def new_movies(bot_id, limit=15):
    return await db.fetchall("SELECT * FROM movies WHERE bot_id=? AND series_id IS NULL ORDER BY id DESC LIMIT ?", (bot_id, limit))


async def new_series(bot_id, limit=10):
    return await db.fetchall("SELECT * FROM series WHERE bot_id=? ORDER BY id DESC LIMIT ?", (bot_id, limit))


# ---------- series ----------
async def add_series(bot_id, code, title, genre, year, description, poster):
    return await db.execute(
        "INSERT INTO series(bot_id,code,title,genre,year,description,poster_file_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (bot_id, code, title, genre, year, description, poster, now()))


async def get_series(sid):
    return await db.fetchone("SELECT * FROM series WHERE id=?", (sid,))


async def get_series_by_code(bot_id, code):
    return await db.fetchone("SELECT * FROM series WHERE bot_id=? AND code=?", (bot_id, code))


async def list_series(bot_id):
    return await db.fetchall("SELECT * FROM series WHERE bot_id=? ORDER BY id DESC", (bot_id,))


async def delete_series(sid):
    await db.execute("DELETE FROM movies WHERE series_id=?", (sid,))
    await db.execute("DELETE FROM series WHERE id=?", (sid,))


async def seasons(sid):
    return await db.fetchall("SELECT season, COUNT(*) c FROM movies WHERE series_id=? GROUP BY season ORDER BY season", (sid,))


async def episodes(sid, season):
    return await db.fetchall("SELECT * FROM movies WHERE series_id=? AND season=? ORDER BY episode", (sid, season))


async def next_episode(sid, season):
    r = await db.fetchone("SELECT MAX(episode) m FROM movies WHERE series_id=? AND season=?", (sid, season))
    return (r["m"] or 0) + 1


# ---------- favorites / ratings ----------
async def toggle_fav(bot_id, uid, mid):
    if await is_fav(bot_id, uid, mid):
        await db.execute("DELETE FROM favorites WHERE bot_id=? AND user_id=? AND movie_id=?", (bot_id, uid, mid))
        return False
    await db.execute("INSERT OR IGNORE INTO favorites VALUES(?,?,?)", (bot_id, uid, mid))
    return True


async def is_fav(bot_id, uid, mid):
    return bool(await db.fetchone("SELECT 1 FROM favorites WHERE bot_id=? AND user_id=? AND movie_id=?", (bot_id, uid, mid)))


async def list_favs(bot_id, uid):
    return await db.fetchall(
        "SELECT m.* FROM movies m JOIN favorites f ON f.movie_id=m.id WHERE f.bot_id=? AND f.user_id=? ORDER BY m.id DESC",
        (bot_id, uid))


async def set_rating(bot_id, uid, mid, score):
    await db.execute("INSERT OR REPLACE INTO ratings VALUES(?,?,?,?)", (bot_id, uid, mid, score))


async def get_rating(mid):
    r = await db.fetchone("SELECT AVG(score) a, COUNT(*) c FROM ratings WHERE movie_id=?", (mid,))
    return (r["a"] or 0.0), r["c"]


# ---------- stats ----------
async def stats(bot_id):
    one = lambda r: r[0]
    users = one(await db.fetchone("SELECT COUNT(*) FROM users WHERE bot_id=?", (bot_id,)))
    blocked = one(await db.fetchone("SELECT COUNT(*) FROM users WHERE bot_id=? AND blocked=1", (bot_id,)))
    today = one(await db.fetchone("SELECT COUNT(*) FROM users WHERE bot_id=? AND joined_at>=?", (bot_id, now() - 86400)))
    movies = one(await db.fetchone("SELECT COUNT(*) FROM movies WHERE bot_id=? AND series_id IS NULL", (bot_id,)))
    eps = one(await db.fetchone("SELECT COUNT(*) FROM movies WHERE bot_id=? AND series_id IS NOT NULL", (bot_id,)))
    series = one(await db.fetchone("SELECT COUNT(*) FROM series WHERE bot_id=?", (bot_id,)))
    views = one(await db.fetchone("SELECT COALESCE(SUM(views),0) FROM movies WHERE bot_id=?", (bot_id,)))
    return dict(users=users, blocked=blocked, today=today, movies=movies, eps=eps, series=series, views=views)
