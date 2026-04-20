import zmq
import json

class ZMQPublisher:
    def __init__(self, address="tcp://127.0.0.1:5557"):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(address)  # bind γιατί είναι ο publisher

    def publish(self, param_name, value):
        topic = b"control/"
        message = json.dumps({
            "param": param_name,
            "value": value
        }).encode("utf-8")
        self.socket.send_multipart([topic, message])

    def close(self):
        self.socket.close()