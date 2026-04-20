#!/bin/bash
# Build script for ZMQ-enabled sysrepo_sdr_controller
# Requires: libsysrepo-dev, libzmq3-dev, libcjson-dev

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="${SCRIPT_DIR}/build"
SRC_FILE="${SCRIPT_DIR}/sysrepo_sdr_controller.c"
OUT_FILE="${SCRIPT_DIR}/sdr_controller"

echo "================================"
echo "Building ZMQ Netconf Controller"
echo "================================"

# Create build directory
mkdir -p "$BUILD_DIR"

echo "[1/3] Checking dependencies..."
if ! pkg-config --exists sysrepo; then
    echo "❌ libsysrepo-dev not installed"
    echo "   Install with: sudo apt-get install libsysrepo-dev"
    exit 1
fi

if ! pkg-config --exists libzmq; then
    echo "❌ libzmq3-dev not installed"
    echo "   Install with: sudo apt-get install libzmq3-dev"
    exit 1
fi

if ! pkg-config --exists libcjson; then
    echo "❌ libcjson-dev not installed"
    echo "   Install with: sudo apt-get install libcjson-dev"
    exit 1
fi

echo "✓ All dependencies found"

echo "[2/3] Compiling..."

# Get compiler flags
CFLAGS=$(pkg-config --cflags sysrepo libzmq libcjson)
LDFLAGS=$(pkg-config --libs sysrepo libzmq libcjson)

# Compile
gcc -o "$OUT_FILE" "$SRC_FILE" $CFLAGS $LDFLAGS -Wall -g

echo "✓ Compilation successful: $OUT_FILE"

echo "[3/3] Verifying..."
ldd "$OUT_FILE" | grep -E "zmq|cjson|sysrepo" && echo "✓ All dependencies linked"

echo ""
echo "================================"
echo "✓ Build Complete!"
echo "================================"
echo ""
echo "To run the controller:"
echo "  sudo $OUT_FILE"
echo ""
echo "Make sure the ZMQ controller daemon is running first:"
echo "  python3 control/zmq_controller.py &"
echo ""
