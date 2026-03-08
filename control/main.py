import time
import json
from transport.zmq_sub import ZMQSubscriber
from phy_metrics.metrics_engine import PhyMetricsEngine

# Subscribes to PHY telemetry, feeds it into the metrics engine, prints metrics/alarms, and loops continuously with a short sleep.

def main():
    subscriber = ZMQSubscriber()
    engine = PhyMetricsEngine()

    print("Starting main loop to receive PHY metrics...")

    while True:
        data = subscriber.receive()
        if data is None:
            # No telemetry this cycle (timeout)
            continue
        alarms = engine.update(data)
        print ("Received data:", data)
        print("ENGINE:", engine.get_all().to_dict())
    
        if alarms:
            print("ALARMS:", alarms)

        time.sleep(0.05)  # Sleep to prevent busy waiting

if __name__ == "__main__":    main()