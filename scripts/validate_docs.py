#!/usr/bin/env python3
"""Validate generated HTML structure, internal links, and public API coverage."""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "build/docs/v0.2"
SITE_URL_PATH = "/python/v0.2/"


def _public_symbols() -> set[str]:
    package = importlib.import_module("ktnode")
    names = set(package.__all__)
    vision = importlib.import_module("ktnode.vision")
    names.update(
        name
        for name in ("make_rgb_image", "encode_image_sample", "decode_image_sample_summary")
        if inspect.isfunction(getattr(vision, name, None))
    )
    return names


def _target_path(page: Path, href: str) -> tuple[Path, str]:
    parsed = urlsplit(href)
    raw = unquote(parsed.path)
    if raw.startswith(SITE_URL_PATH):
        target = SITE / raw.removeprefix(SITE_URL_PATH)
    elif raw.startswith("/"):
        target = SITE / raw.lstrip("/")
    else:
        target = page.parent / raw
    if raw.endswith("/") or not target.suffix:
        target = target / "index.html"
    return target.resolve(), parsed.fragment


def main() -> int:
    pages = sorted(SITE.rglob("*.html"))
    if not pages:
        raise SystemExit("documentation site has no HTML pages")

    errors: list[str] = []
    combined_text: list[str] = []
    site_root = SITE.resolve()
    for page in pages:
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        combined_text.append(soup.get_text(" ", strip=True))
        if page.name == "404.html":
            continue
        if page == SITE / "index.html":
            if soup.find("h1") is None or soup.find("nav") is None:
                errors.append(f"{page}: missing title or navigation landmark")
            search = soup.find(attrs={"role": "search"}) or soup.find("input", attrs={"type": "search"})
            if search is None:
                errors.append(f"{page}: missing search control")
        for element in soup.find_all(["a", "img"]):
            attr = "href" if element.name == "a" else "src"
            value = element.get(attr)
            if not value or value.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target, fragment = _target_path(page, value)
            if site_root not in target.parents and target != site_root:
                errors.append(f"{page}: link escapes site root: {value}")
                continue
            if not target.exists():
                errors.append(f"{page}: missing target: {value}")
                continue
            if fragment and target.suffix == ".html":
                target_soup = BeautifulSoup(target.read_text(encoding="utf-8"), "html.parser")
                if target_soup.find(id=fragment) is None:
                    errors.append(f"{page}: missing fragment: {value}")
        for image in soup.find_all("img"):
            if image.get("alt") is None:
                errors.append(f"{page}: image missing alt text")

    rendered = " ".join(combined_text)
    missing_api = sorted(name for name in _public_symbols() if name not in rendered)
    if missing_api:
        errors.append(f"public API missing from generated reference: {missing_api}")

    required = [SITE / "index.html", SITE / "search/search_index.json", SITE / "reference/api/index.html"]
    errors.extend(f"missing generated artifact: {path}" for path in required if not path.exists())
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated {len(pages)} HTML pages; all public symbols and internal links are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
