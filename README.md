# API-Finder

Simple and advanced tools to discover API endpoints on websites by scanning HTML, JavaScript, and probing common paths.

No external dependencies — uses only the Python standard library.

**Authorized use only.** Do not run against systems you do not own or have explicit permission to test.

## Scripts

| File | Description |
|------|-------------|
| `api_finder.py` | Basic version — fast scan of HTML + optional JS + common path probing |
| `api_finder_advanced.py` | Advanced version — crawling, parallel probing, custom headers, HTML/JSON reports, optional security checks |
| `api_finder_secure.py` | Security-aware edition — **requires Y/N authorization** before any security checks |

## Requirements

- Python 3.7+

## Basic usage

```bash
python api_finder.py https://example.com
python api_finder.py https://example.com --js --probe
```

## Advanced usage

```bash
python api_finder_advanced.py https://example.com --probe
python api_finder_advanced.py https://example.com --js --crawl 3
python api_finder_advanced.py https://example.com --security
python api_finder_advanced.py https://example.com --js --probe --security --html report.html
```

## Security-aware edition (mandatory Y/N)

```bash
python api_finder_secure.py https://example.com --security
python api_finder_secure.py https://example.com --probe --security --html report.html
```

When you use `--security`, the script will prompt:

```
Do you have authorization to test this target? (Y/N):
```

- Answer **Y** to proceed with security checks.
- Any other answer aborts the security checks (discovery still runs).

Security checks remain configuration-only:
- Sensitive path probing (`.env`, `.git`, backups, debug endpoints)
- Missing security header detection
- No exploit payloads

## Notes

- Authorized use only.
- Does not bypass authentication or send exploit payloads.
- Unauthorized testing can be illegal.

## License

MIT
