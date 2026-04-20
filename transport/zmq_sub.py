import zmq
import json
import sys

class ZMQSubscriber:
    def __init__(self, address="tcp://127.0.0.1:5556", topic_prefix="metrics/"):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.setsockopt(zmq.SUBSCRIBE, topic_prefix.encode("utf-8"))
        self.socket.RCVTIMEO = 1000  # 1 second timeout
        self.topic_prefix = topic_prefix

    def receive(self, timeout=None):
        original_timeout = self.socket.RCVTIMEO
        if timeout is not None:
            self.socket.RCVTIMEO = int(timeout)

        try:
            topic, raw_message = self.socket.recv_multipart()
            decoded = self.deserialize(raw_message)
            if decoded is None:
                return None

            if isinstance(decoded, dict) and "metrics" in decoded:
                return decoded["metrics"]

            return decoded
        except zmq.Again:
            return None
        except Exception:
            return None
        finally:
            if timeout is not None:
                self.socket.RCVTIMEO = original_timeout
        
    def deserialize(self, raw_message: str) -> dict:
        try:
            return json.loads(raw_message.decode('utf-8'))
        except Exception as e:
            return None


class ControlUpdateSubscriber:
    def __init__(self, address="tcp://127.0.0.1:5557", topic_prefix="control/"):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.setsockopt(zmq.SUBSCRIBE, topic_prefix.encode("utf-8"))
        self.socket.RCVTIMEO = 1000

    def receive(self, timeout=None):
        original_timeout = self.socket.RCVTIMEO
        if timeout is not None:
            self.socket.RCVTIMEO = int(timeout)

        try:
            topic, raw_message = self.socket.recv_multipart()
            decoded = json.loads(raw_message.decode("utf-8"))
            if not isinstance(decoded, dict):
                return None
            return {
                "topic": topic.decode("utf-8"),
                "param": decoded.get("param"),
                "value": decoded.get("value"),
            }
        except zmq.Again:
            return None
        except Exception:
            return None
        finally:
            if timeout is not None:
                self.socket.RCVTIMEO = original_timeout

    def close(self):
        self.socket.close()