#!/usr/bin/env python3
"""
Test script demonstrating all three ZMQ patterns working together:
  - REQ/REP for synchronous config requests
  - PUB/SUB for parameter update broadcasts
  - PUSH/PULL for metrics ingestion

Run the controller first:
  python3 zmq_controller.py

Then run this test:
  python3 test_zmq_patterns.py
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from zmq_client import ControllerClient, ParamSubscriber, MetricsPublisher


def test_req_rep():
    """Test REQ/REP pattern (synchronous config)."""
    print("\n" + "="*60)
    print("TEST 1: REQ/REP Pattern (Synchronous Config)")
    print("="*60)
    
    with ControllerClient() as client:
        # Get current values
        print("\n1. Getting all parameters...")
        params = client.get_all_params()
        for k, v in params.items():
            print(f"   {k} = {v}")
        
        # Get single param
        print("\n2. Getting freq_offset...")
        freq = client.get_param("freq_offset")
        print(f"   freq_offset = {freq}")
        
        # Set a param
        print("\n3. Setting freq_offset to 5000...")
        freq = client.set_param("freq_offset", 5000, source="test-req-rep")
        print(f"   Set successfully to {freq}")
        
        # Verify
        print("\n4. Verifying freq_offset...")
        freq = client.get_param("freq_offset")
        print(f"   freq_offset = {freq}")


def test_pub_sub():
    """Test PUB/SUB pattern (parameter broadcasts)."""
    print("\n" + "="*60)
    print("TEST 2: PUB/SUB Pattern (Parameter Broadcasts)")
    print("="*60)
    
    # Subscribe to all parameter updates
    print("\n1. Subscribing to all parameter updates...")
    sub = ParamSubscriber(topics=None)  # Subscribe to all updates
    
    # Publisher thread (simulates another client making changes)
    def publish_changes():
        time.sleep(0.5)  # Give subscriber time to connect
        print("\n2. Publisher sending changes (from another thread)...")
        with ControllerClient() as client:
            changes = [
                ("mod_scheme", 2),
                ("rate", 500),
                ("snr", 20.5),
            ]
            for param, value in changes:
                print(f"   Setting {param} = {value}")
                client.set_param(param, value, source="test-pub-sub")
                time.sleep(0.2)
    
    # Start publisher thread
    pub_thread = threading.Thread(target=publish_changes, daemon=False)
    pub_thread.start()
    
    # Receive updates
    print("\n3. Receiving broadcasted updates...")
    received = 0
    for i in range(5):
        update = sub.recv_update(timeout_ms=2000)
        if update:
            topic, param, value, ts = update
            print(f"   [UPDATE] {param} = {value} (ts={ts:.2f})")
            received += 1
        else:
            print(f"   [TIMEOUT] No update received")
    
    pub_thread.join()
    sub.close()
    print(f"\n4. Received {received} updates")


def test_push_pull():
    """Test PUSH/PULL pattern (metrics ingestion)."""
    print("\n" + "="*60)
    print("TEST 3: PUSH/PULL Pattern (Metrics Ingestion)")
    print("="*60)
    
    print("\n1. Starting metrics publisher (PHY simulator)...")
    pub = MetricsPublisher()
    
    # Publish some sample metrics
    print("\n2. Publishing 3 metric batches...")
    for i in range(3):
        metrics = {
            "sequence": i,
            "bits": 1000 + (i * 100),
            "errors": 5 + i,
            "timestamp": time.time(),
        }
        print(f"   Publishing: {metrics}")
        pub.publish_metrics(metrics)
        time.sleep(0.1)
    
    pub.close()
    print("\n3. Metrics published (check controller output to see if received)")


def main():
    """Run all tests."""
    print("\n" + "█"*60)
    print("█  ZMQ Controller - Three Pattern Demo")
    print("█"*60)
    print("\nThis test demonstrates the three ZMQ patterns:")
    print("  1. REQ/REP:  Synchronous config get/set")
    print("  2. PUB/SUB:  Broadcasting parameter updates")
    print("  3. PUSH/PULL: Ingesting metrics from PHY")
    
    try:
        # Test 1: REQ/REP
        test_req_rep()
        
        # Test 2: PUB/SUB
        test_pub_sub()
        
        # Test 3: PUSH/PULL
        test_push_pull()
        
        print("\n" + "█"*60)
        print("█  All Tests Completed Successfully!")
        print("█"*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("Make sure the controller daemon is running:")
        print("  python3 zmq_controller.py")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
