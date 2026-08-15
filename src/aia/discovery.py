from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import AiaError


@dataclass(frozen=True)
class Candidate:
    name: str
    size_bytes: int
    vram_bytes: int

    @property
    def display(self) -> str:
        gib = self.size_bytes / 1024**3
        vram = self.vram_bytes / 1024**3
        return f"{self.name} ({gib:.1f} GB, ~{vram:.1f} GB VRAM)"


class _LibraryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, str]] = []
        self._current_name: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        match = re.fullmatch(r"/library/([a-zA-Z0-9_.-]+)", href)
        if match:
            self._current_name = match.group(1)
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_name:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_name:
            if all(name != self._current_name for name, _ in self.entries):
                self.entries.append((self._current_name, " ".join(self._current_text)))
            self._current_name = None
            self._current_text = []


class _TagParser(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        prefix = f"/library/{self.name}:"
        if href.startswith(prefix):
            model_tag = href.removeprefix(prefix)
            if re.fullmatch(r"\d+(?:\.\d+)?[bm]", model_tag.lower()) and model_tag not in self.tags:
                self.tags.append(model_tag)

class LibraryClient:
    """Discover popular local text models from Ollama's live library.

    Ollama's public library does not expose a stable catalogue API. Its library
    page provides popularity order, while registry manifests provide exact blob
    sizes. Fail closed when either source changes instead of suggesting a model
    whose fit cannot be established.
    """

    LIBRARY_URL = "https://ollama.com/library"
    REGISTRY_URL = "https://registry.ollama.ai/v2/library"
    SPECIALIZED = re.compile(
        r"\b(embedding|embed model|ocr|code-specific|code completion|"
        r"translation model|safety classification)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.library_url = os.environ.get("AIA_LIBRARY_URL", self.LIBRARY_URL)
        self.tags_url = os.environ.get("AIA_TAGS_URL", "https://ollama.com/library")
        self.registry_url = os.environ.get("AIA_REGISTRY_URL", self.REGISTRY_URL)

    def _read(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": "aia/0.1"})
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise AiaError("Model discovery unavailable. Try again later.") from error

    def popular_names(self) -> list[str]:
        parser = _LibraryParser()
        parser.feed(self._read(self.library_url).decode("utf-8", errors="replace"))
        if not parser.entries:
            raise AiaError("Model discovery unavailable. Try again later.")
        return [name for name, text in parser.entries if not self.SPECIALIZED.search(text)]

    def _manifest_size(self, name: str, tag: str) -> int | None:
        url = f"{self.registry_url}/{name}/manifests/{tag}"
        try:
            manifest = json.loads(self._read(url))
        except (AiaError, ValueError):
            return None
        layers = manifest.get("layers", [])
        total = sum(int(layer.get("size", 0)) for layer in layers)
        return total or None

    def _tags(self, name: str) -> list[str]:
        parser = _TagParser(name)
        try:
            parser.feed(
                self._read(f"{self.tags_url}/{name}/tags").decode("utf-8", errors="replace")
            )
        except AiaError:
            return []
        return parser.tags

    def candidates(self, available_vram: int, installed: set[str]) -> list[Candidate]:
        candidates: list[Candidate] = []
        for name in self.popular_names():
            if name in installed or any(model.startswith(f"{name}:") for model in installed):
                continue
            variants: list[tuple[int, str]] = []
            for tag in self._tags(name):
                size = self._manifest_size(name, tag)
                if size is not None and int(size * 1.10) <= available_vram:
                    variants.append((size, tag))
            if not variants:
                continue
            size, tag = max(variants)
            # Model blobs dominate both download and GPU allocation. Keep 10%
            # headroom for metadata/runtime allocations and reject uncertain fits.
            required = int(size * 1.10)
            model = name if tag == "latest" else f"{name}:{tag}"
            candidates.append(Candidate(model, size, required))
            if len(candidates) == 21:
                break
        if not candidates:
            raise AiaError("No compatible models found. Free GPU memory or try later.")
        return candidates
