#!/bin/bash

# ============================================================================
# Android eBPF Profiler - Simple Startup Script
# ============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=========================================="
echo "🚀 Android eBPF Profiler"
echo "=========================================="
echo ""

# Setup virtual environment if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q -r "$PROJECT_DIR/requirements.txt"
echo "✅ Dependencies installed"

# Kill any existing processes on ports 5000 and 8000
echo ""
echo "🧹 Cleaning up old processes..."
pkill -f "python3.*app.py" 2>/dev/null || true
pkill -f "http.server" 2>/dev/null || true
sleep 1
echo "✅ Cleaned up"

# Create output directory
mkdir -p "$PROJECT_DIR/output"
echo "✅ Output directory ready"

# Start Backend
echo ""
echo "🔧 Starting Backend on http://localhost:5000"
cd "$BACKEND_DIR"
python3 app.py &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to start
sleep 3

# Start Frontend
echo ""
echo "🎨 Starting Frontend on http://localhost:8000"
cd "$FRONTEND_DIR"
python3 -m http.server 8000 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

# Test backend
echo ""
echo "🧪 Testing backend..."
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ Backend is responding"
else
    echo "⚠️  Backend test failed"
fi

echo ""
echo "=========================================="
echo "✅ System is ready!"
echo "=========================================="
echo ""
echo "📱 Frontend:  http://localhost:8000"
echo "🔧 Backend:   http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait
