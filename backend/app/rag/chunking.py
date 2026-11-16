"""Split PDF pages into overlapping chunks that remember their document and page."""
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class Chunk:
    doc: str
    title: str
    page: int
    url: Optional[str]
    text: str

    def to_dict(self):
        return asdict(self)


def clean(text: str) -> str:
    text = text.replace("­", "")  # soft hyphens
    text = re.sub(r"-\n(\w)", r"\1", text)  # words broken across lines
    return re.sub(r"\s+", " ", text).strip()


def split_text(text: str, size: int = 800, overlap: int = 150, min_len: int = 120) -> List[str]:
    """Greedy word-boundary windows of about `size` chars, overlapping by `overlap` chars."""
    words = text.split(" ")
    chunks, current, length = [], [], 0
    for word in words:
        current.append(word)
        length += len(word) + 1
        if length >= size:
            chunks.append(" ".join(current))
            # keep the tail as overlap for the next window
            tail, tail_len = [], 0
            for w in reversed(current):
                tail_len += len(w) + 1
                if tail_len > overlap:
                    break
                tail.insert(0, w)
            current, length = tail, sum(len(w) + 1 for w in tail)
    if current and length >= min_len:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c) >= min_len]


def read_sources(docs_dir: Path) -> Dict[str, Dict[str, str]]:
    """Titles and URLs from docs/SOURCES.md table rows: | `file.pdf` | title | url |"""
    meta = {}
    path = docs_dir / "SOURCES.md"
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r"\|\s*`([^`]+\.pdf)`\s*\|\s*(.+?)\s*\|\s*(\S+)\s*\|", line)
            if m:
                meta[m.group(1)] = {"title": m.group(2).replace("*", ""), "url": m.group(3)}
    return meta


def chunk_pages(doc: str, pages: Iterable[str], title: str, url: Optional[str]) -> List[Chunk]:
    out = []
    for page_no, raw in enumerate(pages, start=1):
        for piece in split_text(clean(raw or "")):
            out.append(Chunk(doc=doc, title=title, page=page_no, url=url, text=piece))
    return out


def chunk_pdf(path: Path, title: str, url: Optional[str]) -> List[Chunk]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return chunk_pages(path.name, (p.extract_text() for p in reader.pages), title, url)
