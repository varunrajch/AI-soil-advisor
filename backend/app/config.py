"""Settings, read once from the environment (and the project .env file)."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=value lines, existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and name and not name.startswith("#"):
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    groq_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("GROQ_API_KEY") or None)
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "openai/gpt-oss-120b"))
    docs_dir: Path = field(default_factory=lambda: Path(os.environ.get("DOCS_DIR", ROOT / "docs")))
    index_dir: Path = field(default_factory=lambda: Path(os.environ.get("INDEX_DIR", ROOT / "backend" / "index")))
    embed_model: str = field(default_factory=lambda: os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5"))
    frontend_dist: Path = field(default_factory=lambda: ROOT / "frontend" / "dist")
    max_upload_mb: int = 8
    cors_origins: List[str] = field(default_factory=lambda: os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","))


settings = Settings()
