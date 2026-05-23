from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import warnings
from datetime import datetime, date, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DIGEST_DIR = OUTPUT_DIR / "digests"
LOG_DIR = OUTPUT_DIR / "logs"
SITE_DIR = OUTPUT_DIR / "site"

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def load_config() -> dict[str, Any]:
    with (BASE_DIR / "config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_environment() -> None:
    load_dotenv(BASE_DIR / ".env")


def now_in_timezone(config: dict[str, Any]) -> datetime:
    tz_name = config.get("project", {}).get("timezone", "Asia/Shanghai")
    return datetime.now(ZoneInfo(tz_name))


def today_string(config: dict[str, Any]) -> str:
    return now_in_timezone(config).strftime("%Y-%m-%d")


def ensure_dirs() -> None:
    for path in [DATA_DIR, DATA_DIR / "source_cache", DIGEST_DIR, LOG_DIR, SITE_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(run_date: str) -> Path:
    ensure_dirs()
    log_path = LOG_DIR / f"{run_date}_run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return log_path


def clean_text(value: Any) -> str:
    if not value:
        return ""
    text = BeautifulSoup(str(value), "lxml").get_text(" ")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title: str) -> str:
    text = clean_text(title).lower()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = doi.removeprefix("https://doi.org/")
    doi = doi.removeprefix("http://doi.org/")
    doi = doi.removeprefix("doi:")
    return doi.strip()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def item_identity(item: dict[str, Any]) -> str:
    doi = normalize_doi(item.get("doi"))
    if doi:
        return f"doi:{doi}"
    for field, prefix in [
        ("openalex_id", "openalex"),
        ("arxiv_id", "arxiv"),
        ("url", "url"),
    ]:
        value = (item.get(field) or "").strip()
        if value:
            return f"{prefix}:{value}"
    title = normalize_title(item.get("title", ""))
    return f"title:{stable_hash(title)}"


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date()
    except Exception:
        return None


def iso_date_or_empty(value: Any) -> str:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else ""


def days_ago(config: dict[str, Any], days: int) -> str:
    return (now_in_timezone(config).date() - timedelta(days=days)).isoformat()


def abstract_from_openalex(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned.append((position, word))
    positioned.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in positioned)


def truncate(text: str, max_chars: int = 280) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rsplit(" ", 1)[0]
    return f"{cut}..."


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.warning("JSON 文件损坏，将使用默认值: %s", path)
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)
