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

## BER Injection Note

The BER comparator block (`phy/phy_flowgraph_epy_block_1.py`) supports runtime BER injection
through `ber_inject` in `control/phy_control.txt`.

When enabled, the comparator intentionally introduces controlled symbol mismatches before
computing and publishing BER metrics. `PhyMetricsEngine` then processes those updated
`bits/errors/ber` values like normal telemetry.

## BER / Counter Reset Behavior (Important)

`PhyMetricsEngine` processes incoming telemetry and typically receives cumulative
`bits` and `errors` counters from the publisher side.

Because of that:

- Calling reset only in the SNMP layer does **not** change upstream cumulative counters.
- On the next telemetry packet, raw totals continue increasing from the source.

### Recommended reset model

Use an SNMP-side baseline reset:

- Store `reset_bits_base` = current raw bits at reset time.
- Store `reset_errors_base` = current raw errors at reset time.
- Report effective counters as:
  - `bits_effective = max(0, bits_raw - reset_bits_base)`
  - `errors_effective = max(0, errors_raw - reset_errors_base)`
  - `ber_effective = errors_effective / bits_effective` (if `bits_effective > 0`)

This provides user-visible reset semantics even when publisher counters are cumulative.

### True source reset

If you need absolute reset across all consumers, implement reset in the telemetry
publisher/transmitter that owns the original counters.
