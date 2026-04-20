#!/usr/bin/env python3
"""
Monitor parameter broadcasts from the ZMQ controller.
Run this in a separate terminal to see all parameter updates.
"""
import zmq
import json
import sys


TOPIC_ALIASES = {
    "noise": "param/noise",
    "snr": "param/snr",
    "rate": "param/rate",
    "frequency": "param/frequency",
    "freq_offset": "param/frequency",
    "modulation": "param/modulation",
    "mod_scheme": "param/modulation",
    "ber": "param/ber",
    "ber_inject": "param/ber",
}


def resolve_topics(args):
    if not args:
        return [b"param/"]
    topics = []
    for arg in args:
        topic = TOPIC_ALIASES.get(arg, arg)
        if not topic.startswith("param/"):
            topic = f"param/{topic}"
        topics.append(topic.encode("utf-8"))
    return topics

def main():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    
    # Connect to controller's PUB socket
    socket.connect("tcp://127.0.0.1:5556")

    topics = resolve_topics(sys.argv[1:])
    for topic in topics:
        socket.setsockopt(zmq.SUBSCRIBE, topic)

    print("Listening for parameter broadcasts on 5556...")
    print("Subscribed topics:", ", ".join(topic.decode("utf-8") for topic in topics))
    print("=" * 60)
    
    try:
        while True:
            # Receive topic and message
            topic = socket.recv_string()
            message = socket.recv_string()
            
            try:
                data = json.loads(message)
                print(f"{topic}")
                if "internal_param" in data and data.get("internal_param") != data.get("param"):
                    print(f"   mapping: {data.get('param')} -> {data.get('internal_param')}")
                if "source" in data:
                    print(f"   source: {data.get('source')}")
                print(f"   {json.dumps(data, indent=4)}")
            except json.JSONDecodeError:
                print(f"{topic}: {message}")
            print()
    except KeyboardInterrupt:
        print("\nMonitor stopped")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
