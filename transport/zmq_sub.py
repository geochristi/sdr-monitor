import zmq
import json


class ZMQSubscriber:
    def __init__(self, address="tcp://127.0.0.1:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        print(f"Subscriber connected to {address}")

    def receive(self):
        message = self.socket.recv_string()
        return json.loads(message)