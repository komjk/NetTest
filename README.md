# Test Network Connection (TNC) - Python Implementation

A Python implementation of PowerShell's `Test-NetConnection` cmdlet, with additional features like curl requests, colorized output, and file output in multiple formats.

## Features

- Hostname to IP resolution
- ICMP ping testing
- TCP port connection testing
- Traceroute capability
- HTTP/HTTPS requests (curl-like functionality with authentic output)
- Accurate curl emulation with different verbosity levels (matching real curl output)
- Real-time progress updates for all operations
- Colored output for better readability (with fallback for terminals without color support)
- Save results to file in JSON, CSV, XML, or text formats
- Configurable timeouts for network operations

## Requirements

- Python 3.6+
- Requests library (`pip install requests`)

## Usage

```
python tnc.py [-h] [-p PORT] [--no-ping] [-t] [-c] [-L] [-v] [-nc] [-o OUTPUT]
              [--timeout TIMEOUT] [-f {json,csv,xml,txt}] target
```

### Arguments

- `target`: Target hostname or IP address (required)
- `-p`, `--port`: TCP port to test
- `--no-ping`: Skip ping test
- `-t`, `--trace`: Perform traceroute
- `-c`, `--curl`: Perform curl-like request
- `-L`, `--follow-redirects`: Follow redirects (implied with curl)
- `-v`, `--verbose`: Increase verbosity (can be used multiple times)
- `-nc`: Disable colored output
- `-o`, `--output`: Output file path to save results
- `--timeout`: Timeout in seconds for network operations (default: 3)
- `-f`, `--format`: Output format (json, csv, xml, txt) (default: txt)

### Examples

Basic connection test:
```
python tnc.py google.com
```

Test connection to a specific port:
```
python tnc.py google.com -p 443
```

Perform a basic curl-like request:
```
python tnc.py google.com -c
```

Curl with increased verbosity (like curl -v):
```
python tnc.py google.com -c -v
```

Curl with very high verbosity (like curl -vvv):
```
python tnc.py google.com -c -vvv
```

Follow redirects (like curl -L):
```
python tnc.py google.com -c -L
```

Use a longer timeout for slow connections:
```
python tnc.py slow-server.example.com -c --timeout 10
```

Trace route to the target:
```
python tnc.py google.com -t
```

Save results to a JSON file:
```
python tnc.py google.com -p 443 -o results.json -f json
```

Save results to a text file:
```
python tnc.py google.com -c -t -o network_test.txt
```

## Curl Verbosity Levels

The script emulates the real curl command's verbosity levels:

- No `-v`: Basic output showing only status code, content type and length
- `-v`: Shows connection details, request/response status, and a snippet of the response body
- `-vv`: Adds request/response headers and more connection details
- `-vvv`: Adds SSL/TLS details (for HTTPS), DNS resolution info, and more response body content
- `-vvvv`: Maximum verbosity with timing information and debugging details

## Notes

- On Windows, the script will attempt to enable ANSI colors, but they may not work in all terminal environments
- The `-v` option can be used multiple times for increased verbosity (e.g., `-vvv` for very verbose output)
- Output files are sanitized and validated for security
- The real curl command-line tool is NOT required - the script uses Python's requests library
- Real-time progress updates are provided during each step of the process 