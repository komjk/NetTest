# Network Connection Tester - Python Implementation

A Python implementation of PowerShell's `Test-NetConnection` cmdlet, with additional features like curl requests, colorized output, and file output in multiple formats.

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

## Notes

- On Windows, the script will attempt to enable ANSI colors, but they may not work in all terminal environments
- The `-v` option can be used multiple times for increased verbosity (e.g., `-vvv` for very verbose output)
- Output files are sanitized and validated for security
- The real curl command-line tool is NOT required - the script uses Python's requests library
- Real-time progress updates are provided during each step of the process 