#!/usr/bin/env python3
"""Resumable bounded-concurrency Frida CodeShare crawler."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "Morgana-Frida-Indexer/1.0"
PROJECT_CARD = re.compile(
    r'<h2>\s*<a\s+href="https://codeshare\.frida\.re/(@[^"?#]+/[^"?#]+/)">(.*?)</a>\s*</h2>'
    r'.*?<h3>.*?</i>\s*([0-9,]+)\s*\|\s*<i[^>]*>.*?</i>\s*([0-9,.KM]+)\s*</h3>',
    re.I | re.S,
)
FIELD_PATTERNS = {
    "title": re.compile(r'projectName:\s*("(?:\\.|[^"\\])*")'),
    "slug": re.compile(r'projectSlug:\s*("(?:\\.|[^"\\])*")'),
    "source": re.compile(r'projectSource:\s*("(?:\\.|[^"\\])*")'),
    "description": re.compile(r'projectDesc:\s*("(?:\\.|[^"\\])*")'),
    "uuid": re.compile(r'projectUUID:\s*("(?:\\.|[^"\\])*")'),
}
FINGERPRINT = re.compile(r"Fingerprint:\s*([a-fA-F0-9]{64})")
POPULARITY = re.compile(r"<h3>\s*([0-9,]+)\s*\|\s*([0-9,.KM]+)\s*</h3>", re.I)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(url: str, cache_path: Path, refresh: bool, retries: int = 3) -> str:
    if cache_path.is_file() and not refresh:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8", errors="replace")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")
            return text
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} attempts: {url}: {last_error}")


def page_projects(page_html: str) -> dict[str, dict[str, Any]]:
    projects: dict[str, dict[str, Any]] = {}
    for project_path, title, likes, views in PROJECT_CARD.findall(page_html):
        projects[project_path] = {
            "browse_title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
            "likes": int(likes.replace(",", "")),
            "views": views.strip(),
        }
    return projects


def project_links(page_html: str) -> list[str]:
    return sorted(page_projects(page_html), key=str.lower)


def decode_js_string(raw: str) -> str:
    return json.loads(raw)


def parse_project(
    project_path: str,
    page_html: str,
    discovery_page: int,
    browse_metadata: dict[str, Any] | None = None,
    discovered_at: str | None = None,
) -> dict[str, Any]:
    fields: dict[str, str] = {}
    for name, pattern in FIELD_PATTERNS.items():
        match = pattern.search(page_html)
        if not match:
            raise ValueError(f"CodeShare project is missing {name}")
        fields[name] = decode_js_string(match.group(1))
    fingerprint_match = FINGERPRINT.search(page_html)
    fingerprint = fingerprint_match.group(1).lower() if fingerprint_match else ""
    source_hash = hashlib.sha256(fields["source"].encode("utf-8")).hexdigest()
    author, slug = project_path.strip("/").split("/", 1)
    author = author.lstrip("@")
    return {
        "source_provider": "codeshare",
        "source_id": f"codeshare:{author}/{slug}",
        "author": author,
        "slug": slug,
        "title": html.unescape(fields["title"]),
        "description": html.unescape(fields["description"]),
        "project_uuid": fields["uuid"],
        "project_url": f"https://codeshare.frida.re/@{author}/{slug}/",
        "source_code": fields["source"],
        "source_hash": source_hash,
        "codeshare_fingerprint": fingerprint,
        "fingerprint_matches_source_hash": bool(fingerprint and fingerprint == source_hash),
        "discovery_page": discovery_page,
        "popularity": browse_metadata or {},
        "discovered_at": discovered_at or datetime.now(timezone.utc).isoformat(),
        "license": "unknown",
        "license_source": "No per-project license detected by crawler",
        "distribution_status": "unknown-license",
    }


def crawl(cache_dir: Path, refresh: bool = False, workers: int = 6, max_pages: int = 500) -> dict[str, Any]:
    page_dir = cache_dir / "pages"
    project_dir = cache_dir / "projects"
    author_dir = cache_dir / "authors"
    search_dir = cache_dir / "search"
    previous_inventory_path = cache_dir / "codeshare-inventory.json"
    previous_discovery = {}
    if previous_inventory_path.is_file():
        try:
            previous_inventory = json.loads(previous_inventory_path.read_text(encoding="utf-8"))
            previous_discovery = {
                project["source_id"]: project.get("discovered_at")
                for project in previous_inventory.get("projects", [])
                if project.get("source_id")
            }
        except (OSError, json.JSONDecodeError):
            previous_discovery = {}
    discovered: dict[str, dict[str, Any]] = {}
    pages_scanned = 0
    pages_attempted = 0
    errors: list[dict[str, str]] = []
    for page in range(1, max_pages + 1):
        pages_attempted += 1
        try:
            body = fetch(
                f"https://codeshare.frida.re/browse?page={page}",
                page_dir / f"{page:04d}.html",
                refresh,
            )
        except RuntimeError as exc:
            errors.append({"source": f"browse:{page}", "error": str(exc)})
            continue
        page_metadata = page_projects(body)
        links = set(page_metadata)
        pages_scanned += 1
        new_links = links - set(discovered)
        if not links or (page > 1 and not new_links):
            break
        for link in sorted(new_links):
            discovered[link] = {"page": page, **page_metadata.get(link, {})}

    recovered_projects = 0
    search_recovered_projects = 0
    author_profiles_scanned = 0
    search_queries_scanned = 0
    if errors:
        pending_authors = {path.strip("/").split("/", 1)[0].lstrip("@") for path in discovered}
        scanned_authors: set[str] = set()
        for _round in range(4):
            current_authors = sorted(pending_authors - scanned_authors, key=str.lower)
            if not current_authors:
                break

            def load_author(author: str) -> tuple[str, dict[str, dict[str, Any]]]:
                body = fetch(
                    f"https://codeshare.frida.re/@{author}/",
                    author_dir / f"{author}.html",
                    refresh,
                )
                return author, page_projects(body)

            with ThreadPoolExecutor(max_workers=max(1, min(workers, 12))) as executor:
                futures = {executor.submit(load_author, author): author for author in current_authors}
                for future in as_completed(futures):
                    author = futures[future]
                    scanned_authors.add(author)
                    try:
                        _, projects = future.result()
                        author_profiles_scanned += 1
                    except Exception as exc:
                        errors.append({"source": f"author:{author}", "error": str(exc)})
                        continue
                    for project_path, metadata in projects.items():
                        if project_path not in discovered:
                            discovered[project_path] = {
                                "page": 0,
                                "recovered_from_author": author,
                                **metadata,
                            }
                            recovered_projects += 1
                            pending_authors.add(project_path.strip("/").split("/", 1)[0].lstrip("@"))

        search_terms = "abcdefghijklmnopqrstuvwxyz0123456789"

        def load_search(term: str) -> tuple[str, dict[str, dict[str, Any]]]:
            query = urllib.parse.urlencode({"query": term})
            body = fetch(
                f"https://codeshare.frida.re/search/?{query}",
                search_dir / f"{term}.html",
                refresh,
            )
            return term, page_projects(body)

        with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
            futures = {executor.submit(load_search, term): term for term in search_terms}
            for future in as_completed(futures):
                term = futures[future]
                try:
                    _, projects = future.result()
                    search_queries_scanned += 1
                except Exception as exc:
                    errors.append({"source": f"search:{term}", "error": str(exc)})
                    continue
                for project_path, metadata in projects.items():
                    if project_path not in discovered:
                        discovered[project_path] = {
                            "page": 0,
                            "recovered_from_search": term,
                            **metadata,
                        }
                        search_recovered_projects += 1

    projects: list[dict[str, Any]] = []

    def load_project(item: tuple[str, dict[str, Any]]) -> dict[str, Any]:
        project_path, metadata = item
        author, slug = project_path.strip("/").split("/", 1)
        cache_path = project_dir / author.lstrip("@") / f"{slug}.html"
        body = fetch(f"https://codeshare.frida.re/{project_path}", cache_path, refresh)
        author, slug = project_path.strip("/").split("/", 1)
        source_id = f"codeshare:{author.lstrip('@')}/{slug}"
        return parse_project(
            project_path, body, metadata["page"], metadata,
            previous_discovery.get(source_id),
        )

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 12))) as executor:
        futures = {executor.submit(load_project, item): item for item in discovered.items()}
        for future in as_completed(futures):
            project_path, _ = futures[future]
            try:
                projects.append(future.result())
            except Exception as exc:
                errors.append({"source": project_path, "error": str(exc)})

    projects.sort(key=lambda item: item["source_id"].lower())
    result = {
        "pages_scanned": pages_scanned,
        "pages_attempted": pages_attempted,
        "projects_discovered": len(discovered),
        "projects_fetched": len(projects),
        "author_profiles_scanned": author_profiles_scanned,
        "projects_recovered_from_authors": recovered_projects,
        "search_queries_attempted": 36,
        "search_queries_scanned": search_queries_scanned,
        "projects_recovered_from_search": search_recovered_projects,
        "errors": errors,
        "projects": projects,
    }
    write_json(cache_dir / "codeshare-inventory.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    arguments = parser.parse_args()
    result = crawl(arguments.cache_dir, arguments.refresh, arguments.workers)
    print(f"[CODESHARE] pages={result['pages_scanned']} discovered={result['projects_discovered']} fetched={result['projects_fetched']} errors={len(result['errors'])}")
    return 0 if result["projects_fetched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())