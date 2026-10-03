# 🎬 Kino Bot (aiogram 3.x + aiosqlite, multibot)

## Ishga tushirish
```bash
sudo apt install ffmpeg          # teaser uchun (ffmpeg + ffprobe)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # BOT_TOKEN va ADMIN_IDS ni to'ldiring
python main.py
```

## Arxitektura
```
main.py                 – start: DB, Dispatcher, middleware, routerlar, BotManager
config.py               – .env sozlamalari, default /rooter va PIN 9767
database/db.py          – aiosqlite ulanish + sxema
database/queries.py     – barcha SQL funksiyalar (har jadvalda bot_id!)
middlewares/context.py  – bot_id, is_parent (Parent/Child roli), is_admin, user ro'yxati
middlewares/forcesub.py – majburiy obuna
handlers/common.py      – /cancel
handlers/rooter.py      – yashirin /rooter -> PIN -> token -> sub-bot (faqat Parent)
handlers/admin_*.py     – kino, serial, avto-post, obuna, rassilka, statistika, sozlamalar
handlers/user.py        – qidiruv, kartochka, yuklash, saqlanganlar, baholash
keyboards/              – reply va inline tugmalar
states/states.py        – FSM holatlari
utils/ffmpeg_utils.py   – 30 soniyalik teaser qirqish
utils/autopost.py       – kanalga avto-post
utils/multibot.py       – Multibot menejeri
```

## Multibot / Parent–Child
* Bitta Dispatcher + har bir bot uchun alohida polling vazifasi (`utils/multibot.py`).
  Update `dp.feed_update(bot, update)` orqali umumiy handlerlarga beriladi.
* `bots` jadvalida `is_parent` (1 = asosiy, 0 = sub-bot). Barcha jadvallarda `bot_id` bor,
  shuning uchun har bir sub-botning kinolari, foydalanuvchilari, kanallari, sozlamalari alohida.
* `/rooter` va sozlamalardagi "yashirin buyruq/PIN" bo'limi `IsParent` filtri bilan himoyalangan:
  sub-botda bu handlerlar umuman mos kelmaydi.
* Sub-bot egasi = tokenni kiritgan foydalanuvchi; u sub-botda to'liq admin panelga ega.
  `ADMIN_IDS` dagi super-adminlar barcha botlarda admin.
* Bot qayta ishga tushganda barcha faol sub-botlar bazadan avtomatik yuklanadi.

## /rooter
`/rooter` -> PIN (default 9767; 3 marta xato = 10 daqiqa blok) -> token -> sub-bot ishga tushadi.
Buyruq nomi va PIN: Admin panel -> ⚙️ Sozlamalar (faqat Parent botda).
PIN va token xabarlari chatdan o'chiriladi.

## Teaser (ffmpeg) qanday ishlaydi
1. Video bot orqali yuklab olinadi (Telegram cloud API cheklovi: **20 MB**; kattaroq fayllar uchun
   lokal Bot API server o'rnatib `.env` da `LOCAL_API_URL` ni bering).
2. `ffprobe` bilan davomiylik olinadi.
3. 5 ta nomzod oyna (20/35/50/65/80%) olinadi; har birining o'rtacha ovozi `volumedetect` bilan
   o'lchanadi. Eng baland ovozli oyna ("eng qiziq joy") tanlanadi. Audio bo'lmasa 35% olinadi.
4. 30 soniya qirqiladi, 720p gacha kichraytiriladi (H.264 + AAC, faststart).
5. Kanalga: teaser + nom + kod + "▶️ Kinoni ko'rish" tugmasi (`t.me/bot?start=KOD` — bosilsa kino ochiladi).
6. ffmpeg yo'q / fayl katta bo'lsa — poster bilan post qilinadi (bot to'xtamaydi).

## Eslatmalar
* Majburiy obuna va avto-post uchun bot kanalda ADMIN bo'lishi shart.
* FSM `MemoryStorage` — qayta ishga tushganda yarim qolgan dialoglar tozalanadi.
  Kerak bo'lsa Redis storage'ga almashtiring.
* Kino/serial kodi bitta bot ichida noyob.
