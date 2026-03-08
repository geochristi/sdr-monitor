# Control Module

This folder contains the runtime control loop that consumes PHY telemetry from ZeroMQ,
updates processed metrics, and reports alarm conditions.

## Purpose

`control/main.py` acts as the live monitoring loop of the project.
It connects to the telemetry stream, feeds samples into `PhyMetricsEngine`,
and prints both current metrics and active alarms.

## Data Flow

1. `ZMQSubscriber` connects to `tcp://127.0.0.1:5556`.
2. Incoming JSON telemetry is decoded.
3. `PhyMetricsEngine.update(data)` applies smoothing and metric updates.
4. Alarm detector checks thresholds and returns alarm labels.
5. Loop prints received data, current engine state, and alarms.

## Files

- `main.py`: control loop entrypoint.
- `phy_control.txt`: control-plane state file (currently stores `noise=<value>` for SNMP set path).
- `adaptive_logic.py`: placeholder for closed-loop adaptation logic.
- `scheduler.py`: placeholder for scheduling policy logic.

## Run

From repository root:

```bash
cd ~/Desktop/SDR
python3 -m control.main
```

## Expected Telemetry Keys

The metrics engine can consume:

- `rssi`
- `snr`
- `ber`
- `bits`
- `errors`
- `noise_floor`
- `center_freq`
- `bandwidth`
- `sample_rate`

If `bits` and `errors` are present and `bits > 0`, BER is recomputed as:

`ber = errors / bits`

## Alarm Rules

Current defaults (in `phy_metrics/alarms.py`):

- `Low SNR` when `snr < 5`
- `High BER` when `ber > 0.01`

## Typical Console Output

You should see lines similar to:

- `Received data: {...}`
- `ENGINE: {...}`
- `ALARMS: ['Low SNR']` (only when thresholds are exceeded)

## Notes

- Subscriber receive timeout defaults to 1 second (`RCVTIMEO=1000` in `transport/zmq_sub.py`).
- If no message arrives, loop continues without updating metrics for that cycle.
