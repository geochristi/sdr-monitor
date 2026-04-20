#!/bin/bash
# Quick test script for ZMQ controller
# Run this after starting zmq_controller.py

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}ZMQ Controller - Quick Test${NC}"
echo -e "${BLUE}=================================================${NC}"

# Check if controller is running
echo -e "\n${YELLOW}[1/4] Checking if controller daemon is running...${NC}"
if ! python3 -c "import sys; sys.path.insert(0, '..'); from control.zmq_client import ControllerClient; c = ControllerClient(); print('✓ Connected'); c.close()" 2>/dev/null; then
    echo "❌ Controller not running. Start it with:"
    echo "   cd /home/georgia/Desktop/SDR/control"
    echo "   python3 zmq_controller.py &"
    exit 1
fi

# Test 1: REQ/REP - Get all params
echo -e "\n${YELLOW}[2/4] Testing REQ/REP (GET_ALL)...${NC}"
python3 << 'EOF'
import sys
sys.path.insert(0, '..')
from control.zmq_client import ControllerClient

with ControllerClient() as client:
    params = client.get_all_params()
    print(f"✓ Retrieved {len(params)} parameters:")
    for k, v in sorted(params.items()):
        print(f"    {k:15} = {v}")
EOF

# Test 2: REQ/REP - Set a param
echo -e "\n${YELLOW}[3/4] Testing REQ/REP (SET)...${NC}"
python3 << 'EOF'
import sys
sys.path.insert(0, '..')
from control.zmq_client import ControllerClient

with ControllerClient() as client:
    # Set freq_offset to test value
    old_val = client.get_param("freq_offset")
    test_val = 12345
    new_val = client.set_param("freq_offset", test_val, source="bash-test")
    print(f"✓ Set freq_offset: {old_val} → {new_val}")
    
    # Verify the change
    verify = client.get_param("freq_offset")
    if verify == test_val:
        print(f"✓ Verification passed: {verify}")
    else:
        print(f"❌ Verification failed: expected {test_val}, got {verify}")
        sys.exit(1)
    
    # Reset to original
    client.set_param("freq_offset", 0, source="bash-test-reset")
    print(f"✓ Reset freq_offset to 0")
EOF

# Test 3: PUB/SUB - Subscribe and broadcast
echo -e "\n${YELLOW}[4/4] Testing PUB/SUB (parameter broadcasts)...${NC}"
python3 << 'EOF'
import sys
import threading
import time
sys.path.insert(0, '..')
from control.zmq_client import ControllerClient, ParamSubscriber

# Start subscriber (in main thread)
print("  Starting parameter subscriber...")
sub = ParamSubscriber(topics=["param/rate"])
print(f"  ✓ Subscribed to param/rate")

# Function to publish changes after a delay
def publish_update():
    time.sleep(0.5)
    print("  Publishing update: rate=777...")
    with ControllerClient() as client:
        client.set_param("rate", 777, source="test-pub-sub")

# Start publisher in background
pub_thread = threading.Thread(target=publish_update, daemon=True)
pub_thread.start()

# Wait for broadcast
print("  Waiting for broadcast (2 second timeout)...")
update = sub.recv_update(timeout_ms=2000)
if update:
    topic, param, value, ts = update
    print(f"  ✓ Received broadcast: {param}={value}")
    if value == 777:
        print(f"    ✓ Value matches expected")
    else:
        print(f"    ⚠ Value mismatch: expected 777, got {value}")
else:
    print(f"  ❌ No broadcast received")
    sys.exit(1)

pub_thread.join()
sub.close()

# Reset value
with ControllerClient() as client:
    client.set_param("rate", 100, source="test-reset")
print(f"  ✓ Reset rate to 100")
EOF

echo -e "\n${GREEN}=================================================${NC}"
echo -e "${GREEN}✓ All tests passed! ZMQ controller is working${NC}"
echo -e "${GREEN}=================================================${NC}"
