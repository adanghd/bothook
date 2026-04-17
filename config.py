import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "ratecard" / "assets"
PROPOSALS_DIR = DATA_DIR / "proposals"

DATA_DIR.mkdir(exist_ok=True)
PROPOSALS_DIR.mkdir(exist_ok=True)


def _load_telegram_token() -> str:
    """Load token from env var or ~/.kalopilot/telegram.json."""
    token = os.getenv("TELEGRAM_TOKEN", "")
    if token:
        return token
    cfg_path = Path.home() / ".kalopilot" / "telegram.json"
    if cfg_path.exists():
        data = json.loads(cfg_path.read_text())
        return data.get("bot_token", "")
    return ""


TELEGRAM_TOKEN = _load_telegram_token()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DB_PATH = DATA_DIR / "ratecard.db"
PLATFORM_DEFAULTS_PATH = ASSETS_DIR / "platform_defaults.json"
RATE_CARD_TEMPLATE_PATH = ASSETS_DIR / "rate_card_template.json"

FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
