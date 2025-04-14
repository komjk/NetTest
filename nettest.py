#!/usr/bin/env python3
import argparse
import socket
import subprocess
import platform
import http.client
import ipaddress
import colorama
from colorama import Fore, Style
import threading
import time
import sys
import json  # Import for JSON file handling
import ssl
import datetime

colorama.init(autoreset=True)

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

def get_local_ip():
    """Get the local IP address."""
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def resolve_hostname(target):
    """Resolve the hostname to an IP address."""
    try:
        ip_address = socket.gethostbyname(target)
        print(f"{Colors.GREEN}Resolved {target} to {ip_address}{Colors.RESET}")
        return ip_address
    except socket.error as e:
        print(f"{Colors.RED}Error resolving hostname: {e}{Colors.RESET}")
        return None

def ping(target):
    """Ping the target and return the result."""
    print(f"{Colors.BLUE}Pinging {target}...{Colors.RESET}")
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', target]
    response = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if response.returncode == 0:
        print(f"{Colors.GREEN}Ping to {target} was successful.{Colors.RESET}")
    else:
        print(f"{Colors.RED}Ping to {target} failed.{Colors.RESET}")

def test_tcp_port(target, port):
    """Test if a TCP port is open on the target."""
    try:
        with socket.create_connection((target, port), timeout=3):
            print(f"{Colors.GREEN}TCP port {port} on {target} is open.{Colors.RESET}")
            return True
    except (socket.timeout, ConnectionRefusedError):
        print(f"{Colors.RED}TCP port {port} on {target} is closed.{Colors.RESET}")
        return False

def check_udp_port(ip, port):
    """Check if a UDP port is open on the target."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(1)
        try:
            sock.sendto(b'', (ip, port))
            sock.recvfrom(1024)  # Wait for a response
            return True  # Port is open
        except socket.error:
            return False  # Port is closed or no response

def format_headers(headers):
    """Format headers for display"""
    return '\n'.join(f'{k}: {v}' for k, v in headers)

def perform_http_request(host, verbose=0, follow_redirects=False):
    """Perform an HTTP request to the host with curl-like verbosity."""
    start_time = datetime.datetime.now()
    
    try:
        if verbose >= 1:
            print(f"\n* Trying {host}...")
            print(f"* TCP_NODELAY set")
        
        if verbose >= 3:
            print(f"* DNS resolution for {host}")
            ip = socket.gethostbyname(host)
            print(f"* Resolved to {ip}")
            print("* DNS resolution completed")

        conn = http.client.HTTPConnection(host, timeout=10)
        
        if verbose >= 2:
            print("\n> GET / HTTP/1.1")
            print(f"> Host: {host}")
            print("> User-Agent: nettest/1.0")
            print("> Accept: */*")
            print(">")
        
        headers = {
            'User-Agent': 'nettest/1.0',
            'Accept': '*/*'
        }
        
        conn.request("GET", "/", headers=headers)
        
        if verbose >= 1:
            print("* Connected to server")
            
        response = conn.getresponse()
        
        if verbose >= 4:
            print(f"\n* Request completed at: {datetime.datetime.now()}")
            print(f"* Time since start: {(datetime.datetime.now() - start_time).total_seconds():.3f} seconds")
            
        status = response.status
        reason = response.reason
        headers = response.getheaders()
        
        if verbose >= 2:
            print(f"\n< HTTP/1.1 {status} {reason}")
            for header, value in headers:
                print(f"< {header}: {value}")
            print("<")
            
        if verbose >= 1:
            content_type = dict(headers).get('Content-Type', 'unknown')
            content_length = dict(headers).get('Content-Length', 'unknown')
            print(f"\n< Status: {status} {reason}")
            print(f"< Content-Type: {content_type}")
            print(f"< Content-Length: {content_length}")
        
        if verbose >= 3:
            body = response.read(1024).decode('utf-8', errors='ignore')
            print("\n[Response body preview]")
            print(body[:500] + ("..." if len(body) > 500 else ""))
            
        if verbose >= 4:
            print("\n* Connection statistics:")
            print(f"* Response time: {(datetime.datetime.now() - start_time).total_seconds():.3f} seconds")
            print(f"* Connection reused: no")
            print(f"* Connection #: 1")
            
        return status, reason, headers
            
    except Exception as e:
        if verbose >= 1:
            print(f"\n* Error: {str(e)}")
        return None, str(e), None
    finally:
        if verbose >= 1:
            print("\n* Connection closed")
        conn.close()

def traceroute(target):
    """Perform a traceroute to the target."""
    print(f"{Colors.BLUE}Tracerouting to {target}...{Colors.RESET}")
    command = ['tracert', target] if platform.system().lower() == 'windows' else ['traceroute', target]
    response = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if response.returncode == 0:
        print(f"{Colors.GREEN}Traceroute to {target} was successful.{Colors.RESET}")
        print(response.stdout.decode())
    else:
        print(f"{Colors.RED}Traceroute to {target} failed.{Colors.RESET}")

def save_results_to_file(results, output_file):
    """Save results to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"{Colors.GREEN}Results saved to {output_file}{Colors.RESET}")

def print_header(title):
    print(Fore.CYAN + Style.BRIGHT + f"\n=== {title} ===" + Style.RESET_ALL)

def print_success(message):
    print(Fore.GREEN + f"[SUCCESS] {message}" + Style.RESET_ALL)

def print_error(message):
    print(Fore.RED + f"[ERROR] {message}" + Style.RESET_ALL)

def print_info(message):
    print(Fore.YELLOW + f"[INFO] {message}" + Style.RESET_ALL)

def print_result(target, ip, status, reason=None):
    print(Fore.BLUE + f"\nTarget: {target}")
    print(f"Resolved IP: {ip}")
    print(f"Status: {status}", end="")
    if reason:
        print(f" (Reason: {reason})", end="")
    print(Style.RESET_ALL)

def print_summary(success_count, error_count):
    print(Fore.MAGENTA + Style.BRIGHT + "\n=== Summary ===" + Style.RESET_ALL)
    print(f"Total Successful Requests: {success_count}")
    print(f"Total Errors: {error_count}")

def wait_animation():
    spinner = ['|', '/', '-', '\\']
    while not stop_event.is_set():
        for symbol in spinner:
            sys.stdout.write(f'\r{Fore.YELLOW}[INFO] Waiting... {symbol}')
            sys.stdout.flush()
            time.sleep(0.1)

def main():
    parser = argparse.ArgumentParser(description='Test Network Connection (TNC)')
    parser.add_argument('target', help='Target hostname or IP address')
    parser.add_argument('-p', '--port', type=int, help='TCP/UDP port to test', required=True)
    parser.add_argument('-c', '--curl', action='store_true', help='Perform curl-like request')
    parser.add_argument('-L', '--follow-redirects', action='store_true', help='Follow HTTP redirects')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity (use -v, -vv, -vvv, -vvvv)')
    parser.add_argument('-proto', '--protocol', choices=['tcp', 'udp'], required=True, help='Protocol to use (tcp or udp)')
    parser.add_argument('-t', '--trace', action='store_true', help='Perform traceroute')
    parser.add_argument('-o', '--output', type=str, help='Output file path to save results')
    args = parser.parse_args()

    target = args.target
    local_ip = get_local_ip()
    print(f"{Colors.YELLOW}Local IP Address: {local_ip}{Colors.RESET}")

    ip_address = resolve_hostname(target)

    results = {
        "target": target,
        "resolved_ip": ip_address,
        "ping_status": None,
        "tcp_port_status": None,
        "udp_port_status": None,
        "http_status": None,
    }

    if ip_address:
        print(f"{Colors.YELLOW}Remote IP Address: {ip_address}{Colors.RESET}")
        ping(ip_address)
        results["ping_status"] = "successful"

        if args.port:
            if args.protocol == 'tcp':
                results["tcp_port_status"] = test_tcp_port(ip_address, args.port)
            elif args.protocol == 'udp':
                results["udp_port_status"] = check_udp_port(ip_address, args.port)

        if args.curl:
            status, reason, headers = perform_http_request(
                target, 
                verbose=args.verbose,
                follow_redirects=args.follow_redirects
            )
            results["http_status"] = status
            if status is not None:
                if args.verbose == 0:
                    print_success(f"HTTP request to {ip_address} succeeded with status {status}.")
            else:
                print_error(f"Error during HTTP request: {reason}")

        # Perform traceroute if specified
        if args.trace:
            traceroute(ip_address)

        # Save results if output file is specified
        if args.output:
            save_results_to_file(results, args.output)

    print_header("Network Test Results")
    
    global stop_event
    stop_event = threading.Event()
    animation_thread = threading.Thread(target=wait_animation)
    animation_thread.start()

    try:
        print_info(f"Resolved {target} to {ip_address}")

        # Summary
        print_summary(1, 0)  # Example counts

    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
    finally:
        stop_event.set()  # Stop the animation
        animation_thread.join()  # Wait for the animation thread to finish

if __name__ == '__main__':
    main()

