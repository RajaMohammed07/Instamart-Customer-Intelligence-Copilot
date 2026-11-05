from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
CLEAN_DIR = DATA_DIR / 'clean'
POLICY_DIR = DATA_DIR / 'policies'
OUTPUTS_DIR = ROOT / 'outputs'
STATE_DIR = ROOT / 'state'
DB_PATH = DATA_DIR / 'instamart.db'
