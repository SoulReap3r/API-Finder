# API-Finder

Simple and advanced tools to discover API endpoints on websites by scanning HTML, JavaScript, and probing common paths.

No external dependencies — uses only the Python standard library.

**Authorized use only.** Do not run against systems you do not own or have explicit permission to test.

## Scripts

| File | Description |
|------|-------------|
| `api_finder.py` | Basic version — fast scan of HTML + optional JS + common path probing |
| `api_finder_advanced.py` | Advanced version — crawling, parallel probing, custom headers, HTML/JSON reports, optional security checks |

## Requirements

- Python 3.7+

## Basic usage

```bash
# Scan a site
python api_finder.py https://example.com

# Also scan linked JS files
python api_finder.py https://example.com --js

# Probe common paths (/api, /swagger.json, /graphql, etc.)
python api_finder.py https://example.com --probe

# Save results
python api_finder.py https://example.com --js --probe -o results.json
```

## Advanced usage

```bash
# Probe common paths
python api_finder_advanced.py https://example.com --probe

# Scan JS + crawl 3 more pages
python api_finder_advanced.py https://example.com --js --crawl 3

# Custom header + HTML report
python api_finder_advanced.py https://example.com --probe --header "Authorization: Bearer TOKEN" --html report.html

# Safe security checks (sensitive paths + missing headers)
python api_finder_advanced.py https://example.com --security

# Full run
python api_finder_advanced.py https://example.com --js --probe --security --crawl 2 -o results.json --html report.html
```

### Advanced options

| Flag | Description |
|------|-------------|
| `--js` | Scan linked JavaScript files |
| `--crawl N` | Follow and scan N additional pages on the same domain |
| `--probe` | Probe common API paths and show status codes |
| `--security` | Run safe configuration checks (sensitive paths + security headers). **Authorized use only.** |
| `--workers N` | Parallel workers for probing (default: 5) |
| `--header "Key: Value"` | Add custom headers (can be used multiple times) |
| `--output FILE` / `-o` | Save JSON report |
| `--html FILE` | Save clickable HTML report |
| `--delay SECONDS` | Delay between requests (default: 0.2) |

## Security checks (`--security`)

This mode performs **passive / low-impact configuration review only**:

- Probes common sensitive paths (`.env`, `.git`, backups, debug endpoints, etc.)
- Checks for missing security headers (HSTS, CSP, X-Frame-Options, etc.)
- Does **not** send exploit payloads, attempt injection, or brute-force anything

Use only on systems you are authorized to test.

## What it looks for

- Paths like `/api/`, `/v1/`, `/graphql`, `/rest/`
- `fetch()`, `axios.get/post`, `$.ajax` URLs
- `endpoint`, `baseURL` variables
- Common documentation endpoints (`/swagger.json`, `/openapi.json`, `/docs`, etc.)

## Output

- Printed list of discovered endpoints
- Optional JSON report
- Optional HTML report with clickable links (advanced)
- Security findings section when `--security` is used

## Notes

- This is a discovery and configuration-review tool. It does not bypass authentication or exploit vulnerabilities.
- Use responsibly and only on sites you are allowed to test.
- Some endpoints may return 401/403 — that still means the path exists.
- Unauthorized scanning or testing can be illegal.

## License

MIT
