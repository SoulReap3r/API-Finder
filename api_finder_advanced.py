#!/usr/bin/env python3
"""
Advanced API Endpoint Discovery Tool
- Crawls pages and JS files
- Multiple detection patterns
- Probes common paths with status codes
- Supports custom headers
- Outputs JSON / HTML report
"""

import argparse
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from typing import Set, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

API_PATTERNS = [
    r'["\'](/api/[^"\'\s<>]+)["\']',
    r'["\'](/v[0-9]+/[^"\'\s<>]+)["\']',
    r'["\'](/graphql[^"\'\s<>]*)["\']',
    r'["\'](https?://[^"\']+/(?:api|v[0-9]|graphql)[^"\']*)["\']',
    r'fetch\(\s*["\']([^"\']+)["\']',
    r'axios\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']',
    r'url\s*:\s*["\']([^"\']+)["\']',
    r'endpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'["\'](/rest/[^"\'\s]+)["\']',
    r'["\'](/service/[^"\'\s]+)["\']',
]

COMMON_PATHS = [
    "/api", "/api/", "/api/v1", "/api/v2", "/api/v3", "/api/v1/", "/api/v2/",
    "/graphql", "/graphiql", "/playground",
    "/swagger", "/swagger.json", "/swagger/v1/swagger.json", "/swagger-ui",
    "/openapi.json", "/openapi.yaml", "/openapi/v1",
    "/docs", "/redoc", "/api-docs", "/api/docs",
    "/.well-known/openapi", "/.well-known/api",
    "/v1", "/v2", "/v3",
    "/rest", "/rest/api", "/services",
    "/health", "/status", "/ping", "/version",
    "/users", "/auth", "/login", "/token",
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


def fetch(url: str, headers: Dict = None, timeout: int = 12) -> tuple:
    """Returns (status, body, final_url)"""
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.status, body, resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception:
        return 0, "", url


def extract_endpoints(text: str, base_url: str) -> Set[str]:
    found = set()
    for pattern in API_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            raw = m.group(1) if m.lastindex else m.group(0)
            raw = raw.strip().split("?")[0].split("#")[0]
            if not raw or len(raw) > 200:
                continue
            if raw.startswith(("http://", "https://")):
                found.add(raw)
            elif raw.startswith("/"):
                found.add(urllib.parse.urljoin(base_url, raw))
            elif "/" in raw:
                found.add(urllib.parse.urljoin(base_url, "/" + raw))
    return found


def probe_path(base: str, path: str, headers: Dict) -> Dict:
    url = urllib.parse.urljoin(base, path)
    status, _, final = fetch(url, headers, timeout=8)
    return {"url": url, "status": status, "final": final}


def main():
    parser = argparse.ArgumentParser(description="Advanced API endpoint finder")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--js", action="store_true", help="Scan linked JavaScript files")
    parser.add_argument("--crawl", type=int, default=0, help="Crawl N additional pages")
    parser.add_argument("--probe", action="store_true", help="Probe common API paths")
    parser.add_argument("--workers", type=int, default=5, help="Parallel probe workers")
    parser.add_argument("--header", action="append", help="Custom header (Key:Value)")
    parser.add_argument("--output", "-o", help="Save JSON report")
    parser.add_argument("--html", help="Save HTML report")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base

    headers = {}
    if args.header:
        for h in args.header:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    print(f"[*] Target: {base}")
    print(f"[*] Started: {datetime.now().isoformat()}\n")

    all_endpoints = set()
    visited = set()
    to_visit = [base]

    pages_fetched = 0
    max_pages = 1 + args.crawl
    while to_visit and pages_fetched < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        pages_fetched += 1

        print(f"[*] Fetching: {url}")
        status, body, final = fetch(url, headers)
        if status == 0:
            continue
        all_endpoints.update(extract_endpoints(body, base))

        if args.crawl and pages_fetched < max_pages:
            extractor = LinkExtractor()
            try:
                extractor.feed(body)
            except Exception:
                pass
            for link in extractor.links:
                full = urllib.parse.urljoin(base, link)
                if full.startswith(base) and full not in visited:
                    to_visit.append(full)

        time.sleep(args.delay)

    if args.js:
        print("\n[*] Scanning JavaScript files...")
        status, body, _ = fetch(base, headers)
        extractor = LinkExtractor()
        try:
            extractor.feed(body)
        except Exception:
            pass
        for src in list(extractor.scripts)[:20]:
            js_url = urllib.parse.urljoin(base, src)
            print(f"  -> {js_url}")
            _, js_body, _ = fetch(js_url, headers)
            all_endpoints.update(extract_endpoints(js_body, base))
            time.sleep(args.delay)

    probed = []
    if args.probe:
        print(f"\n[*] Probing {len(COMMON_PATHS)} common paths with {args.workers} workers...")
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = [ex.submit(probe_path, base, p, headers) for p in COMMON_PATHS]
            for fut in as_completed(futures):
                r = fut.result()
                if r["status"] and r["status"] < 500:
                    probed.append(r)
                    print(f"  [{r['status']}] {r['url']}")

    print("\n" + "=" * 50)
    print(f"Discovered endpoints from source: {len(all_endpoints)}")
    for ep in sorted(all_endpoints):
        print(f"  {ep}")

    if probed:
        print(f"\nProbed paths that responded: {len(probed)}")
        for p in sorted(probed, key=lambda x: x["status"]):
            print(f"  [{p['status']}] {p['url']}")

    report = {
        "target": base,
        "timestamp": datetime.now().isoformat(),
        "from_source": sorted(all_endpoints),
        "probed": probed,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(f"\n[*] JSON saved: {args.output}")

    if args.html:
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>API Discovery - {base}</title>
<style>body{{font-family:sans-serif;margin:2em}} li{{margin:4px 0}} .ok{{color:green}} .auth{{color:orange}}</style>
</head><body>
<h1>API Discovery Report</h1>
<p>Target: <a href="{base}">{base}</a></p>
<p>Generated: {report['timestamp']}</p>
<h2>From Source ({len(all_endpoints)})</h2>
<ul>{''.join(f'<li><a href="{e}">{e}</a></li>' for e in sorted(all_endpoints))}</ul>
<h2>Probed ({len(probed)})</h2>
<ul>{''.join(f'<li class="{"ok" if p["status"]<400 else "auth"}">[{p["status"]}] <a href="{p["url"]}">{p["url"]}</a></li>' for p in probed)}</ul>
</body></html>"""
        Path(args.html).write_text(html)
        print(f"[*] HTML saved: {args.html}")

    print("\n[*] Done.")


if __name__ == "__main__":
    main()
