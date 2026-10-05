import os
import sys
from pathlib import Path

# Keep the repository root importable when pytest is launched from any directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Unit tests do not need a live PostgreSQL/LLM service.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-change-me")
os.environ.setdefault("AI_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
