#!/usr/bin/env python3
"""
Simple API endpoint discovery tool.
Fetches a website, scans HTML/JS for likely API paths, and optionally probes common endpoints.
"""

import argparse
import re
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from typing import Set, List
import json

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Common API path patterns
API_PATTERNS = [
    r'["\'](/api/[^"\'\s]+)["\']',
    r'["\'](/v[0-9]+/[^"\'\s]+)["\']',
    r'["\'](/graphql[^"\'\s]*)["\']',
    r'["\'](https?://[^"\']+/api/[^"\']+)["\']',
    r'fetch\(["\']([^"\']+)["\']',
    r'axios\.(get|post|put|delete)\(["\']([^"\']+)["\']',
    r'\.ajax\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)["\']',
    r'endpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
]

COMMON_PATHS = [
    "/api", "/api/v1", "/api/v2", "/api/v3",
    "/graphql", "/graphiql",
    "/swagger", "/swagger.json", "/swagger/v1/swagger.json",
    "/openapi.json", "/openapi.yaml",
    "/docs", "/redoc",
    "/.well-known/openapi",
    "/api-docs",
    "/v1", "/v2",
    "/rest", "/rest/api",
]


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
        self.scripts = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.add(attrs["href"])
        if tag == "script" and "src" in attrs:
            self.scripts.add(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet" and "href" in attrs:
            self.links.add(attrs["href"])


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [!] Failed to fetch {url}: {e}")
        return ""


def extract_from_text(text: str, base_url: str) -> Set[str]:
    found = set()
    for pattern in API_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            path = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
            if path.startswith(("http://", "https://")):
                found.add(path)
            elif path.startswith("/"):
                found.add(urllib.parse.urljoin(base_url, path))
            else:
                found.add(urllib.parse.urljoin(base_url, "/" + path))
    return found


def probe_common(base_url: str) -> List[str]:
    hits = []
    for path in COMMON_PATHS:
        url = urllib.parse.urljoin(base_url, path)
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status < 400:
                    hits.append(f"{url}  [{resp.status}]")
        except urllib.error.HTTPError as e:
            if e.code in (200, 401, 403):
                hits.append(f"{url}  [{e.code}]")
        except Exception:
            pass
    return hits


def main():
    parser = argparse.ArgumentParser(description="Find likely API endpoints on a website")
    parser.add_argument("url", help="Website URL (e.g. https://example.com)")
    parser.add_argument("--probe", action="store_true", help="Also probe common API paths")
    parser.add_argument("--js", action="store_true", help="Fetch and scan linked JavaScript files")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base

    print(f"[*] Target: {base}\n")

    print("[*] Fetching main page...")
    html = fetch(base)
    endpoints = extract_from_text(html, base)

    parser_html = LinkExtractor()
    try:
        parser_html.feed(html)
    except Exception:
        pass

    if args.js and parser_html.scripts:
        print(f"[*] Scanning {len(parser_html.scripts)} JavaScript files...")
        for src in list(parser_html.scripts)[:15]:
            js_url = urllib.parse.urljoin(base, src)
            print(f"  -> {js_url}")
            js_text = fetch(js_url)
            endpoints.update(extract_from_text(js_text, base))

    probed = []
    if args.probe:
        print("[*] Probing common API paths...")
        probed = probe_common(base)

    print("\n=== Discovered endpoints (from source) ===")
    if endpoints:
        for ep in sorted(endpoints):
            print(f"  {ep}")
    else:
        print("  (none found in HTML/JS)")

    if probed:
        print("\n=== Probed common paths that responded ===")
        for p in probed:
            print(f"  {p}")

    if args.output:
        data = {
            "target": base,
            "from_source": sorted(endpoints),
            "probed": probed,
        }
        Path(args.output).write_text(json.dumps(data, indent=2))
        print(f"\n[*] Saved to {args.output}")


if __name__ == "__main__":
    main()
