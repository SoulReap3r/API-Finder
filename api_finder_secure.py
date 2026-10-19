#!/usr/bin/env python3
"""
API Finder — Security-Aware Edition
Requires explicit Y/N confirmation that the user has authorization
before running any security configuration checks.

AUTHORIZED USE ONLY.
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
]

COMMON_PATHS = [
    "/api", "/api/v1", "/api/v2", "/graphql", "/swagger.json",
    "/openapi.json", "/docs", "/health", "/status",
]

SENSITIVE_PATHS = [
    "/.env", "/.env.local", "/.git/config", "/.git/HEAD",
    "/backup.zip", "/backup.tar.gz", "/db.sql", "/dump.sql",
    "/config.json", "/wp-config.php", "/web.config",
    "/admin", "/phpinfo.php", "/server-status",
    "/debug", "/actuator/env", "/actuator/health",
    "/robots.txt",
]

SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
]


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and "src" in attrs:
            self.scripts.add(attrs["src"])


def fetch(url: str, headers: Dict = None, timeout: int = 12) -> tuple:
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
    return found


def probe_path(base: str, path: str, headers: Dict) -> Dict:
    url = urllib.parse.urljoin(base, path)
    status, body, final = fetch(url, headers, timeout=8)
    return {"url": url, "status": status, "final": final}


def check_security_headers(url: str, headers: Dict) -> Dict:
    req = urllib.request.Request(
        url,
        headers={**{"User-Agent": USER_AGENT}, **(headers or {})},
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            missing = [h for h in SECURITY_HEADERS if h not in resp_headers]
            return {"url": url, "status": resp.status, "missing_headers": missing}
    except Exception as e:
        return {"url": url, "error": str(e), "missing_headers": SECURITY_HEADERS}


def require_authorization() -> bool:
    print("\n" + "=" * 60)
    print("AUTHORIZATION REQUIRED")
    print("=" * 60)
    print("Security checks will probe for sensitive paths and missing headers.")
    print("You must have explicit permission to test the target system.")
    print("Unauthorized testing may be illegal.")
    print()
    answer = input("Do you have authorization to test this target? (Y/N): ").strip().upper()
    if answer != "Y":
        print("\n[!] Authorization not confirmed. Security checks aborted.")
        return False
    print("[+] Authorization confirmed. Proceeding with security checks.\n")
    return True


def run_security_checks(base: str, headers: Dict, workers: int) -> Dict:
    findings = {"sensitive_paths": [], "missing_headers": [], "notes": []}
    print("[*] Running security configuration checks...")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(probe_path, base, p, headers) for p in SENSITIVE_PATHS]
        for fut in as_completed(futures):
            r = fut.result()
            if r["status"] and r["status"] < 400:
                findings["sensitive_paths"].append(r)
                print(f"  [!] Exposed: [{r['status']}] {r['url']}")
    header_result = check_security_headers(base, headers)
    if header_result.get("missing_headers"):
        findings["missing_headers"] = header_result["missing_headers"]
        print(f"  [!] Missing security headers: {', '.join(header_result['missing_headers'])}")
    findings["notes"].append("Configuration checks only. No exploit payloads sent.")
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="API Finder with mandatory authorization for security checks"
    )
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--js", action="store_true", help="Scan linked JavaScript")
    parser.add_argument("--probe", action="store_true", help="Probe common API paths")
    parser.add_argument("--security", action="store_true",
                        help="Run security checks (requires Y/N authorization)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--header", action="append", help="Custom header Key:Value")
    parser.add_argument("--output", "-o", help="JSON report path")
    parser.add_argument("--html", help="HTML report path")
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

    print("[*] Fetching main page...")
    status, body, _ = fetch(base, headers)
    endpoints = extract_endpoints(body, base) if status else set()

    if args.js:
        extractor = LinkExtractor()
        try:
            extractor.feed(body)
        except Exception:
            pass
        for src in list(extractor.scripts)[:10]:
            js_url = urllib.parse.urljoin(base, src)
            print(f"  -> JS: {js_url}")
            _, js_body, _ = fetch(js_url, headers)
            endpoints.update(extract_endpoints(js_body, base))

    probed = []
    if args.probe:
        print("[*] Probing common paths...")
        for path in COMMON_PATHS:
            r = probe_path(base, path, headers)
            if r["status"] and r["status"] < 500:
                probed.append(r)
                print(f"  [{r['status']}] {r['url']}")

    security = {}
    if args.security:
        if require_authorization():
            security = run_security_checks(base, headers, args.workers)
        else:
            security = {"aborted": True, "reason": "User did not confirm authorization"}

    print("\n" + "=" * 50)
    print(f"Endpoints from source: {len(endpoints)}")
    for ep in sorted(endpoints):
        print(f"  {ep}")

    report = {
        "target": base,
        "timestamp": datetime.now().isoformat(),
        "from_source": sorted(endpoints),
        "probed": probed,
        "security": security,
        "authorization_required": True,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(f"\n[*] JSON: {args.output}")

    if args.html:
        sec_section = ""
        if security.get("aborted"):
            sec_section = "<p><strong>Security checks aborted — authorization not confirmed.</strong></p>"
        elif security:
            sec_section = "<h2>Security Checks</h2>"
            if security.get("sensitive_paths"):
                sec_section += "<ul>" + "".join(
                    f'<li>[{p["status"]}] <a href="{p["url"]}">{p["url"]}</a></li>'
                    for p in security["sensitive_paths"]
                ) + "</ul>"
            if security.get("missing_headers"):
                sec_section += f"<p>Missing headers: {', '.join(security['missing_headers'])}</p>"
            sec_section += "<p><em>Authorized use only. No exploit payloads.</em></p>"

        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Report - {base}</title>
<style>body{{font-family:sans-serif;margin:2em}}</style></head><body>
<h1>API Finder Report</h1>
<p>Target: <a href="{base}">{base}</a></p>
<p>Generated: {report['timestamp']}</p>
<h2>Endpoints ({len(endpoints)})</h2>
<ul>{''.join(f'<li><a href="{e}">{e}</a></li>' for e in sorted(endpoints))}</ul>
{sec_section}
</body></html>"""
        Path(args.html).write_text(html)
        print(f"[*] HTML: {args.html}")

    print("\n[*] Done.")


if __name__ == "__main__":
    main()
