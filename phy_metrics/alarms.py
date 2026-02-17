class PhyAlarmDetector:
    def __init__(self):
        self.thresholds = {
            "snr_low": 5,
            "ber_high": 0.01
        }

    def check(self, metrics):
        alarms = []
        if metrics.snr is not None and metrics.snr < self.thresholds["snr_low"]:
            alarms.append("Low SNR")
        if metrics.ber is not None and metrics.ber > self.thresholds["ber_high"]:
            alarms.append("High BER")
        return alarms