from transport.zmq_sub import ZMQSubscriber
from phy_metrics.metrics_engine import PhyMetricsEngine

def main():
    subscriber = ZMQSubscriber()
    engine = PhyMetricsEngine()

    print("Starting main loop to receive PHY metrics...")

    while True:
        data = subscriber.receive()
        alarms = engine.update(data)

        print(engine.get_all().to_dict())
    
        if alarms:
            print("ALARMS:", alarms)

if __name__ == "__main__":    main()