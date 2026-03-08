# PHY Metrics Module

This folder contains the metric-processing core used by the SDR monitor control loop.

It takes raw PHY telemetry (from ZeroMQ subscriber input), smooths key signals,
stores the latest values, and returns alarm conditions when thresholds are violated.

## What It Does

- Keeps a live in-memory PHY metric state (`rssi`, `snr`, `ber`, `bits`, `errors`, etc.).
- Applies filtering to noisy values (`rssi`, `snr`) using moving averages.
- Checks simple alarm rules (low SNR, high BER).
- Timestamps each update for downstream monitoring.

## Files

- `metrics_engine.py`: main orchestration class (`PhyMetricsEngine`).
- `models.py`: `PhyMetrics` state object and serialization helper (`to_dict`).
- `filters.py`: smoothing filters (`MovingAverage`, `ExponentialSmoothing`).
- `alarms.py`: alarm detector and thresholds.

## Processing Flow

1. `PhyMetricsEngine.update(data)` receives a telemetry dictionary.
2. `rssi` and `snr` are filtered using a 5-sample moving average.
3. Other supported keys are copied directly (`ber`, `bits`, `errors`, `noise_floor`, `center_freq`, `bandwidth`, `sample_rate`).
4. If `bits > 0`, BER is recomputed as `errors / bits`.
5. Timestamp is refreshed.
6. Alarm detector runs and returns a list of active alarms.

## Default Alarm Thresholds

Defined in `alarms.py`:

- `snr_low`: `5`
- `ber_high`: `0.01`

Possible alarm strings:

- `Low SNR`
- `High BER`

## Example Usage

```python
from phy_metrics.metrics_engine import PhyMetricsEngine

engine = PhyMetricsEngine()

sample = {
	"rssi": -48.2,
	"snr": 4.1,
	"bits": 20000,
	"errors": 240,
	"noise_floor": -92.0,
}

alarms = engine.update(sample)
print(engine.get_all().to_dict())
print(alarms)
```

## Integration Point

This module is used by `control/main.py`, which receives telemetry via `transport/zmq_sub.py` and feeds each message into `PhyMetricsEngine`.
