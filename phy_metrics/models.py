from dataclasses import dataclass
import time


class PhyMetrics:
    bits: int = 0
    errors: int = 0
    rssi: float = None
    snr: float = None
    ber: float = None
    noise_floor: float = None
    center_freq: float = None
    bandwidth: float = None
    sample_rate: float = None
    timestamp: float = None

    def update_timestamp(self):
        self.timestamp = time.time()

    def __repr__(self):
        return (f"PhyMetrics(rssi={self.rssi}, snr={self.snr}, ber={self.ber}, "
                f"noise_floor={self.noise_floor}, center_freq={self.center_freq}, "
                f"bandwidth={self.bandwidth}, sample_rate={self.sample_rate}, "
                f"timestamp={self.timestamp}, bits={self.bits}, errors={self.errors})")
    
    def to_dict(self):
        return self.__dict__