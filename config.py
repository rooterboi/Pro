import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
DB_PATH = os.getenv("DB_PATH", "kino.db")
LOCAL_API_URL = os.getenv("LOCAL_API_URL", "").strip()

DEFAULT_ROOTER_CMD = "rooter"
DEFAULT_ROOTER_PIN = "9767"

TEASER_SECONDS = 30
TMP_DIR = "tmp"
