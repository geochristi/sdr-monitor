from .models import PhyMetrics
from .filters import MovingAverage
from .alarms import PhyAlarmDetector

class PhyMetricsEngine:
    def __init__(self):
        self.metrics = PhyMetrics()
        self.alarm_detector = PhyAlarmDetector()

        #filters
        self.rssi_filter = MovingAverage(5)
        self.snr_filter = MovingAverage(5)
        

    def update(self, data: dict):
        if 'rssi' in data:
            self.metrics.rssi = self.rssi_filter.update(data['rssi'])
        if 'snr' in data:
            self.metrics.snr = self.snr_filter.update(data['snr'])
        if 'ber' in data:
            self.metrics.ber = data['ber']
        if 'noise_floor' in data:
            self.metrics.noise_floor = data['noise_floor']
        if 'center_freq' in data:
            self.metrics.center_freq = data['center_freq']
        if 'bandwidth' in data:
            self.metrics.bandwidth = data['bandwidth']
        if 'sample_rate' in data:
            self.metrics.sample_rate = data['sample_rate']

        self.metrics.update_timestamp()
        return self.alarm_detector.check(self.metrics)

    def get_metrics(self, name: str):
        return getattr(self.metrics, name, None)
    
    def get_all(self):
        return self.metrics