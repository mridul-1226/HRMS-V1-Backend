from pathlib import Path

from decouple import config
from firebase_admin import credentials
import firebase_admin

BASE_DIR = Path(__file__).resolve().parent.parent
credentials_path = Path(
    config('FIREBASE_CREDENTIALS', default=str(BASE_DIR / 'firebase-service-account.json'))
).expanduser()

if not firebase_admin._apps:
    if not credentials_path.exists():
        raise FileNotFoundError(f"Firebase credentials file not found: {credentials_path}")
    cred = credentials.Certificate(str(credentials_path))
    firebase_admin.initialize_app(cred)