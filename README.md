# NetTest

A Python implementation of PowerShell's `Test-NetConnection` cmdlet — with colorized output, HTTP(S) requests, redirect following, traceroute, and JSON result export.

## Requirements

- Python 3.10+
- `colorama` *(optional — output still works without it)*

```bash
pip install colorama
```

No other third-party libraries required. Uses only the Python standard library.

## Usage

```
python nettest.py [-h] -p PORT -proto {tcp,udp} [-c] [--tls] [-L] [-v] [-t] [-o FILE] target
```

### Arguments

| Argument | Description |
|---|---|
| `target` | Target hostname or IP address *(required)* |
| `-p`, `--port` | Port to test *(required)* |
| `-proto` | Protocol — `tcp` or `udp` *(required)* |
| `-c`, `--curl` | Perform an HTTP(S) GET request |
| `--tls` | Use HTTPS instead of HTTP (use with `-c`) |
| `-L`, `--follow-redirects` | Follow HTTP redirects (up to 5 hops) |
| `-v`, `--verbose` | Increase verbosity; repeat for more detail (`-v` / `-vv` / `-vvv` / `-vvvv`) |
| `-t`, `--trace` | Perform a traceroute |
| `-o FILE` | Save results to a JSON file |

### Examples

```bash
# TCP port check
python nettest.py example.com -p 443 -proto tcp

# HTTPS request with verbose output
python nettest.py example.com -p 443 -proto tcp -c --tls -vv

# HTTP request following redirects, save results
python nettest.py example.com -p 80 -proto tcp -c -L -o results.json

# UDP port check with traceroute
python nettest.py 1.1.1.1 -p 53 -proto udp -t
```

## Output

Each run prints:

- Local and resolved remote IP
- Ping result
- TCP/UDP port status
- HTTP(S) response status *(if `-c` is used)*
- Traceroute output *(if `-t` is used)*
- Pass/fail summary

Results saved with `-o` are JSON, and include a UTC timestamp.

## Notes

- Targets are validated before any network activity — malformed hostnames and IPs are rejected early
- All network operations have timeouts; nothing hangs indefinitely
- HTTPS uses `ssl.create_default_context()` — certificate verification is enforced by default
- UDP "open" detection is best-effort; a non-response may mean open *or* silently filtered
- `colorama` is optional; if not installed, output is plain text with no crashes
- No external tools required (`curl`, `ping`, `traceroute` are invoked as system binaries where available)
