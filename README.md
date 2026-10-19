# API-Finder

Simple and advanced tools to discover API endpoints on websites by scanning HTML, JavaScript, and probing common paths.

No external dependencies — uses only the Python standard library.

## Scripts

| File | Description |
|------|-------------|
| `api_finder.py` | Basic version — fast scan of HTML + optional JS + common path probing |
| `api_finder_advanced.py` | Advanced version — crawling, parallel probing, custom headers, HTML/JSON reports |

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

# Full run
python api_finder_advanced.py https://example.com --js --probe --crawl 2 -o results.json --html report.html
```

### Advanced options

| Flag | Description |
|------|-------------|
| `--js` | Scan linked JavaScript files |
| `--crawl N` | Follow and scan N additional pages on the same domain |
| `--probe` | Probe common API paths and show status codes |
| `--workers N` | Parallel workers for probing (default: 5) |
| `--header "Key: Value"` | Add custom headers (can be used multiple times) |
| `--output FILE` / `-o` | Save JSON report |
| `--html FILE` | Save clickable HTML report |
| `--delay SECONDS` | Delay between requests (default: 0.2) |

## What it looks for

- Paths like `/api/`, `/v1/`, `/graphql`, `/rest/`
- `fetch()`, `axios.get/post`, `$.ajax` URLs
- `endpoint`, `baseURL` variables
- Common documentation endpoints (`/swagger.json`, `/openapi.json`, `/docs`, etc.)

## Output

- Printed list of discovered endpoints
- Optional JSON report
- Optional HTML report with clickable links (advanced)

## Notes

- This is a discovery tool. It does not bypass authentication.
- Use responsibly and only on sites you are allowed to test.
- Some endpoints may return 401/403 — that still means the path exists.

## License

MIT
