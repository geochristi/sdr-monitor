import time
from transport.zmq_sub import ZMQSubscriber
from phy_metrics.metrics_engine import PhyMetricsEngine


"""Live metrics monitor that consumes controller-republished PHY telemetry."""

def main():
    subscriber = ZMQSubscriber()
    engine = PhyMetricsEngine()

    print("Starting metrics monitor loop...")

    while True:
        data = subscriber.receive()
        if data is None:
            continue

        alarms = engine.update(data)
        print("Received metrics:", data)
        print("ENGINE:", engine.get_all().to_dict())
    
        if alarms:
            print("ALARMS:", alarms)

        time.sleep(0.05)  # Sleep to prevent busy waiting

if __name__ == "__main__":    main()