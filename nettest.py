#!/usr/bin/env python3
"""
nettest.py - Network Connection Tester
"""

import argparse
import socket
import subprocess
import platform
import http.client
import ssl
import datetime
import json
import sys
import re
import threading
import time

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

# ---------------------------------------------------------------------------
# Output helpers (single color system via colorama; graceful fallback)
# ---------------------------------------------------------------------------

class C:
    """Thin wrapper so we don't crash when colorama is absent."""
    @staticmethod
    def _w(code, text):
        return f"{code}{text}{Style.RESET_ALL}" if HAS_COLOR else text

    header  = lambda _, t: C._w(_, Fore.CYAN + Style.BRIGHT, t)
    success = lambda _, t: C._w(_, Fore.GREEN, t)
    error   = lambda _, t: C._w(_, Fore.RED, t)
    info    = lambda _, t: C._w(_, Fore.YELLOW, t)
    detail  = lambda _, t: C._w(_, Fore.BLUE, t)

c = C()

def print_header(title):  print(c.header(f"\n=== {title} ==="))
def print_success(msg):   print(c.success(f"[SUCCESS] {msg}"))
def print_error(msg):     print(c.error(f"[ERROR]   {msg}"))
def print_info(msg):      print(c.info(f"[INFO]    {msg}"))
def print_detail(msg):    print(c.detail(f"          {msg}"))

# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

# Loose but effective: rejects obvious junk before hitting DNS
_HOSTNAME_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
)

def validate_target(target: str) -> str:
    """Return target unchanged if valid, raise ValueError otherwise."""
    # Allow plain IPv4/IPv6
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            socket.inet_pton(family, target)
            return target
        except OSError:
            pass
    if _HOSTNAME_RE.match(target) and len(target) <= 253:
        return target
    raise ValueError(f"Invalid target: {target!r}")

# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def get_local_ip() -> str:
    """Return the primary outbound IP (avoids 127.0.0.1 on Linux)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))   # no data sent
            return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def resolve_hostname(target: str) -> str | None:
    """Resolve hostname → IP; return None on failure."""
    try:
        ip = socket.getaddrinfo(target, None, socket.AF_UNSPEC,
                                socket.SOCK_STREAM)[0][4][0]
        print_success(f"Resolved {target!r} → {ip}")
        return ip
    except socket.gaierror as exc:
        print_error(f"DNS resolution failed: {exc}")
        return None


def ping(target: str, timeout: int = 5) -> bool:
    """ICMP ping; returns True on success."""
    print_info(f"Pinging {target} …")
    flag = "-n" if platform.system().lower() == "windows" else "-c"
    w_flag = ["-w", str(timeout * 1000)] if platform.system().lower() == "windows" \
             else ["-W", str(timeout)]
    cmd = ["ping", flag, "1", *w_flag, target]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2,   # subprocess-level safety net
        )
        ok = result.returncode == 0
        (print_success if ok else print_error)(
            f"Ping {'succeeded' if ok else 'failed'} for {target}"
        )
        return ok
    except subprocess.TimeoutExpired:
        print_error(f"Ping timed out after {timeout}s")
        return False
    except FileNotFoundError:
        print_error("'ping' binary not found on this system")
        return False


def test_tcp_port(target: str, port: int, timeout: int = 3) -> bool:
    """Return True if the TCP port accepts a connection."""
    try:
        with socket.create_connection((target, port), timeout=timeout):
            print_success(f"TCP {target}:{port} is open")
            return True
    except ConnectionRefusedError:
        print_error(f"TCP {target}:{port} is closed (connection refused)")
    except socket.timeout:
        print_error(f"TCP {target}:{port} timed out")
    except OSError as exc:
        print_error(f"TCP {target}:{port} error: {exc}")
    return False


def test_udp_port(target: str, port: int, timeout: int = 2) -> bool:
    """
    Send an empty UDP datagram and wait for a response.
    UDP "open" detection is inherently unreliable; treat result as best-effort.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.sendto(b"\x00", (target, port))
            sock.recvfrom(1024)
            print_success(f"UDP {target}:{port} responded")
            return True
        except socket.timeout:
            print_info(f"UDP {target}:{port} — no response (may be filtered or open)")
            return False
        except OSError as exc:
            print_error(f"UDP {target}:{port} error: {exc}")
            return False


def perform_http_request(
    host: str,
    port: int = 80,
    use_tls: bool = False,
    verbose: int = 0,
    follow_redirects: bool = False,
    max_redirects: int = 5,
) -> tuple[int | None, str, list]:
    """
    HTTP(S) GET /  with optional redirect following and curl-style verbosity.
    Returns (status_code, reason, headers).
    """
    scheme = "https" if use_tls else "http"
    url = f"{scheme}://{host}:{port}/"
    redirect_count = 0
    path = "/"

    while True:
        conn = None
        try:
            t0 = datetime.datetime.now()

            if verbose >= 1:
                print_info(f"Connecting to {host}:{port} ({scheme.upper()}) …")

            if use_tls:
                ctx = ssl.create_default_context()
                conn = http.client.HTTPSConnection(host, port, timeout=10, context=ctx)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=10)

            req_headers = {"User-Agent": "nettest/1.0", "Accept": "*/*",
                           "Connection": "close"}

            if verbose >= 2:
                print(f"\n> GET {path} HTTP/1.1")
                for k, v in req_headers.items():
                    print(f"> {k}: {v}")
                print(">")

            conn.request("GET", path, headers=req_headers)
            resp = conn.getresponse()
            elapsed = (datetime.datetime.now() - t0).total_seconds()

            status  = resp.status
            reason  = resp.reason
            headers = resp.getheaders()
            hdict   = dict(headers)

            if verbose >= 2:
                print(f"\n< HTTP/1.1 {status} {reason}")
                for k, v in headers:
                    print(f"< {k}: {v}")
                print("<")

            if verbose >= 1:
                print_detail(f"Status: {status} {reason}")
                print_detail(f"Content-Type:   {hdict.get('Content-Type', '-')}")
                print_detail(f"Content-Length: {hdict.get('Content-Length', '-')}")
                print_detail(f"Elapsed: {elapsed:.3f}s")

            if verbose >= 3:
                body = resp.read(1024).decode("utf-8", errors="replace")
                print("\n[Body preview]")
                print(body[:500] + ("…" if len(body) == 1024 else ""))

            # Redirect handling
            if follow_redirects and status in (301, 302, 303, 307, 308):
                location = hdict.get("Location", "")
                if not location:
                    break
                redirect_count += 1
                if redirect_count > max_redirects:
                    print_error(f"Too many redirects (>{max_redirects})")
                    break
                print_info(f"Redirect {redirect_count}: {location}")
                # Simple same-host path redirect; full URL parsing out of scope
                if location.startswith("/"):
                    path = location
                    conn.close()
                    continue
                # Cross-host redirect — just report and stop
                print_info("Cross-host redirect detected; not following further")
                break

            return status, reason, headers

        except ssl.SSLError as exc:
            print_error(f"TLS error: {exc}")
            return None, str(exc), []
        except (http.client.HTTPException, OSError) as exc:
            print_error(f"HTTP request failed: {exc}")
            return None, str(exc), []
        finally:
            if conn:
                conn.close()
        break   # reached only when not redirecting

    return None, "no response", []


def traceroute(target: str, timeout: int = 30) -> None:
    """Run traceroute/tracert."""
    print_info(f"Traceroute to {target} …")
    cmd = (["tracert", target] if platform.system().lower() == "windows"
           else ["traceroute", "-n", target])
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        if result.returncode == 0:
            print_success("Traceroute complete")
            print(result.stdout.decode(errors="replace"))
        else:
            print_error("Traceroute failed")
            print(result.stderr.decode(errors="replace"))
    except subprocess.TimeoutExpired:
        print_error(f"Traceroute timed out after {timeout}s")
    except FileNotFoundError:
        print_error("traceroute binary not found")


def save_results(results: dict, path: str) -> None:
    try:
        with open(path, "w") as fh:
            json.dump(results, fh, indent=4, default=str)
        print_success(f"Results saved → {path}")
    except OSError as exc:
        print_error(f"Could not write {path}: {exc}")


# ---------------------------------------------------------------------------
# Spinner (fixed: only runs while work is in progress)
# ---------------------------------------------------------------------------

class Spinner:
    _FRAMES = "|/-\\"

    def __init__(self, label: str = "Working"):
        self._label = label
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self._FRAMES[i % len(self._FRAMES)]
            sys.stdout.write(f"\r{c.info(self._label)} {frame} ")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Network Connection Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("target",
                   help="Target hostname or IP address")
    p.add_argument("-p", "--port", type=int, required=True,
                   help="TCP/UDP port to test")
    p.add_argument("-proto", "--protocol", choices=["tcp", "udp"], required=True,
                   help="Transport protocol")
    p.add_argument("-c", "--curl", action="store_true",
                   help="Perform HTTP(S) request")
    p.add_argument("--tls", action="store_true",
                   help="Use HTTPS instead of HTTP")
    p.add_argument("-L", "--follow-redirects", action="store_true",
                   help="Follow HTTP redirects (up to 5)")
    p.add_argument("-v", "--verbose", action="count", default=0,
                   help="Increase verbosity (-v / -vv / -vvv / -vvvv)")
    p.add_argument("-t", "--trace", action="store_true",
                   help="Perform traceroute")
    p.add_argument("-o", "--output", metavar="FILE",
                   help="Save JSON results to FILE")
    return p


def main() -> int:
    args = build_parser().parse_args()

    # --- validate target before any network activity ---
    try:
        target = validate_target(args.target)
    except ValueError as exc:
        print_error(str(exc))
        return 1

    print_header("Network Test")
    print_info(f"Local IP : {get_local_ip()}")

    # Results accumulator
    results: dict = {
        "target": target,
        "resolved_ip": None,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "ping": None,
        "tcp_port": None,
        "udp_port": None,
        "http_status": None,
    }

    ip = resolve_hostname(target)
    if not ip:
        return 1

    results["resolved_ip"] = ip
    print_info(f"Remote IP: {ip}")

    success_count = 0
    error_count   = 0

    # Ping
    ok = ping(ip)
    results["ping"] = "ok" if ok else "fail"
    success_count += ok
    error_count   += not ok

    # Port test
    if args.protocol == "tcp":
        ok = test_tcp_port(ip, args.port)
        results["tcp_port"] = ok
    else:
        ok = test_udp_port(ip, args.port)
        results["udp_port"] = ok
    success_count += ok
    error_count   += not ok

    # HTTP(S)
    if args.curl:
        status, reason, _ = perform_http_request(
            target,
            port=443 if args.tls else 80,
            use_tls=args.tls,
            verbose=args.verbose,
            follow_redirects=args.follow_redirects,
        )
        results["http_status"] = status
        if status is not None:
            print_success(f"HTTP {status} {reason}")
            success_count += 1
        else:
            print_error(f"HTTP failed: {reason}")
            error_count += 1

    # Traceroute
    if args.trace:
        traceroute(ip)

    # Save
    if args.output:
        save_results(results, args.output)

    # Summary
    print_header("Summary")
    print_info(f"Successful checks : {success_count}")
    print_info(f"Failed checks     : {error_count}")

    return 0 if error_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
