#!/bin/bash

# ============================================================================
# Android eBPF Profiler - Startup Script
# ============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "🚀 Android eBPF Profiler Startup Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

echo "✅ pip3 found: $(pip3 --version)"

# Check if ADB is installed
if ! command -v adb &> /dev/null; then
    echo "⚠️  ADB is not installed or not in PATH."
    echo "   You can install it via: sudo apt-get install adb (Linux)"
    echo "   or download from Android SDK Platform Tools"
    echo ""
fi

# Create output directory
mkdir -p "$PROJECT_DIR/output"
echo "✅ Output directory ready: $PROJECT_DIR/output"

# Create and activate virtual environment
echo ""
echo "📦 Setting up Python virtual environment..."
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
fi

source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -q -r "$PROJECT_DIR/requirements.txt"
echo "✅ Dependencies installed"

# Start backend
echo ""
echo "🔧 Starting Backend (Flask API on http://localhost:5000)..."
echo "   Press Ctrl+C to stop"
cd "$BACKEND_DIR"
python3 app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo ""
echo "🎨 Starting Frontend (Open http://localhost:8000 in your browser)..."
echo "   Press Ctrl+C to stop"
cd "$FRONTEND_DIR"

# Check if Python's http.server can be used
if command -v python3 &> /dev/null; then
    python3 -m http.server 8000 --bind localhost
else
    echo "❌ Could not start HTTP server"
    kill $BACKEND_PID
    exit 1
fi

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
