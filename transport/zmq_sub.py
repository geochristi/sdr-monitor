import zmq
import json


class ZMQSubscriber:
    def __init__(self, address="tcp://127.0.0.1:5556"):#metrics port, don't subscribe to the 5555 because we don't actually want to get the packets.. only telemetry
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')  # Subscribe to all messages"")
        self.socket.RCVTIMEO = 1000  # 1 second timeout
        print(f"Subscriber connected to {address}")
        

    def receive(self):
        try:
            raw_message = self.socket.recv()
            # print("RAW:", raw_message)

            # find beginning of JSON object
            json_start = raw_message.find(b'{')
            if json_start == -1:
                print("No JSON object found in message.")
                return None
            json_bytes = raw_message[json_start:]
            
            # here it shows everything 
            print("RAW Decoded", self.deserialize(json_bytes))
            return self.deserialize(json_bytes)
        except zmq.Again:
            print("No message received within timeout period.")
            return None
        except Exception as e:
            print(f"Failed to receive message: {e}")
            return None
        
    def deserialize(self, raw_message: str) -> dict:
        try:
            return json.loads(raw_message.decode('utf-8'))
        except Exception as e:
            print(f"Failed to decode JSON message: {e}")
            return None
        
    # # if i want struct
    # def deserialize(self, raw_msg: bytes) -> dict:
    # import struct
    # snr, ber, rssi = struct.unpack("fff", raw_msg)
    # return {"snr": snr, "ber": ber, "rssi": rssi}