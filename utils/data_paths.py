from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_ROOT / "content"
QUESTIONS_DIR = PROJECT_ROOT / "questions"
DATA_DIR = PROJECT_ROOT / "data"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

