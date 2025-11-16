# ???? Android eBPF Profiler

Complete automation system for kernel tracing and performance profiling on Android devices using eBPF and BPFtrace.

## ??? Quick Start

```bash
bash verify_setup.sh  # Check prerequisites
bash start.sh         # Start backend + frontend
# Open http://localhost:8000
```

## ???? Features

- **Automated Device Management**: ADB detection, capability checking
- **Real-time Tracing**: Monitor syscalls, file I/O, memory operations
- **Web UI**: One-click trace execution and result viewing
- **REST API**: 15+ endpoints for integration
- **Data Analysis**: Parse NDJSON, aggregate events, export statistics
- **Subprocess Automation**: Complete JSON output handling
- **Docker Support**: Containerized deployment

## ???? Requirements

- Python 3.7+
- ADB (Android Debug Bridge)
- Android device with USB debugging enabled
- Linux 4.4+ kernel (for eBPF support)

## ??????? Project Structure

```
backend/          - Flask REST API & core logic
frontend/         - Web UI (HTML5, CSS3, Vanilla JS)
bpftrace_scripts/ - eBPF tracing scripts
tests/            - Jest unit & integration tests
```

## ???? Installation

```bash
pip3 install -r requirements.txt
npm install
```

## ???? API Endpoints

```
Device Management:
  GET  /api/health              Health check
  GET  /api/devices             List devices
  GET  /api/devices/<id>/info   Device info

Tracing:
  POST /api/traces/syscall      Start syscall trace
  POST /api/traces/file-access  Start file access trace
  POST /api/traces/memory       Start memory trace
  POST /api/traces/custom       Run custom script
  GET  /api/traces/<id>/summary Get trace summary
  GET  /api/traces/<id>/download Download results
```

## ???? Testing

```bash
npm test                    # Run all tests
npm test -- --coverage      # With coverage report
npm test -- --watch         # Watch mode
```

## ???? Usage

### Terminal 1 - Backend
```bash
cd backend
python3 app.py
```

### Terminal 2 - Frontend
```bash
cd frontend
python3 -m http.server 8000
```

### Open Browser
```
http://localhost:8000
```

### Connect Device & Start Tracing
1. adb devices (verify connection)
2. Click "Refresh" in UI
3. Select device
4. Choose trace type
5. Click "Start Trace"
6. Download results when complete

## ???? Troubleshooting

**Device not detected?**
```bash
adb kill-server
adb start-server
adb devices
```

**Backend error?**
```bash
python3 --version
pip3 install -r requirements.txt
```

**Frontend not loading?**
```
Hard refresh: Ctrl+Shift+R
Check console: F12
Verify backend: curl http://localhost:5000/api/health
```

**Tests failing?**
```bash
npm install
npm test
```

## ??????? Commands

```bash
# Startup & Verification
bash verify_setup.sh      Check prerequisites
bash start.sh             Start everything
npm test                  Run tests

# Device Management
adb devices               List devices
adb shell id              Check root

# Offline Analysis
python3 analyze_trace.py output/trace_*.json --summary
python3 analyze_trace.py output/trace_*.json --export-csv

# Docker
docker-compose up         Start in containers
```

## ???? Manual Testing

```bash
# Health check
curl http://localhost:5000/api/health

# List devices
curl http://localhost:5000/api/devices

# Start trace (example)
curl -X POST http://localhost:5000/api/traces/syscall \
  -H "Content-Type: application/json" \
  -d '{"device_id": "SERIAL", "duration": 30}'
```

## ???? Data Flow

```
Browser UI
    ???
Frontend (Vanilla JS)
    ???
Flask Backend
  ?????? Device Manager (ADB)
  ?????? BPFtrace Orchestrator
  ?????? Data Parser
    ???
Android Device (ADB)
    ???
Kernel (eBPF)
```

## ???? Tech Stack

- **Backend**: Python 3, Flask, subprocess
- **Frontend**: HTML5, CSS3, JavaScript
- **Testing**: Jest, Supertest
- **Tracing**: eBPF, BPFtrace
- **Device**: ADB, Android Debug Bridge
- **Deployment**: Docker, Docker Compose

## ???? Security

- Requires ADB debugging on device
- Operations need root/elevated privileges
- Trace data contains process information
- No auth layer (add for production)

## ???? Performance

| Operation | Time | Memory |
|-----------|------|--------|
| Device detection | ~1s | ~10MB |
| 30s trace | ~35s | ~50-200MB |
| Parse 10k events | ~100ms | ~20MB |

## ???? Output

Trace results saved in `./output/` directory:
```
trace_<name>_<device>_<timestamp>.json
```

## ???? Next Steps

1. Run `bash verify_setup.sh`
2. Run `bash start.sh`
3. Open http://localhost:8000
4. Connect device via ADB
5. Start tracing!

## ???? Support

- Backend logs: Terminal output
- Frontend: Browser F12 console
- Diagnostics: `bash verify_setup.sh`
- API testing: `curl` commands above

---

**Happy Profiling! ????**
