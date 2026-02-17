import zmq
import json
import time
import random


# This is a mock publisher that simulates the behavior of a real PHY metrics publisher.
# it will disappear when real GNU Radio is connected

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://127.0.0.1:5555")

print("Mock publisher started on tcp://127.0.0.1:5555")

while True:
    data = {
        "rssi": random.uniform(-60, -30),
        "snr": random.uniform(2, 20),
        "ber": random.uniform(0, 0.02),
        # "rssi": -55,
        # "snr": 3,   # Force low SNR 
        # "ber": 0.02 # Force high BER
    }

    socket.send_string(json.dumps(data))
    print(f"Published: {data}")
    time.sleep(1)