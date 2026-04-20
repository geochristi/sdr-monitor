#!/usr/bin/env python3
"""
ZMQ-based Controller Daemon
Manages PHY configuration state and metrics via three ZMQ patterns:
  - REQ/REP: Synchronous config get/set from SNMP, Netconf, etc.
  - PUB/SUB: Broadcast parameter updates to PHY when config changes
  - PUSH/PULL: Ingest metrics/telemetry from PHY
"""

import zmq
import json
import threading
import time
import logging
import sys
from pathlib import Path

try:
    import pmt
except ImportError:
    pmt = None

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

try:
    from .controller import Controller
except ImportError:
    from controller import Controller
from transport.zmq_pub import ZMQPublisher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ZMQ Socket Addresses
REQ_REP_ADDR = "tcp://127.0.0.1:5555"      # Config requests (synchronous)
PUB_ADDR = "tcp://127.0.0.1:5556"           # Parameter updates (broadcast)
CONTROL_PUB_ADDR = "tcp://127.0.0.1:5557"   # GNU Radio control updates
PULL_ADDR = "tcp://127.0.0.1:5558"          # Metrics ingestion

# Message protocol constants
MSG_GET = "GET"
MSG_SET = "SET"
MSG_SET_CONFIG = "SET_CONFIG"
MSG_GET_ALL = "GET_ALL"
MSG_HELLO = "HELLO"
MSG_OK = "OK"
MSG_ERROR = "ERROR"

# Public topic names used on PUB/SUB (external interface)
TOPIC_PARAM_MAP = {
    "noise": "noise",
    "snr": "snr",
    "rate": "rate",
    "freq_offset": "frequency",
    "mod_scheme": "modulation",
    "ber_inject": "ber",
}

METRICS_TOPIC = "metrics/phy"


class ZMQController:
    def __init__(self):
        # Keep the legacy control file synchronized so existing GNU Radio
        # blocks that still poll from disk continue to react to SNMP/NETCONF.
        self.state = Controller(persist=True)
        self.context = zmq.Context()
        
        # REQ/REP socket (config requests)
        self.req_rep_socket = self.context.socket(zmq.REP)
        self.req_rep_socket.bind(REQ_REP_ADDR)
        logger.info(f"REQ/REP listening on {REQ_REP_ADDR}")
        
        # PUB socket (parameter broadcasts)
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(PUB_ADDR)
        logger.info(f"PUB listening on {PUB_ADDR}")

        self.control_publisher = ZMQPublisher(CONTROL_PUB_ADDR)
        logger.info(f"Control PUB listening on {CONTROL_PUB_ADDR}")
        
        # PULL socket (metrics ingestion)
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(PULL_ADDR)
        logger.info(f"PULL listening on {PULL_ADDR}")
        
        # Initialize in-memory state with defaults.
        self.state.ensure_control_file()
        
        # Threads for socket handling
        self.running = True
        self.threads = []
        
    def start(self):
        """Start all ZMQ handler threads."""
        logger.info("Starting ZMQ controller daemon...")
        
        req_rep_thread = threading.Thread(target=self._handle_req_rep, daemon=True)
        pull_thread = threading.Thread(target=self._handle_pull, daemon=True)
        
        self.threads.extend([req_rep_thread, pull_thread])
        
        for thread in self.threads:
            thread.start()
        
        logger.info("All handler threads started")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
            self.stop()
    
    def stop(self):
        """Gracefully shutdown all sockets and threads."""
        logger.info("Shutting down ZMQ controller...")
        self.running = False
        
        # Close sockets
        self.req_rep_socket.close()
        self.pub_socket.close()
        self.control_publisher.close()
        self.pull_socket.close()
        self.context.term()
        
        logger.info("ZMQ context terminated")
    
    def _handle_req_rep(self):
        """Handle synchronous REQ/REP configuration requests."""
        while self.running:
            try:
                # Receive request
                request_bytes = self.req_rep_socket.recv()
                request = json.loads(request_bytes.decode('utf-8'))
                
                response = self._process_config_request(request)
                
                # Send response
                self.req_rep_socket.send(json.dumps(response).encode('utf-8'))
                
            except zmq.error.ContextTerminated:
                break
            except Exception as e:
                logger.error(f"REQ/REP handler error: {e}")
                try:
                    self.req_rep_socket.send(json.dumps({
                        "status": MSG_ERROR,
                        "error": str(e)
                    }).encode('utf-8'))
                except:
                    pass
    
    def _process_config_request(self, request):
        """Process a configuration request (GET, SET, GET_ALL)."""
        op = request.get("op")
        
        if op == MSG_GET:
            param = request.get("param")
            value = self.state.get_param(param, refresh=False)
            if value is None:
                return {"status": MSG_ERROR, "error": f"Unknown parameter: {param}"}
            return {"status": MSG_OK, "param": param, "value": value}
        
        elif op == MSG_SET:
            param = request.get("param")
            value = request.get("value")
            source = request.get("source", "zmq-client")
            try:
                self.state.set_param(param, value, source=source)
                # Broadcast the change via PUB
                self._broadcast_update(param, value, source)
                return {"status": MSG_OK, "param": param, "value": value}
            except ValueError as e:
                return {"status": MSG_ERROR, "error": str(e)}
        
        elif op == MSG_SET_CONFIG:
            config = request.get("config", {})
            source = request.get("source", "zmq-client")
            if not isinstance(config, dict) or not config:
                return {"status": MSG_ERROR, "error": "config must be a non-empty object"}
            applied = {}
            errors = {}
            for param, value in config.items():
                try:
                    self.state.set_param(param, value, source=source)
                    self._broadcast_update(param, value, source)
                    applied[param] = value
                except ValueError as e:
                    errors[param] = str(e)
            if errors:
                return {"status": MSG_ERROR, "applied": applied, "errors": errors}
            return {"status": MSG_OK, "applied": applied}

        elif op == MSG_GET_ALL:
            params = self.state.get_all_params(refresh=False)
            return {"status": MSG_OK, "params": params}

        elif op == MSG_HELLO:
            # Subscriber handshake: return current full configuration snapshot.
            params = self.state.get_all_params(refresh=False)
            return {
                "status": MSG_OK,
                "op": MSG_HELLO,
                "params": params,
                "timestamp": time.time()
            }
        
        else:
            return {"status": MSG_ERROR, "error": f"Unknown operation: {op}"}
    
    def _broadcast_update(self, param, value, source):
        """Publish parameter update via PUB socket."""
        topic_param = TOPIC_PARAM_MAP.get(param, param)
        message = json.dumps({
            "param": topic_param,
            "internal_param": param,
            "value": value,
            "source": source,
            "timestamp": time.time()
        })
        # Prefix topic for filtering
        self.pub_socket.send_multipart([
            f"param/{topic_param}".encode('utf-8'),
            message.encode('utf-8')
        ])
        self.control_publisher.publish(param, value)
        logger.debug(f"Published update: topic=param/{topic_param}, internal={param}, value={value}")

    def _broadcast_metrics(self, metrics):
        """Publish PHY metrics via PUB socket for monitoring clients."""
        message = json.dumps({
            "metrics": metrics,
            "timestamp": time.time(),
        })
        self.pub_socket.send_multipart([
            METRICS_TOPIC.encode('utf-8'),
            message.encode('utf-8'),
        ])
        logger.debug("Published metrics on %s", METRICS_TOPIC)

    def _decode_metrics_message(self, metrics_bytes):
        """Decode either plain JSON or GNU Radio PMT-wrapped JSON metrics."""
        try:
            return json.loads(metrics_bytes.decode("utf-8").strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        if pmt is not None:
            try:
                message = pmt.deserialize_str(metrics_bytes)
                payload = message
                if pmt.is_pair(message):
                    payload = pmt.cdr(message)

                if pmt.is_u8vector(payload):
                    decoded = bytes(pmt.u8vector_elements(payload)).decode("utf-8")
                    return json.loads(decoded)
            except Exception:
                pass

        decoded = metrics_bytes.decode("utf-8", errors="ignore")
        json_start = min(
            (index for index in (decoded.find("{"), decoded.find("[")) if index != -1),
            default=-1,
        )
        if json_start != -1:
            return json.loads(decoded[json_start:])

        raise ValueError("Unsupported metrics payload format")
    
    def _handle_pull(self):
        """Handle asynchronous PULL metrics ingestion from PHY."""
        while self.running:
            try:
                # Receive metrics
                metrics_bytes = self.pull_socket.recv(zmq.NOBLOCK)
                metrics = self._decode_metrics_message(metrics_bytes)
                
                # Process metrics (could store, aggregate, etc.)
                logger.info(f"Received metrics: {metrics}")
                self._broadcast_metrics(metrics)
                
            except zmq.error.Again:
                # No message available, sleep briefly
                time.sleep(0.01)
            except zmq.error.ContextTerminated:
                break
            except Exception as e:
                logger.error(f"PULL handler error: {e}")


def main():
    controller = ZMQController()
    controller.start()


if __name__ == "__main__":
    main()
