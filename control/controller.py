# Controller stores the state of the system and provides methods to update it.

import threading
import os
import tempfile
import fcntl
from pathlib import Path

CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"
FALLBACK_CONTROL_FILE = str(Path(__file__).resolve().parents[1] / "phy_cotrol.txt")

DEFAULT_CONTROL_STATE = {
    "noise": 0.0,
    "snr": 30.0,
    "rate": 0,
    "freq_offset": 0,
    "mod_scheme": 3,
    "ber_inject": 0.0,
}

CONTROL_FILE_MODE = 0o664
LOCK_FILE_MODE = 0o666

LEGACY_ALIASES = {
    "packet_rate": "rate",
    "modulation": "mod_scheme",
    "frequency": "freq_offset",
}

class Controller:
    def __init__(self):
        self.state = dict(DEFAULT_CONTROL_STATE)
        self.lock = threading.Lock()

    def ensure_control_file(self):
        with self.lock:
            if self._read_state_from_disk_locked() is not None:
                return

            self.state = dict(DEFAULT_CONTROL_STATE)
            for name, value in DEFAULT_CONTROL_STATE.items():
                self._write_to_file(name, value, source="controller-init", emit_warning=False)

    def set_param(self, name, value, source="unknown"):
        with self.lock:
            canonical_name = self._canonical_name(name)
            if canonical_name not in self.state:
                raise ValueError(f"Unknown parameter: {name}")

            normalized_value = self._normalize_value(canonical_name, value)
            self.state[canonical_name] = normalized_value
            print(f"Parameter '{name}' set to {value} by {source}")
            self._write_to_file(canonical_name, normalized_value, source, emit_warning=True)

    def upsert_control_param(self, name, value, source="unknown"):
        with self.lock:
            canonical_name = self._canonical_name(name)
            normalized_value = self._normalize_value(canonical_name, value)
            self.state[canonical_name] = normalized_value
            self._write_to_file(canonical_name, normalized_value, source, emit_warning=False)

    def get_param(self, name, refresh=False):
        with self.lock:
            canonical_name = self._canonical_name(name)
            if refresh:
                self._refresh_state_from_disk_locked()
            return self.state.get(canonical_name, None)

    def get_all_params(self, refresh=False):
        with self.lock:
            if refresh:
                self._refresh_state_from_disk_locked()
            return dict(self.state)

    def _canonical_name(self, name):
        return LEGACY_ALIASES.get(name, name)

    def _refresh_state_from_disk_locked(self):
        loaded_state = self._read_state_from_disk_locked()
        if loaded_state is not None:
            self.state.update(loaded_state)

    def _read_state_from_disk_locked(self):
        for file_path in (CONTROL_FILE, FALLBACK_CONTROL_FILE):
            loaded_state = self._read_state_file(file_path)
            if loaded_state is not None:
                return loaded_state
        return None

    def _read_state_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as control_file:
                loaded_state = {}
                for raw_line in control_file:
                    if "=" not in raw_line:
                        continue

                    key, raw_value = raw_line.strip().split("=", 1)
                    canonical_name = self._canonical_name(key.strip())
                    if canonical_name not in DEFAULT_CONTROL_STATE:
                        continue

                    try:
                        loaded_state[canonical_name] = self._normalize_value(canonical_name, raw_value)
                    except (TypeError, ValueError):
                        continue

                return loaded_state
        except (FileNotFoundError, PermissionError, OSError):
            return None

    def _normalize_value(self, name, value):
        if name == "noise":
            return max(0.0, min(float(value), 10.0))
        if name == "snr":
            return max(0.0, min(float(value), 60.0))
        if name == "rate":
            return max(0, min(int(value), 1000000))
        if name == "freq_offset":
            return max(-1000000, min(int(value), 1000000))
        if name == "mod_scheme":
            return max(0, min(int(value), 4))
        if name == "ber_inject":
            return max(0.0, min(float(value), 1.0))
        raise ValueError(f"Unknown parameter: {name}")
        
    def _write_to_file(self, name, value, source, emit_warning=False):
        line = f"{name}={value}\n"
        try:
            self._upsert_param(CONTROL_FILE, name, line)
        except PermissionError:
            self._upsert_param(FALLBACK_CONTROL_FILE, name, line)
            if emit_warning:
                print(
                    f"Warning: No write permission for {CONTROL_FILE}; wrote update to {FALLBACK_CONTROL_FILE} instead."
                )

    def _upsert_param(self, file_path, name, new_line):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = str(path) + ".lock"

        # Open lock file with explicit mode; if stale permissions block access,
        # recreate it in our writable control directory.
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, LOCK_FILE_MODE)
        except PermissionError:
            os.unlink(lock_path)
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, LOCK_FILE_MODE)

        with os.fdopen(lock_fd, "a", encoding="utf-8") as lock_file:
            try:
                os.fchmod(lock_file.fileno(), LOCK_FILE_MODE)
            except OSError:
                pass
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing_lines = f.readlines()
                except (FileNotFoundError, PermissionError):
                    existing_lines = []

                updated_lines = []
                replaced = False

                for raw_line in existing_lines:
                    if "=" not in raw_line:
                        updated_lines.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
                        continue

                    key, _ = raw_line.split("=", 1)
                    if key.strip() == name:
                        if not replaced:
                            updated_lines.append(new_line)
                            replaced = True
                        continue

                    updated_lines.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")

                if not replaced:
                    updated_lines.append(new_line)

                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        "w",
                        encoding="utf-8",
                        dir=path.parent,
                        prefix=f".{path.name}.",
                        suffix=".tmp",
                        delete=False,
                    ) as tmp_file:
                        tmp_file.writelines(updated_lines)
                        tmp_file.flush()
                        os.fsync(tmp_file.fileno())
                        tmp_path = tmp_file.name

                    os.replace(tmp_path, path)
                    try:
                        os.chmod(path, CONTROL_FILE_MODE)
                    except OSError:
                        pass
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)