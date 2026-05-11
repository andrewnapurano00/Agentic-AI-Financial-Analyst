from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
ENV_FILE = ROOT / ".env"

# Load .env from the project root before importing the app
load_dotenv(dotenv_path=ENV_FILE, override=True)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from langgraphagenticai.main import load_langgraph_agenticai_app


if __name__ == "__main__":
    load_langgraph_agenticai_app()