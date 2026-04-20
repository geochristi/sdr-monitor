"""
ZMQ Client for Controller Communication
Provides a simple client API for SNMP, Netconf, and PHY to interact with the ZMQ Controller daemon.
"""

import zmq
import json
import time
import logging

logger = logging.getLogger(__name__)

# Default controller addresses
DEFAULT_REQ_REP_ADDR = "tcp://127.0.0.1:5555"
DEFAULT_PUB_ADDR = "tcp://127.0.0.1:5556"
DEFAULT_PULL_ADDR = "tcp://127.0.0.1:5558"

# Message types
MSG_GET = "GET"
MSG_SET = "SET"
MSG_GET_ALL = "GET_ALL"
MSG_HELLO = "HELLO"


class ControllerClient:
    """ZMQ client for communicating with the controller daemon."""
    
    def __init__(self, req_rep_addr=DEFAULT_REQ_REP_ADDR, timeout=5000):
        """
        Initialize the controller client.
        
        Args:
            req_rep_addr: Address of the REQ/REP socket
            timeout: Timeout in milliseconds for REQ operations
        """
        self.context = zmq.Context()
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.setsockopt(zmq.RCVTIMEO, timeout)
        self.req_socket.setsockopt(zmq.LINGER, 0)
        self.req_socket.connect(req_rep_addr)
        self.req_rep_addr = req_rep_addr
    
    def get_param(self, param_name):
        """
        Get a single parameter value from the controller.
        
        Args:
            param_name: Name of the parameter (e.g., 'freq_offset', 'mod_scheme')
        
        Returns:
            The parameter value, or None if not found
        
        Raises:
            zmq.error.Again: If timeout occurs
            ValueError: If parameter doesn't exist
        """
        request = {"op": MSG_GET, "param": param_name}
        response = self._send_request(request)
        
        if response.get("status") == "ERROR":
            raise ValueError(response.get("error", f"Parameter not found: {param_name}"))
        
        return response.get("value")
    
    def get_all_params(self):
        """
        Get all parameters from the controller.
        
        Returns:
            Dictionary of {param_name: value}
        
        Raises:
            zmq.error.Again: If timeout occurs
        """
        request = {"op": MSG_GET_ALL}
        response = self._send_request(request)
        
        if response.get("status") == "ERROR":
            raise ValueError(response.get("error", "Failed to get all parameters"))
        
        return response.get("params", {})
    
    def set_param(self, param_name, value, source="zmq-client"):
        """
        Set a parameter value on the controller.
        
        Args:
            param_name: Name of the parameter
            value: Value to set
            source: Source identifier for logging (default: "zmq-client")
        
        Returns:
            The value that was set
        
        Raises:
            zmq.error.Again: If timeout occurs
            ValueError: If parameter doesn't exist or value is invalid
        """
        request = {"op": MSG_SET, "param": param_name, "value": value, "source": source}
        response = self._send_request(request)
        
        if response.get("status") == "ERROR":
            raise ValueError(response.get("error", f"Failed to set {param_name}"))
        
        return response.get("value")
    
    def _send_request(self, request):
        """
        Send a request and receive a response.
        
        Args:
            request: Dictionary to encode as JSON
        
        Returns:
            Decoded response dictionary
        
        Raises:
            zmq.error.Again: If response timeout occurs
        """
        try:
            # Send request
            self.req_socket.send(json.dumps(request).encode('utf-8'))
            
            # Receive response (blocking, with timeout)
            response_bytes = self.req_socket.recv()
            return json.loads(response_bytes.decode('utf-8'))
        
        except zmq.error.Again:
            logger.error(f"Controller timeout for request: {request}")
            raise
    
    def close(self):
        """Close the ZMQ socket and context."""
        self.req_socket.close()
        self.context.term()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MetricsPublisher:
    """ZMQ client for publishing metrics from PHY to controller."""
    
    def __init__(self, pull_addr=DEFAULT_PULL_ADDR):
        """
        Initialize the metrics publisher.
        
        Args:
            pull_addr: Address of the PULL socket on controller
        """
        self.context = zmq.Context()
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.setsockopt(zmq.LINGER, 0)
        self.push_socket.connect(pull_addr)
    
    def publish_metrics(self, metrics_dict):
        """
        Publish metrics to the controller.
        
        Args:
            metrics_dict: Dictionary of metrics to publish
        """
        try:
            message = json.dumps(metrics_dict)
            self.push_socket.send(message.encode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to publish metrics: {e}")
    
    def close(self):
        """Close the ZMQ socket and context."""
        self.push_socket.close()
        self.context.term()


class ParamSubscriber:
    """ZMQ client for subscribing to parameter updates from controller."""
    
    def __init__(
        self,
        pub_addr=DEFAULT_PUB_ADDR,
        topics=None,
        req_rep_addr=DEFAULT_REQ_REP_ADDR,
        hello_on_connect=True,
        hello_timeout=2000,
    ):
        """
        Initialize the parameter subscriber.
        
        Args:
            pub_addr: Address of the PUB socket on controller
            topics: List of topics to subscribe to (e.g., ['param/frequency', 'param/noise'])
                   If None, subscribe to all updates
            req_rep_addr: Address of controller REQ/REP socket for HELLO snapshot
            hello_on_connect: If True, send HELLO and store returned snapshot
            hello_timeout: Timeout in milliseconds for HELLO response
        """
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.LINGER, 0)
        self.sub_socket.connect(pub_addr)

        # Dedicated REQ socket for HELLO handshake snapshot.
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.setsockopt(zmq.LINGER, 0)
        self.req_socket.setsockopt(zmq.RCVTIMEO, hello_timeout)
        self.req_socket.connect(req_rep_addr)

        self.initial_snapshot = None
        
        # Subscribe to topics
        if topics is None:
            # Subscribe to all param updates
            self.sub_socket.subscribe(b"param/")
        else:
            for topic in topics:
                self.sub_socket.subscribe(topic.encode('utf-8'))
        
        # Small delay to allow subscription to establish
        time.sleep(0.1)

        if hello_on_connect:
            self.initial_snapshot = self.request_snapshot()

    def request_snapshot(self):
        """Send HELLO handshake and return full configuration snapshot dict."""
        try:
            request = {"op": MSG_HELLO, "role": "subscriber"}
            self.req_socket.send(json.dumps(request).encode('utf-8'))
            response_bytes = self.req_socket.recv()
            response = json.loads(response_bytes.decode('utf-8'))

            if response.get("status") == "ERROR":
                err = response.get("error", "")
                # Backward compatibility: older controller versions do not support HELLO.
                if "Unknown operation" in str(err) and "HELLO" in str(err):
                    fallback = {"op": MSG_GET_ALL}
                    self.req_socket.send(json.dumps(fallback).encode('utf-8'))
                    fallback_bytes = self.req_socket.recv()
                    fallback_resp = json.loads(fallback_bytes.decode('utf-8'))
                    if fallback_resp.get("status") == "OK":
                        logger.info("HELLO unsupported; using GET_ALL snapshot fallback")
                        return fallback_resp.get("params", {})
                logger.error("HELLO handshake error: %s", err)
                return {}

            return response.get("params", {})
        except zmq.error.Again:
            logger.error("HELLO handshake timed out")
            return {}
        except Exception as e:
            logger.error(f"HELLO handshake failed: {e}")
            return {}
    
    def recv_update(self, timeout_ms=None):
        """
        Receive a parameter update.
        
        Args:
            timeout_ms: Timeout in milliseconds (None = blocking)
        
        Returns:
            Tuple of (topic, param_name, value, timestamp, internal_param) or None if timeout
        """
        try:
            if timeout_ms is not None:
                self.sub_socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
            
            topic, message = self.sub_socket.recv_multipart()
            data = json.loads(message.decode('utf-8'))
            
            param_name = data.get("param")
            internal_param = data.get("internal_param", param_name)
            value = data.get("value")
            timestamp = data.get("timestamp")
            
            return (topic.decode('utf-8'), param_name, value, timestamp, internal_param)
        
        except zmq.error.Again:
            return None
        except Exception as e:
            logger.error(f"Error receiving update: {e}")
            return None
    
    def close(self):
        """Close the ZMQ socket and context."""
        self.req_socket.close()
        self.sub_socket.close()
        self.context.term()


# Convenience function for one-off operations
def quick_get(param_name, timeout_ms=5000):
    """Quick one-off parameter get."""
    with ControllerClient(timeout=timeout_ms) as client:
        return client.get_param(param_name)


def quick_set(param_name, value, timeout_ms=5000):
    """Quick one-off parameter set."""
    with ControllerClient(timeout=timeout_ms) as client:
        return client.set_param(param_name, value)


def quick_get_all(timeout_ms=5000):
    """Quick one-off get all parameters."""
    with ControllerClient(timeout=timeout_ms) as client:
        return client.get_all_params()
