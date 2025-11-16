#!/bin/bash

# ============================================================================
# Android eBPF Profiler - Setup Verification Script
# ============================================================================

set -e

echo "🔍 Android eBPF Profiler - Setup Verification"
echo "=============================================="
echo ""

ISSUES=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_command() {
    if command -v $1 &> /dev/null; then
        VERSION=$($1 --version 2>&1 | head -n 1)
        echo -e "${GREEN}✓${NC} $1 found: $VERSION"
        return 0
    else
        echo -e "${RED}✗${NC} $1 NOT found"
        ((ISSUES++))
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        SIZE=$(du -h "$1" | cut -f1)
        echo -e "${GREEN}✓${NC} $1 ($SIZE)"
        return 0
    else
        echo -e "${RED}✗${NC} $1 NOT found"
        ((ISSUES++))
        return 1
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        COUNT=$(ls -1 "$1" 2>/dev/null | wc -l)
        echo -e "${GREEN}✓${NC} $1 (contains $COUNT items)"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $1 does not exist"
        ((WARNINGS++))
        return 1
    fi
}

# ============================================================================
# System Dependencies
# ============================================================================

echo "📦 System Dependencies:"
echo "─────────────────────"
check_command python3 || true
check_command pip3 || true
check_command adb || echo -e "${YELLOW}⚠${NC} adb NOT found (install with: sudo apt-get install adb)"
check_command git || true
echo ""

# ============================================================================
# Python Environment
# ============================================================================

echo "🐍 Python Environment:"
echo "──────────────────────"

if command -v python3 &> /dev/null; then
    PYVER=$(python3 --version 2>&1)
    echo -e "${GREEN}✓${NC} $PYVER"
    
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python 3.7+ requirement met"
    else
        echo -e "${RED}✗${NC} Python 3.7+ is required"
        ((ISSUES++))
    fi
    
    # Check key modules
    for module in flask flask_cors json subprocess pathlib; do
        if python3 -c "import $module" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Module: $module"
        else
            echo -e "${YELLOW}⚠${NC} Module: $module (will be installed with requirements.txt)"
        fi
    done
else
    echo -e "${RED}✗${NC} Python 3 not found"
    ((ISSUES++))
fi

echo ""

# ============================================================================
# Project Files
# ============================================================================

echo "📁 Project Files:"
echo "────────────────"
check_file "requirements.txt"
check_file "backend/app.py"
check_file "backend/device_manager.py"
check_file "backend/bpftrace_orchestrator.py"
check_file "backend/trace_data_manager.py"
check_file "frontend/index.html"
check_file "frontend/app.js"
check_file "frontend/styles.css"
check_file "README.md"
check_file "start.sh"
check_file "analyze_trace.py"
echo ""

# ============================================================================
# BPFtrace Scripts
# ============================================================================

echo "🎯 BPFtrace Scripts:"
echo "───────────────────"
check_directory "bpftrace_scripts"
check_file "bpftrace_scripts/syscall_trace.bt"
check_file "bpftrace_scripts/file_access.bt"
check_file "bpftrace_scripts/memory_trace.bt"
echo ""

# ============================================================================
# ADB Device Check
# ============================================================================

echo "📱 Android Devices:"
echo "──────────────────"
if command -v adb &> /dev/null; then
    DEVICES=$(adb devices 2>/dev/null | tail -n +2 | grep -v "^$" | wc -l)
    if [ $DEVICES -gt 0 ]; then
        echo -e "${GREEN}✓${NC} $DEVICES device(s) detected"
        adb devices -l | tail -n +2 | grep -v "^$" | while read line; do
            echo "  - $line"
        done
    else
        echo -e "${YELLOW}⚠${NC} No devices connected"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} ADB not available - cannot check devices"
fi
echo ""

# ============================================================================
# Output Directory
# ============================================================================

echo "💾 Output Directory:"
echo "───────────────────"
check_directory "output" || mkdir -p output && echo -e "${GREEN}✓${NC} Created output directory"
echo ""

# ============================================================================
# Ports Check
# ============================================================================

echo "🔌 Port Availability:"
echo "────────────────────"

for port in 5000 8000; do
    if command -v netstat &> /dev/null; then
        if ! netstat -tuln 2>/dev/null | grep -q ":$port "; then
            echo -e "${GREEN}✓${NC} Port $port is available"
        else
            echo -e "${RED}✗${NC} Port $port is already in use"
            ((ISSUES++))
        fi
    elif command -v lsof &> /dev/null; then
        if ! lsof -i :$port &> /dev/null; then
            echo -e "${GREEN}✓${NC} Port $port is available"
        else
            echo -e "${RED}✗${NC} Port $port is already in use"
            ((ISSUES++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} Cannot check port $port (netstat/lsof not available)"
    fi
done
echo ""

# ============================================================================
# Summary
# ============================================================================

echo "═════════════════════════════════════════════════════════════"
if [ $ISSUES -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Setup verification PASSED${NC}"
    echo ""
    echo "You're ready to run: ./start.sh"
    exit 0
elif [ $ISSUES -eq 0 ]; then
    echo -e "${YELLOW}⚠ Setup verification completed with $WARNINGS warning(s)${NC}"
    echo ""
    echo "You can try running: ./start.sh"
    exit 0
else
    echo -e "${RED}✗ Setup verification FAILED with $ISSUES issue(s)${NC}"
    echo ""
    echo "Please fix the issues above before running ./start.sh"
    exit 1
fi
