#!/usr/bin/env python3
"""GUI rehabilitasi FES dengan koneksi serial langsung.

Fokus antarmuka:
- Persiapan sensor: kalibrasi sudut IMU dan pengambilan nilai MVC EMG.
- Mode Auto dan Manual dengan parameter arus, frekuensi, PW, durasi ACTIVE/REST.
- Mode Auto menambahkan target sudut.
- FSM sesi menggunakan state IDLE, KONTRAKSI, dan RELAKSASI.
- Monitoring EMG menampilkan RMS, sudut, error sudut, PW, frekuensi, arus, FSM,
  status gerakan, serta durasi ACTIVE dan REST.
- System Health, status MCP4725/H-Bridge/FES, logging CSV, dan E-STOP tetap tersedia.

Koneksi MCU memakai UART langsung tanpa handshake. Begitu port serial terbuka,
kontrol serial tersedia; firmware tetap menjadi pemilik interlock, batas arus,
watchdog, dead-time H-bridge, dan proteksi perangkat.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import queue
import random
import re
import sys
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple, Union

if sys.platform == "win32":
    try:
        import ctypes

        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover - only relevant on minimal Linux installs
    tk = None  # type: ignore[assignment]
    filedialog = messagebox = ttk = None  # type: ignore[assignment]
    TK_IMPORT_ERROR: Optional[Exception] = exc
else:
    TK_IMPORT_ERROR = None

try:
    import serial  # type: ignore[import-not-found]
except ImportError as exc:
    serial = None  # type: ignore[assignment]
    SERIAL_IMPORT_ERROR: Optional[Exception] = exc
else:
    SERIAL_IMPORT_ERROR = None

try:
    from serial.tools import list_ports  # type: ignore[import-not-found]
except (ImportError, AttributeError):
    list_ports = None  # type: ignore[assignment]

try:
    import winreg  # Windows Registry fallback untuk enumerasi COM
except ImportError:  # pragma: no cover - non-Windows
    winreg = None  # type: ignore[assignment]


APP_NAME = "GUI Stimulator Aldin · Direct Serial · SYNC FIX v4"
BAUD_RATE = 115200
SERIAL_FRAME_MAX_BYTES = 2048
SERIAL_DIAGNOSTIC_INTERVAL_SECONDS = 1.0
DATA_STALE_SECONDS = 1.0
DATA_ABORT_SECONDS = 3.0
HEARTBEAT_INTERVAL_SECONDS = 0.25
PROJECT_CURRENT_MAX_MA = 30.0
PROJECT_FIXED_CURRENT_MA = 15.0
PROJECT_FIXED_FREQUENCY_HZ = 35.0
PROJECT_FREQUENCY_MIN_HZ = 10.0
PROJECT_FREQUENCY_MAX_HZ = 80.0
# Firmware stim4_config / H-Bridge memakai pulse width, bukan duty-cycle persen.
PROJECT_PWM_MIN_US = 100.0
PROJECT_PWM_MAX_US = 400.0
PROJECT_PWM_DEFAULT_US = 250.0
PROJECT_DEFAULT_TARGET_ANGLE_DEG = 35.0

ACTIVE_PHASES = {
    "AUTO": {"AUTO", "RUNNING_AUTO", "AUTO_RUNNING", "KONTRAKSI", "CONTRACTION", "RELAKSASI", "RELAXATION", "REST"},
    "MANUAL": {"MANUAL", "RUNNING_MANUAL", "MANUAL_RUNNING", "KONTRAKSI", "CONTRACTION", "RELAKSASI", "RELAXATION", "REST"},
}
STOPPED_PHASES = {
    "IDLE", "SAFE_IDLE", "OUTPUT_OFF", "STOPPED_USER", "STOPPED_LINK",
    "STOPPED_SENSOR", "STOPPED_FAULT", "FAULT", "E_STOP", "ESTOP",
}
SELECTED_MODES = {"NONE", "AUTO", "MANUAL"}
SYSTEM_STATES = {
    "SYSTEM_INIT", "SYSTEM_WAIT_READY", "SYSTEM_CALIBRATION", "SYSTEM_CONFIG",
    "SYSTEM_READY_TO_START", "SYSTEM_THERAPY", "SYSTEM_COMPLETED", "SYSTEM_EMERGENCY",
}
SYSTEM_MODES = {"WAIT", "STANDBY", "AUTO", "MANUAL", "EMERGENCY"}
FSM_ACTIVE_FAMILY = {"KONTRAKSI", "ACTIVE_NORMAL", "ACTIVE_FATIGUE", "MANUAL_ACTIVE"}
FSM_REST_FAMILY = {"RELAKSASI", "REST", "FATIGUE_REST", "MANUAL_REST"}
FSM_SAFE_STOPPED = {"IDLE", "MANUAL_STOPPED", "THERAPY_STOP"}


COLORS = {
    "bg": "#0A0F16",
    "sidebar": "#0D141E",
    "panel": "#121A24",
    "panel_2": "#182331",
    "line": "#2A3747",
    "text": "#E8EDF4",
    "muted": "#909CAA",
    "blue": "#5793D1",
    "cyan": "#55AAA5",
    "green": "#62B58E",
    "yellow": "#D5A94F",
    "red": "#DF6A70",
    "red_dark": "#8E343C",
    "ready_bg": "#17352F",
    "white": "#FFFFFF",
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def phase_matches_mode(mode: str, phase: str) -> bool:
    return str(phase).strip().upper() in ACTIVE_PHASES.get(str(mode).strip().upper(), set())


def phase_confirms_stopped(phase: str) -> bool:
    return str(phase).strip().upper() in STOPPED_PHASES


def pwm_pct_to_us(pct: float) -> float:
    pct = max(0.0, min(100.0, float(pct)))
    return PROJECT_PWM_MIN_US + pct * (PROJECT_PWM_MAX_US - PROJECT_PWM_MIN_US) / 100.0


def pwm_us_to_pct(pulse_width_us: float) -> float:
    pulse_width_us = max(PROJECT_PWM_MIN_US, min(PROJECT_PWM_MAX_US, float(pulse_width_us)))
    span = PROJECT_PWM_MAX_US - PROJECT_PWM_MIN_US
    return 0.0 if span <= 0.0 else 100.0 * (pulse_width_us - PROJECT_PWM_MIN_US) / span


def format_elapsed_ms(ms: Optional[Union[int, float]]) -> str:
    """Format elapsed state timer in integer seconds (floor semantics)."""
    if ms is None:
        return "--- s"
    return f"{max(0, int(ms) // 1000)} s"


def format_remaining_ms(ms: Optional[Union[int, float]]) -> str:
    """Format remaining state timer in integer seconds (ceiling semantics for positive values)."""
    if ms is None:
        return "--- s"
    val = int(ms)
    if val <= 0:
        return "0 s"
    return f"{(val + 999) // 1000} s"


def format_remaining_duration(
    timer_ms: Optional[Union[int, float]], remaining_ms: Optional[Union[int, float]],
) -> str:
    """Format countdown over state duration in integer seconds: '10/10 s', '9/10 s', etc."""
    if remaining_ms is None and timer_ms is None:
        return "---"
    rem_ms = int(remaining_ms) if remaining_ms is not None else 0
    elap_ms = int(timer_ms) if timer_ms is not None else 0
    total_ms = rem_ms + elap_ms
    if total_ms <= 0:
        return "---"
    rem_s = (rem_ms + 999) // 1000 if rem_ms > 0 else 0
    dur_s = max(1, (total_ms + 500) // 1000)
    return f"{rem_s}/{dur_s} s"


def generate_therapy_session_id() -> str:
    """Generate a unique, readable therapy session identifier: YYYYMMDD_HHMMSS_XXXX."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{timestamp}_{suffix}"


def _norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip().replace("%", "")
    # A single comma without a dot is commonly used as a decimal separator.
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
    text = _norm_key(value)
    if text in {"1", "true", "yes", "on", "active", "aktif", "ready"}:
        return True
    if text in {"0", "false", "no", "off", "inactive", "nonaktif", "not_ready"}:
        return False
    return None


def _flatten_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Flatten common telemetry wrappers without trying to interpret commands."""

    flat: Dict[str, Any] = {}
    for key, value in payload.items():
        normalized = _norm_key(key)
        if normalized in {"data", "telemetry", "payload", "values"} and isinstance(value, Mapping):
            flat.update(_flatten_payload(value))
        elif normalized == "fatigue" and isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                flat[f"fatigue_{_norm_key(nested_key)}"] = nested_value
        else:
            flat[normalized] = value
    return flat


CURRENT_CMD_MA_KEYS = {
    "current_cmd_ma", "current_command_ma",
    "current_ma", "current_m_a", "i_ma", "ima", "arus_ma", "ampere_ma",
}
CURRENT_CMD_A_KEYS = {"current_cmd_a", "current_command_a", "current_a", "i_a", "ampere", "amps"}
CURRENT_SET_KEYS = {"current_set_ma", "i_set_ma", "arus_set_ma", "target_current_ma"}
ANGLE_KEYS = {"angle", "angle_deg", "sudut", "sudut_deg", "theta", "joint_angle"}
ANGLE_TARGET_KEYS = {"angle_target_deg", "target_angle_deg", "sudut_target_deg"}
PWM_KEYS = {
    "pw_pct", "pwm_pct", "pwm_percent", "pwm_out_pct", "duty_pct",
}
PWM_COMMAND_KEYS = {"pw_command_pct", "pwm_cmd_pct", "pwm_command_pct", "pwm_set_pct"}
PWM_RAW_KEYS = {"pwm_raw", "duty_raw", "pwm_8bit"}
FATIGUE_SCORE_KEYS = {
    "fatigue_score", "fatigue_index", "fatigue_level", "fatigue_pct", "fatigue_percent",
}
FATIGUE_STATE_KEYS = {
    "fatigue_state", "fatigue_status", "fatigue_phase", "fatigue_detected", "fatigue",
}
EMG_KEYS = {"emg_rms_mv", "rms_mv", "emg_rms", "emg", "rms"}
EMG_MAV_KEYS = {"emg_mav_mv", "mav_mv", "emg_mav", "mav"}
MAV_RATIO_KEYS = {"mav_ratio", "emg_mav_ratio"}
FATIGUE_FLAG_KEYS = {"fatigue_flag", "fatigue_confirmed"}
FATIGUE_COUNT_KEYS = {"fatigue_count", "fatigue_rest_count"}
CLIPPING_PERCENT_KEYS = {"clipping_percent_1s", "emg_clipping_percent_1s", "clipping_percent"}
EMG_ERROR_FLAGS_KEYS = {"emg_error_flags", "emg_errors", "emg_fault_flags"}
QUALITY_KEYS = {"signal_quality", "emg_quality", "quality"}
PHASE_KEYS = {"phase", "session_phase", "stim_phase", "state"}
FATIGUE_THRESHOLD_KEYS = {"fatigue_threshold", "fatigue_threshold_score", "fatigue_limit"}
OUTPUT_KEYS = {"output", "output_active", "stim_active", "stimulation_active"}
STOP_REASON_KEYS = {"stop_reason", "reason_stop", "last_stop_reason"}
FAULT_KEYS = {"fault", "fault_code", "error_code"}
EMERGENCY_KEYS = {"emergency", "estop", "emergency_active"}
EMERGENCY_SOURCE_KEYS = {"emergency_source", "estop_source"}
PULSE_WIDTH_KEYS = {"pulse_width_us", "pulse_us", "pw_us"}
FREQUENCY_SET_KEYS = {"frequency_set_hz", "frequency_target_hz", "freq_set_hz"}
FREQUENCY_OUTPUT_KEYS = {"frequency_output_hz", "frequency_out_hz", "freq_output_hz"}
FREQUENCY_LEGACY_KEYS = {"frequency_hz", "freq_hz", "stim_frequency_hz"}
SESSION_KEYS = {"session_id", "sid"}
MCU_STATUS_KEYS = {"mcu_status", "mcu", "device_status"}
EMG_STATUS_KEYS = {"emg_status", "sensor_emg_status"}
IMU_A_STATUS_KEYS = {"imu_a_status", "imu1_status", "imu_a", "imu1"}
IMU_B_STATUS_KEYS = {"imu_b_status", "imu2_status", "imu_b", "imu2"}
IMU_A_ANGLE_KEYS = {"imu_a_angle_deg", "imu1_angle_deg", "angle_a_deg", "imu_a_angle"}
IMU_B_ANGLE_KEYS = {"imu_b_angle_deg", "imu2_angle_deg", "angle_b_deg", "imu_b_angle"}
ANGLE_ERROR_KEYS = {"angle_error_deg", "error_angle_deg", "error_deg", "joint_error_deg"}
DELTA_ERROR_KEYS = {"delta_error_deg", "error_delta_deg", "delta_error", "d_error_deg", "de_deg"}
FUZZY_PWM_KEYS = {"fuzzy_pwm_pct", "pwm_fuzzy_pct", "fuzzy_output_pct", "pwm_star_pct"}
INTENT_STATE_KEYS = {"intent", "intent_state", "movement_intent", "emg_intent"}
INTENT_SCORE_KEYS = {"intent_score", "intent_level", "intent_confidence"}
MCP4725_STATUS_KEYS = {"mcp4725_status", "dac_status", "mcp_status"}
HBRIDGE_STATUS_KEYS = {"hbridge_status", "h_bridge_status", "hb_status", "hbridge_ready", "h_bridge_ready"}
DAC_RAW_KEYS = {"dac_raw", "dac_value", "mcp4725_raw", "mcp4725_value"}
DAC_VOLTAGE_KEYS = {"dac_voltage_v", "dac_v", "mcp4725_voltage_v"}
FES_STATUS_KEYS = {"fes_status", "stimulator_status", "stim_status"}
START_BLOCK_KEYS = {"start_block", "start_block_reason", "start_reject_reason"}
ANGLE_CAL_KEYS = {"angle_calibrated", "imu_calibrated", "angle_cal_ok"}
EMG_CAL_KEYS = {"emg_calibrated", "emg_cal_ok"}
FSM_STATE_KEYS = {"fsm", "fsm_state", "state_fsm", "rehab_state"}
MVC_VALUE_KEYS = {"mvc_mv", "mvc_value_mv", "mvc_value", "emg_mvc_mv"}
MVC_READY_KEYS = {"mvc_ready", "mvc_valid", "mvc_done", "mvc_ok"}
ACTIVE_DURATION_KEYS = {"active_duration_s", "duration_active_s", "active_s", "waktu_active_s"}
REST_DURATION_KEYS = {"rest_duration_s", "duration_rest_s", "rest_s", "waktu_rest_s"}
SYSTEM_STATE_KEYS = {"system_state", "stm32_system_state"}
THERAPY_RUNNING_KEYS = {"therapy_running", "therapy_active", "therapy_is_running"}
MODE_KEYS = {"mode", "selected_mode", "therapy_mode"}
THERAPY_TIMER_MS_KEYS = {"therapy_timer_ms", "state_elapsed_ms", "phase_elapsed_ms"}
STATE_REMAINING_MS_KEYS = {"state_remaining_ms", "phase_remaining_ms"}
IMU_ZERO_OFFSET_KEYS = {"imu_zero_offset_deg", "zero_offset_deg", "g_zero_offset", "offset_deg"}

EMG_ERROR_EXCESSIVE_CLIPPING = 1 << 6


def has_excessive_clipping(error_flags: Any) -> bool:
    return (
        isinstance(error_flags, int)
        and not isinstance(error_flags, bool)
        and (error_flags & EMG_ERROR_EXCESSIVE_CLIPPING) != 0
    )


def should_estop_for_emg_quality(signal_quality: Any, error_flags: Any) -> bool:
    quality = str(signal_quality or "").strip().upper()
    return (
        not has_excessive_clipping(error_flags)
        and quality not in {"GOOD", "BAIK", "OK", "VALID", "CLIPPING"}
    )


def normalize_fatigue_state(value: Any) -> str:
    if isinstance(value, bool):
        return "WARNING" if value else "NORMAL"
    text = _norm_key(value)
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", str(value).strip()):
        return "UNKNOWN"
    if text in {"akhir", "end", "final", "severe", "stop", "stopped_fatigue", "fatigue_final"}:
        return "FINAL"
    if text in {"1", "true", "yes", "detected", "fatigue", "warning", "warn", "medium", "waspada", "early", "fatiguing"}:
        return "WARNING"
    if text in {"0", "false", "no", "normal", "fresh", "relax", "relaxed", "aman"}:
        return "NORMAL"
    if text in {"na", "n_a", "not_available", "invalid", "sensor_invalid", "unknown"}:
        return "INVALID" if text in {"invalid", "sensor_invalid"} else "N/A"
    if text in {"calibrating", "kalibrasi"}:
        return "CALIBRATING"
    return str(value).strip().upper()[:24] if str(value).strip() else "UNKNOWN"


def normalize_fsm_state(value: Any) -> str:
    text = _norm_key(value)
    if text in {"idle", "safe_idle", "standby", "ready", "manual_stopped"}:
        return "IDLE"
    if text in {"kontraksi", "contraction", "contract", "active", "stim_active", "stimulation"}:
        return "KONTRAKSI"
    if text in {"relaksasi", "relaxation", "relax", "rest", "recovery"}:
        return "RELAKSASI"
    if text in {"emergency", "e_stop", "estop", "fault_emergency"}:
        return "EMERGENCY"
    if text in {"auto", "manual"}:
        return "UNKNOWN"
    return str(value).strip().upper()[:24] if str(value).strip() else "IDLE"


def raw_fsm_state(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text[:32] if text else "IDLE"


def fsm_is_safe_stopped(value: Any) -> bool:
    return raw_fsm_state(value) in FSM_SAFE_STOPPED


def normalize_selected_mode(value: Any) -> str:
    mode = str(value or "").strip().upper()
    return mode if mode in SELECTED_MODES else "NONE"


def normalize_system_state(value: Any) -> str:
    state = str(value or "").strip().upper()
    return state if state in SYSTEM_STATES else "SYSTEM_INIT"


def derive_system_mode(telemetry: "Telemetry") -> str:
    state = normalize_system_state(telemetry.system_state)
    selected_mode = normalize_selected_mode(telemetry.selected_mode)

    if telemetry.emergency is True or state == "SYSTEM_EMERGENCY":
        return "EMERGENCY"
    if state == "SYSTEM_THERAPY" and telemetry.therapy_running is True:
        if selected_mode == "AUTO":
            return "AUTO"
        if selected_mode == "MANUAL":
            return "MANUAL"
        return "WAIT"
    if (
        state in {"SYSTEM_CONFIG", "SYSTEM_READY_TO_START", "SYSTEM_COMPLETED"}
        and telemetry.output_active is not True
    ):
        return "STANDBY"
    return "WAIT"


def telemetry_fsm_state(update: Mapping[str, Any]) -> str:
    """Use explicit firmware FSM state. Use phase only when FSM is absent."""

    explicit = update.get("fsm_state")
    if explicit is not None and str(explicit).strip():
        return raw_fsm_state(explicit)
    return normalize_fsm_state(update.get("phase", "IDLE"))


def telemetry_confirms_estop_reset(
    emergency: Optional[bool], output_active: Optional[bool], fsm_state: Any,
) -> bool:
    """Accept reset only from explicit safe, non-running firmware telemetry."""

    return bool(
        emergency is False
        and fsm_is_safe_stopped(fsm_state)
        and output_active is False
    )


def parse_telemetry_line(line: str) -> Dict[str, Any]:
    """Parse JSON, ``TEL key=value`` and legacy ``EMG_RMS_MV`` messages.

    The parser intentionally returns only known telemetry fields. Unknown content
    cannot become a GUI command.
    """

    raw = line.strip().strip("\x00")
    if not raw:
        return {}

    source: Dict[str, Any] = {}
    frame_type = ""
    if raw.startswith("{"):
        try:
            decoded = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            decoded = None
        if isinstance(decoded, Mapping):
            source = _flatten_payload(decoded)
            if _norm_key(decoded.get("type", "")) in {"tel", "telemetry"}:
                frame_type = "TEL"

    if not source:
        body = re.sub(r"^\s*(?:TEL|TELEMETRY)\s*[:|,]?\s*", "", raw, flags=re.IGNORECASE)
        if re.match(r"^\s*(?:TEL|TELEMETRY)(?:\s|:|,|$)", raw, flags=re.IGNORECASE):
            frame_type = "TEL_TEXT"
        # Values are deliberately token-sized; free-form serial text is never executed.
        pairs = re.findall(r"([A-Za-z][A-Za-z0-9_.-]*)\s*[=:]\s*([^\s,;|]+)", body)
        source = {_norm_key(key): value for key, value in pairs}

        # Some existing EMG sketches print "EMG_RMS_MV 0.432" without ':' or '='.
        if not source:
            legacy = re.search(
                r"\bEMG_RMS_MV\b\s*[, ]\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                body,
                flags=re.IGNORECASE,
            )
            if legacy:
                source = {"emg_rms_mv": legacy.group(1)}

    if not source:
        return {}

    normalized: Dict[str, Any] = {
        "received_at": utc_timestamp(), "raw": raw[:500], "_frame_type": frame_type,
    }
    for key, value in source.items():
        key = _norm_key(key)
        if key in SYSTEM_STATE_KEYS:
            state = str(value or "").strip().upper()
            if state in SYSTEM_STATES:
                normalized["system_state"] = state
        elif key in THERAPY_RUNNING_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["therapy_running"] = parsed_bool
        elif key in MODE_KEYS:
            mode = str(value or "").strip().upper()
            if mode in SELECTED_MODES:
                normalized["selected_mode"] = mode
        elif key in CURRENT_CMD_MA_KEYS:
            number = _float(value)
            if number is not None:
                normalized["current_cmd_ma"] = number
        elif key in CURRENT_CMD_A_KEYS:
            number = _float(value)
            if number is not None:
                normalized["current_cmd_ma"] = number * 1000.0
        elif key in CURRENT_SET_KEYS:
            number = _float(value)
            if number is not None:
                normalized["current_set_ma"] = number
        elif key in ANGLE_KEYS:
            number = _float(value)
            if number is not None:
                normalized["angle_deg"] = number
        elif key in ANGLE_TARGET_KEYS:
            number = _float(value)
            if number is not None:
                normalized["angle_target_deg"] = number
        elif key in PWM_COMMAND_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 100.0:
                normalized["pwm_command_pct"] = number
        elif key in PWM_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 100.0:
                normalized["pwm_pct"] = number
        elif key in PWM_RAW_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 255.0:
                normalized["pwm_pct"] = number * 100.0 / 255.0
        elif key in FATIGUE_SCORE_KEYS:
            number = _float(value)
            if number is not None:
                if number > 1.0:
                    number /= 100.0
                normalized["fatigue_score"] = max(0.0, min(1.0, number))
        elif key in FATIGUE_STATE_KEYS:
            normalized["fatigue_state"] = normalize_fatigue_state(value)
            if key == "fatigue":
                number = _float(value)
                if number is not None:
                    if number > 1.0:
                        number /= 100.0
                    normalized["fatigue_score"] = max(0.0, min(1.0, number))
        elif key in FATIGUE_FLAG_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["fatigue_flag"] = parsed_bool
        elif key in FATIGUE_COUNT_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 4294967295.0 and number.is_integer():
                normalized["fatigue_count"] = int(number)
        elif key in FATIGUE_THRESHOLD_KEYS:
            number = _float(value)
            if number is not None:
                if number > 1.0:
                    number /= 100.0
                normalized["fatigue_threshold"] = max(0.0, min(1.0, number))
        elif key in EMG_KEYS:
            number = _float(value)
            if number is not None:
                normalized["emg_rms_mv"] = max(0.0, number)
        elif key in EMG_MAV_KEYS:
            number = _float(value)
            if number is not None:
                normalized["emg_mav_mv"] = max(0.0, number)
        elif key in MAV_RATIO_KEYS:
            number = _float(value)
            if number is not None:
                normalized["mav_ratio"] = max(0.0, number)
        elif key in CLIPPING_PERCENT_KEYS:
            number = _float(value)
            if number is not None:
                normalized["clipping_percent_1s"] = max(0.0, min(100.0, number))
        elif key in EMG_ERROR_FLAGS_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 4294967295.0 and number.is_integer():
                normalized["emg_error_flags"] = int(number)
        elif key in QUALITY_KEYS:
            normalized["signal_quality"] = str(value).strip().upper()[:24]
        elif key in PHASE_KEYS:
            normalized["phase"] = str(value).strip().upper()[:32]
        elif key in OUTPUT_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["output_active"] = parsed_bool
        elif key in STOP_REASON_KEYS:
            normalized["stop_reason"] = str(value).strip().upper()[:48]
        elif key in FAULT_KEYS:
            normalized["fault"] = str(value).strip().upper()[:48]
        elif key in EMERGENCY_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["emergency"] = parsed_bool
        elif key in EMERGENCY_SOURCE_KEYS:
            normalized["emergency_source"] = str(value).strip().upper()[:24]
        elif key in PULSE_WIDTH_KEYS:
            number = _float(value)
            if number is not None:
                normalized["pulse_width_us"] = max(0.0, number)
        elif key in FREQUENCY_SET_KEYS:
            number = _float(value)
            if number is not None:
                normalized["frequency_set_hz"] = max(0.0, number)
        elif key in FREQUENCY_OUTPUT_KEYS:
            number = _float(value)
            if number is not None:
                normalized["frequency_output_hz"] = max(0.0, number)
        elif key in FREQUENCY_LEGACY_KEYS:
            number = _float(value)
            if number is not None:
                normalized["frequency_set_hz"] = max(0.0, number)
                normalized["frequency_output_hz"] = max(0.0, number)
        elif key in SESSION_KEYS:
            session_id = str(value).strip()
            if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
                normalized["session_id"] = session_id
        elif key in MCU_STATUS_KEYS:
            normalized["mcu_status"] = str(value).strip().upper()[:24]
        elif key in EMG_STATUS_KEYS:
            normalized["emg_status"] = str(value).strip().upper()[:24]
        elif key in IMU_A_STATUS_KEYS:
            normalized["imu_a_status"] = str(value).strip().upper()[:24]
        elif key in IMU_B_STATUS_KEYS:
            normalized["imu_b_status"] = str(value).strip().upper()[:24]
        elif key in IMU_A_ANGLE_KEYS:
            number = _float(value)
            if number is not None:
                normalized["imu_a_angle_deg"] = number
        elif key in IMU_B_ANGLE_KEYS:
            number = _float(value)
            if number is not None:
                normalized["imu_b_angle_deg"] = number
        elif key in ANGLE_ERROR_KEYS:
            number = _float(value)
            if number is not None:
                normalized["angle_error_deg"] = number
        elif key in DELTA_ERROR_KEYS:
            number = _float(value)
            if number is not None:
                normalized["delta_error_deg"] = number
        elif key in IMU_ZERO_OFFSET_KEYS:
            number = _float(value)
            if number is not None:
                normalized["imu_zero_offset_deg"] = number
        elif key in FUZZY_PWM_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 100.0:
                normalized["fuzzy_pwm_pct"] = number
        elif key in INTENT_STATE_KEYS:
            normalized["intent_state"] = str(value).strip().upper()[:24]
        elif key in INTENT_SCORE_KEYS:
            number = _float(value)
            if number is not None:
                if number > 1.0:
                    number /= 100.0
                normalized["intent_score"] = max(0.0, min(1.0, number))
        elif key in MCP4725_STATUS_KEYS:
            normalized["mcp4725_status"] = str(value).strip().upper()[:24]
        elif key in HBRIDGE_STATUS_KEYS:
            ready = _bool(value)
            normalized["hbridge_status"] = ("READY" if ready else "NOT_READY") if ready is not None else str(value).strip().upper()[:24]
        elif key in DAC_RAW_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 4095.0:
                normalized["dac_raw"] = int(round(number))
        elif key in DAC_VOLTAGE_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 10.0:
                normalized["dac_voltage_v"] = number
        elif key in FES_STATUS_KEYS:
            normalized["fes_status"] = str(value).strip().upper()[:24]
        elif key in START_BLOCK_KEYS:
            normalized["start_block"] = str(value).strip().upper()[:32]
        elif key in ANGLE_CAL_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["angle_calibrated"] = parsed_bool
        elif key in EMG_CAL_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["emg_calibrated"] = parsed_bool
        elif key in FSM_STATE_KEYS:
            normalized["fsm_state"] = raw_fsm_state(value)
        elif key in MVC_VALUE_KEYS:
            number = _float(value)
            if number is not None:
                normalized["mvc_value_mv"] = max(0.0, number)
        elif key in MVC_READY_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["mvc_ready"] = parsed_bool
        elif key in ACTIVE_DURATION_KEYS:
            number = _float(value)
            if number is not None and number >= 0.0:
                normalized["active_duration_s"] = number
        elif key in REST_DURATION_KEYS:
            number = _float(value)
            if number is not None and number >= 0.0:
                normalized["rest_duration_s"] = number
        elif key in THERAPY_TIMER_MS_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 4294967295.0 and number.is_integer():
                normalized["therapy_timer_ms"] = int(number)
        elif key in STATE_REMAINING_MS_KEYS:
            number = _float(value)
            if number is not None and 0.0 <= number <= 4294967295.0 and number.is_integer():
                normalized["state_remaining_ms"] = int(number)

    telemetry_fields = {
        "current_cmd_ma", "current_set_ma", "angle_deg", "angle_target_deg", "pwm_pct",
        "pwm_command_pct", "pulse_width_us", "frequency_set_hz", "frequency_output_hz", "fatigue_score",
        "system_state", "therapy_running", "selected_mode",
        "fatigue_threshold", "fatigue_state", "fatigue_flag", "fatigue_count",
        "emg_rms_mv", "emg_mav_mv", "mav_ratio", "clipping_percent_1s",
        "emg_error_flags", "signal_quality",
        "phase", "output_active", "stop_reason", "fault", "emergency", "emergency_source",
        "imu_a_status", "imu_b_status", "imu_a_angle_deg", "imu_b_angle_deg",
        "angle_error_deg", "delta_error_deg", "fuzzy_pwm_pct", "intent_state", "intent_score",
        "mcp4725_status", "hbridge_status", "dac_raw", "dac_voltage_v", "fes_status", "start_block",
        "angle_calibrated", "emg_calibrated", "mcu_status", "emg_status",
        "fsm_state", "mvc_value_mv", "mvc_ready", "active_duration_s", "rest_duration_s",
        "therapy_timer_ms", "state_remaining_ms",
    }
    if not telemetry_fields.intersection(normalized):
        return {}
    return normalized


CONTROL_TELEMETRY_FIELDS = {
    "system_state",
    "therapy_running",
    "selected_mode",
    "fsm_state",
    "current_cmd_ma",
    "angle_deg",
    "signal_quality",
    "phase",
    "output_active",
    "fault",
}


def is_complete_control_telemetry(update: Mapping[str, Any]) -> bool:
    """Validate one atomic control telemetry frame for direct-serial operation."""

    if update.get("_frame_type") != "TEL" or not CONTROL_TELEMETRY_FIELDS.issubset(update):
        return False
    if "pwm_pct" not in update and "pwm_command_pct" not in update:
        return False
    current = update.get("current_cmd_ma")
    angle = update.get("angle_deg")
    signal_quality = str(update.get("signal_quality", "")).strip().upper()
    phase = str(update.get("phase", "")).strip().upper()
    system_state = str(update.get("system_state", "")).strip().upper()
    selected_mode = str(update.get("selected_mode", "")).strip().upper()
    return bool(
        isinstance(current, (int, float))
        and not isinstance(current, bool)
        and math.isfinite(float(current))
        and 0.0 <= float(current) <= 100.0
        and isinstance(angle, (int, float))
        and not isinstance(angle, bool)
        and math.isfinite(float(angle))
        and -180.0 <= float(angle) <= 180.0
        and signal_quality in {"GOOD", "BAIK", "OK", "VALID", "BAD", "POOR", "INVALID", "NOISY", "CLIPPING"}
        and bool(phase)
        and system_state in SYSTEM_STATES
        and selected_mode in SELECTED_MODES
        and isinstance(update.get("therapy_running"), bool)
        and bool(str(update.get("fsm_state", "")).strip())
        and str(update.get("fault", "")).strip()
        and isinstance(update.get("output_active"), bool)
    )


@dataclass
class Telemetry:
    received_at: str = ""
    session_id: str = ""
    mcu_status: str = ""
    emg_status: str = ""
    system_state: str = "SYSTEM_INIT"
    therapy_running: Optional[bool] = None
    selected_mode: str = "NONE"
    current_cmd_ma: Optional[float] = None
    current_set_ma: Optional[float] = None
    angle_deg: Optional[float] = None
    angle_target_deg: Optional[float] = None
    pwm_pct: Optional[float] = None
    pwm_command_pct: Optional[float] = None
    pulse_width_us: Optional[float] = None
    frequency_set_hz: Optional[float] = None
    frequency_output_hz: Optional[float] = None
    fatigue_score: Optional[float] = None
    fatigue_threshold: Optional[float] = None
    fatigue_state: str = "WAITING"
    fatigue_flag: Optional[bool] = None
    fatigue_count: Optional[int] = None
    emg_rms_mv: Optional[float] = None
    emg_mav_mv: Optional[float] = None
    mav_ratio: Optional[float] = None
    clipping_percent_1s: Optional[float] = None
    emg_error_flags: Optional[int] = None
    signal_quality: str = "WAITING"
    phase: str = "IDLE"
    output_active: Optional[bool] = None
    stop_reason: str = ""
    fault: str = ""
    emergency: Optional[bool] = None
    emergency_source: str = ""
    imu_a_status: str = "WAITING"
    imu_b_status: str = "WAITING"
    imu_a_angle_deg: Optional[float] = None
    imu_b_angle_deg: Optional[float] = None
    angle_error_deg: Optional[float] = None
    delta_error_deg: Optional[float] = None
    fuzzy_pwm_pct: Optional[float] = None
    intent_state: str = "WAITING"
    intent_score: Optional[float] = None
    mcp4725_status: str = "WAITING"
    hbridge_status: str = "WAITING"
    dac_raw: Optional[int] = None
    dac_voltage_v: Optional[float] = None
    fes_status: str = "WAITING"
    start_block: str = ""
    angle_calibrated: Optional[bool] = None
    emg_calibrated: Optional[bool] = None
    fsm_state: str = "IDLE"
    mvc_value_mv: Optional[float] = None
    mvc_ready: Optional[bool] = None
    active_duration_s: Optional[float] = None
    rest_duration_s: Optional[float] = None
    therapy_timer_ms: Optional[int] = None
    state_remaining_ms: Optional[int] = None
    imu_zero_offset_deg: Optional[float] = None

    def merge(self, update: Mapping[str, Any]) -> None:
        allowed = {item.name for item in fields(self)}
        for key, value in update.items():
            if key in allowed:
                setattr(self, key, value)


class CSVLogger:
    FIELDNAMES = [
        "timestamp", "source", "connection", "session_id", "mode", "selected_mode",
        "current_set_ma", "current_cmd_ma",
        "angle_target_deg", "angle_deg", "pwm_command_pct", "pwm_pct",
        "pulse_width_us", "frequency_set_hz", "frequency_output_hz", "fatigue_score", "fatigue_threshold",
        "fatigue_state", "fatigue_flag", "fatigue_count", "emg_rms_mv", "emg_mav_mv", "mav_ratio",
        "clipping_percent_1s", "emg_error_flags",
        "signal_quality", "phase", "output_active",
        "stop_reason", "fault", "emergency", "emergency_source", "imu_a_status", "imu_b_status",
        "imu_a_angle_deg", "imu_b_angle_deg", "imu_zero_offset_deg", "angle_error_deg", "delta_error_deg",
        "intent_state", "intent_score", "mcp4725_status", "hbridge_status", "dac_raw", "dac_voltage_v",
        "fes_status", "start_block", "angle_calibrated", "emg_calibrated", "fsm_state",
        "mvc_value_mv", "mvc_ready", "active_duration_s", "rest_duration_s",
        "therapy_timer_ms", "state_remaining_ms", "session_time_s", "system_state", "therapy_running",
    ]

    def __init__(self) -> None:
        self._file: Optional[Any] = None
        self._writer: Optional[csv.DictWriter] = None
        self._lock = threading.Lock()
        self.path: Optional[str] = None

    @property
    def active(self) -> bool:
        return self._file is not None

    def start(self, path: str) -> None:
        self.stop()
        file_obj = open(path, "w", newline="", encoding="utf-8")
        writer = csv.DictWriter(file_obj, fieldnames=self.FIELDNAMES)
        writer.writeheader()
        file_obj.flush()
        with self._lock:
            self._file = file_obj
            self._writer = writer
            self.path = os.path.abspath(path)

    def log(
        self,
        telemetry: Telemetry,
        source: str,
        connection: str,
        mode: str,
        session_id: Optional[str] = None,
        session_time_s: Optional[Union[int, str]] = None,
    ) -> None:
        with self._lock:
            if self._file is None or self._writer is None:
                return
            snapshot = asdict(telemetry)
            resolved_session_id = session_id if session_id is not None else (snapshot.get("session_id") or "")
            resolved_session_time = str(session_time_s) if session_time_s is not None else ""

            row = {
                "timestamp": snapshot.get("received_at") or utc_timestamp(),
                "source": source,
                "connection": connection,
                "session_id": resolved_session_id,
                "mode": mode,
                "selected_mode": snapshot.get("selected_mode") or "",
                "current_set_ma": snapshot.get("current_set_ma"),
                "current_cmd_ma": snapshot.get("current_cmd_ma"),
                "angle_target_deg": snapshot.get("angle_target_deg"),
                "angle_deg": snapshot.get("angle_deg"),
                "pwm_command_pct": snapshot.get("pwm_command_pct"),
                "pwm_pct": snapshot.get("pwm_pct"),
                "pulse_width_us": snapshot.get("pulse_width_us"),
                "frequency_set_hz": snapshot.get("frequency_set_hz"),
                "frequency_output_hz": snapshot.get("frequency_output_hz"),
                "fatigue_score": snapshot.get("fatigue_score"),
                "fatigue_threshold": snapshot.get("fatigue_threshold"),
                "fatigue_state": snapshot.get("fatigue_state"),
                "fatigue_flag": snapshot.get("fatigue_flag"),
                "fatigue_count": snapshot.get("fatigue_count"),
                "emg_rms_mv": snapshot.get("emg_rms_mv"),
                "emg_mav_mv": snapshot.get("emg_mav_mv"),
                "mav_ratio": snapshot.get("mav_ratio"),
                "clipping_percent_1s": snapshot.get("clipping_percent_1s"),
                "emg_error_flags": snapshot.get("emg_error_flags"),
                "signal_quality": snapshot.get("signal_quality"),
                "phase": snapshot.get("phase"),
                "output_active": snapshot.get("output_active"),
                "stop_reason": snapshot.get("stop_reason"),
                "fault": snapshot.get("fault"),
                "emergency": snapshot.get("emergency"),
                "emergency_source": snapshot.get("emergency_source"),
                "imu_a_status": snapshot.get("imu_a_status"),
                "imu_b_status": snapshot.get("imu_b_status"),
                "imu_a_angle_deg": snapshot.get("imu_a_angle_deg"),
                "imu_b_angle_deg": snapshot.get("imu_b_angle_deg"),
                "imu_zero_offset_deg": snapshot.get("imu_zero_offset_deg"),
                "angle_error_deg": snapshot.get("angle_error_deg"),
                "delta_error_deg": snapshot.get("delta_error_deg"),
                "intent_state": snapshot.get("intent_state"),
                "intent_score": snapshot.get("intent_score"),
                "mcp4725_status": snapshot.get("mcp4725_status"),
                "hbridge_status": snapshot.get("hbridge_status"),
                "dac_raw": snapshot.get("dac_raw"),
                "dac_voltage_v": snapshot.get("dac_voltage_v"),
                "fes_status": snapshot.get("fes_status"),
                "start_block": snapshot.get("start_block"),
                "angle_calibrated": snapshot.get("angle_calibrated"),
                "emg_calibrated": snapshot.get("emg_calibrated"),
                "fsm_state": snapshot.get("fsm_state"),
                "mvc_value_mv": snapshot.get("mvc_value_mv"),
                "mvc_ready": snapshot.get("mvc_ready"),
                "active_duration_s": snapshot.get("active_duration_s"),
                "rest_duration_s": snapshot.get("rest_duration_s"),
                "therapy_timer_ms": snapshot.get("therapy_timer_ms"),
                "state_remaining_ms": snapshot.get("state_remaining_ms"),
                "session_time_s": resolved_session_time,
                "system_state": snapshot.get("system_state") or "",
                "therapy_running": snapshot.get("therapy_running"),
            }
            self._writer.writerow(row)
            self._file.flush()

    def stop(self) -> None:
        with self._lock:
            file_obj = self._file
            self._file = None
            self._writer = None
            self.path = None
        if file_obj is not None:
            file_obj.close()


def _windows_registry_com_ports() -> list[str]:
    """Ambil COM port langsung dari Registry Windows sebagai fallback.

    Ini membuat tombol Scan tetap dapat menemukan COM3/COMx ketika
    serial.tools.list_ports gagal/tidak tersedia, selama Windows sendiri
    sudah mendaftarkan perangkat di Device Manager.
    """
    if winreg is None or os.name != "nt":
        return []

    ports: list[str] = []
    key_path = r"HARDWARE\DEVICEMAP\SERIALCOMM"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            index = 0
            while True:
                try:
                    _name, value, _kind = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                port = str(value).strip().upper()
                if re.fullmatch(r"COM\d+", port) and port not in ports:
                    ports.append(port)
    except OSError:
        return []

    def port_number(value: str) -> int:
        match = re.search(r"(\d+)$", value)
        return int(match.group(1)) if match else 9999

    ports.sort(key=port_number)
    return ports


class SerialManager:
    """Own the serial/demo worker and expose queue-based, Tk-safe events."""

    def __init__(self, hardware_control_requested: bool = True) -> None:
        self.events: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.hardware_control_requested = True
        self.port_open = False
        self.connected = False
        self._session_id = ""
        self._reset_estop_requested = False
        self.connection_kind = "DISCONNECTED"
        self.port_name = ""
        self.estop_latched = False
        self._serial: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._demo_state: Dict[str, Any] = {
            "output": False,
            "mode": "NONE",
            "current_target": 10.0,
            "pwm_target": PROJECT_PWM_DEFAULT_US,
            "angle_target": PROJECT_DEFAULT_TARGET_ANGLE_DEG,
            "session_started": None,
            "frequency_target": PROJECT_FIXED_FREQUENCY_HZ,
            "active_duration": 5.0,
            "rest_duration": 5.0,
            "angle_calibrated": True,
            "mvc_ready": True,
            "mvc_value_mv": 1.20,
        }

    def state(self) -> Dict[str, Any]:
        with self._state_lock:
            return {
                "connected": self.connected,
                "port_open": self.port_open,
                "telemetry_live": self.connected,
                "session_id": self._session_id,
                "kind": self.connection_kind,
                "port": self.port_name,
                "estop": self.estop_latched,
                "can_control": self.can_control(),
                "hardware_requested": self.hardware_control_requested,
            }

    @property
    def session_id(self) -> str:
        with self._state_lock:
            return self._session_id

    def can_control(self) -> bool:
        if self.estop_latched:
            return False
        return bool(self.connected and self.connection_kind in {"SERIAL", "DEMO"})

    def _status(self, message: str) -> None:
        payload = self.state()
        payload["message"] = message
        self.events.put(("status", payload))

    def connect_serial(self, port: str, baud: int) -> Tuple[bool, str]:
        port = port.strip()
        if not port:
            return False, "Isi nama port terlebih dahulu (contoh: COM6)."
        if serial is None:
            return False, "pyserial belum terpasang. Jalankan: pip install pyserial"
        self.disconnect()
        try:
            serial_obj = serial.Serial(port=port, baudrate=baud, timeout=0.25, write_timeout=0.5)
            reset_input = getattr(serial_obj, "reset_input_buffer", None)
            if callable(reset_input):
                reset_input()
        except Exception as exc:  # pyserial exposes several backend-specific exceptions
            return False, f"Tidak dapat membuka {port}: {exc}"

        with self._state_lock:
            self._serial = serial_obj
            self.port_open = True
            self.connected = False
            self._session_id = "DIRECT"
            self.connection_kind = "SERIAL"
            self.port_name = port
        worker_stop = threading.Event()
        self._stop_event = worker_stop
        self._thread = threading.Thread(
            target=self._serial_loop, args=(worker_stop,), name="stimulator-serial", daemon=True,
        )
        self._thread.start()
        self._status(f"Port {port} terbuka; menunggu telemetry STM32.")
        return True, f"Port {port} terbuka; menunggu telemetry STM32"

    def start_demo(self) -> None:
        self.disconnect()
        with self._state_lock:
            self.port_open = False
            self.connected = True
            self._session_id = "DEMO"
            self._reset_estop_requested = False
            self.connection_kind = "DEMO"
            self.port_name = "SIMULATOR"
            self.estop_latched = False
            self._demo_state.update(
                output=False,
                mode="IDLE",
                session_started=None,
                angle_calibrated=True,
                mvc_ready=True,
                mvc_value_mv=1.20,
            )
        worker_stop = threading.Event()
        self._stop_event = worker_stop
        self._thread = threading.Thread(
            target=self._demo_loop, args=(worker_stop,), name="stimulator-demo", daemon=True,
        )
        self._thread.start()
        self._status("Mode demo aktif; tidak ada keluaran ke hardware.")

    def disconnect(self) -> None:
        self._stop_event.set()
        serial_obj = self._serial
        if serial_obj is not None and self.connection_kind == "SERIAL" and self.port_open:
            # Closing a link makes the physical output unverifiable. Send both the
            # V1 and legacy de-energizing forms before the port is closed.
            self._send_safety_stop_wire(
                include_estop=not (self.estop_latched and self._reset_estop_requested),
                reason="disconnect_after_reset" if self._reset_estop_requested else "disconnect",
            )
        self._serial = None
        if serial_obj is not None:
            try:
                serial_obj.close()
            except Exception:
                pass
        thread = self._thread
        self._thread = None
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=1.0)
        was_active = self.connected or self.port_open
        with self._state_lock:
            self.connected = False
            self.port_open = False
            self._session_id = ""
            self.connection_kind = "DISCONNECTED"
            self.port_name = ""
        if was_active:
            self._status("Koneksi dihentikan.")

    def _serial_loop(self, stop_event: threading.Event) -> None:
        last_valid: Optional[float] = None
        last_diagnostic = 0.0

        def report_diagnostic(message: str) -> None:
            nonlocal last_diagnostic
            now = time.monotonic()
            if now - last_diagnostic >= SERIAL_DIAGNOSTIC_INTERVAL_SECONDS:
                last_diagnostic = now
                self.events.put(("error", message))

        def expire_telemetry_if_needed(now: float) -> None:
            if last_valid is None or now - last_valid <= DATA_STALE_SECONDS:
                return
            with self._state_lock:
                was_connected = self.connected
                self.connected = False
            if was_connected:
                self._status("Telemetry STM32 timeout; port tetap terbuka.")

        while not stop_event.is_set():
            serial_obj = self._serial
            if serial_obj is None:
                break
            try:
                raw = serial_obj.read_until(expected=b"\n", size=SERIAL_FRAME_MAX_BYTES)
            except Exception as exc:
                self.events.put(("error", f"Kesalahan serial: {exc}"))
                break
            now = time.monotonic()
            if not raw:
                expire_telemetry_if_needed(now)
                continue
            if len(raw) >= SERIAL_FRAME_MAX_BYTES and not raw.endswith(b"\n"):
                report_diagnostic(
                    f"Telemetry frame exceeded {SERIAL_FRAME_MAX_BYTES}-byte receive limit / truncated."
                )
                expire_telemetry_if_needed(now)
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                expire_telemetry_if_needed(now)
                continue
            if line.lstrip().startswith("{"):
                try:
                    decoded = json.loads(line)
                except (json.JSONDecodeError, TypeError) as exc:
                    report_diagnostic(f"Telemetry JSON malformed; frame rejected ({exc.msg if isinstance(exc, json.JSONDecodeError) else exc}).")
                    expire_telemetry_if_needed(now)
                    continue
                if not isinstance(decoded, Mapping):
                    report_diagnostic("Telemetry JSON malformed; object expected.")
                    expire_telemetry_if_needed(now)
                    continue
            try:
                telemetry = parse_telemetry_line(line)
            except Exception as exc:
                report_diagnostic(f"Telemetry parser error; frame rejected ({type(exc).__name__}).")
                expire_telemetry_if_needed(now)
                continue
            if not telemetry:
                if re.match(r"^\s*(?:TEL|TELEMETRY)(?:\s|:|,|$)", line, flags=re.IGNORECASE):
                    report_diagnostic("Telemetry TEL malformed; frame rejected.")
                expire_telemetry_if_needed(now)
                continue

            control_frame = is_complete_control_telemetry(telemetry)
            if telemetry.get("_frame_type") == "TEL" and not control_frame:
                report_diagnostic("Telemetry TEL incomplete; control connection not confirmed.")
            if control_frame:
                last_valid = now
                with self._state_lock:
                    newly_connected = not self.connected
                    self.connected = True
                if newly_connected:
                    self._status("Telemetry STM32 terkonfirmasi; MCU ONLINE.")
            self.events.put(("telemetry", telemetry))
            expire_telemetry_if_needed(now)
        if not stop_event.is_set():
            serial_obj = self._serial
            self._serial = None
            if serial_obj is not None:
                try:
                    serial_obj.close()
                except Exception:
                    pass
            with self._state_lock:
                self.connected = False
                self.port_open = False
                self._session_id = ""
                self.connection_kind = "DISCONNECTED"
                self.port_name = ""
            self._status("Koneksi serial terputus.")

    def _demo_loop(self, stop_event: threading.Event) -> None:
        started = time.monotonic()
        current = angle = pwm = emg = 0.0
        previous_angle_error: Optional[float] = None
        while not stop_event.wait(0.10):
            now = time.monotonic()
            with self._state_lock:
                demo = dict(self._demo_state)
                estop = self.estop_latched

            session_started = demo.get("session_started")
            running = bool(demo.get("output")) and not estop and session_started is not None
            active_s = max(0.1, float(demo.get("active_duration", 5.0)))
            rest_s = max(0.1, float(demo.get("rest_duration", 5.0)))
            cycle = active_s + rest_s
            cycle_pos = ((now - float(session_started)) % cycle) if running else 0.0
            fsm_state = "KONTRAKSI" if running and cycle_pos < active_s else "RELAKSASI" if running else "IDLE"
            output = running and fsm_state == "KONTRAKSI"
            state_duration_s = active_s if fsm_state == "KONTRAKSI" else rest_s
            state_elapsed_s = cycle_pos if fsm_state == "KONTRAKSI" else max(0.0, cycle_pos - active_s)

            target_current = float(demo.get("current_target", PROJECT_FIXED_CURRENT_MA)) if output else 0.0
            target_pwm = float(demo.get("pwm_target", PROJECT_PWM_DEFAULT_US)) if output else 0.0
            frequency = float(demo.get("frequency_target", PROJECT_FIXED_FREQUENCY_HZ))
            angle_target = float(demo.get("angle_target", PROJECT_DEFAULT_TARGET_ANGLE_DEG))

            current += (target_current - current) * 0.15
            pwm += (target_pwm - pwm) * 0.20
            if output:
                pwm_drive_pct = pwm_us_to_pct(target_pwm)
                movement_target = min(angle_target, max(2.0, pwm_drive_pct * 1.1))
            else:
                movement_target = max(2.0, angle * 0.96)
            angle += (movement_target - angle) * 0.05

            emg_base = 0.12 + current * 0.025 if fsm_state == "KONTRAKSI" else 0.05
            emg = max(0.0, emg_base + 0.07 * math.sin((now - started) * 5.0) + random.uniform(-0.02, 0.02))
            angle_error_now = angle_target - angle
            delta_error_now = 0.0 if previous_angle_error is None else angle_error_now - previous_angle_error
            previous_angle_error = angle_error_now
            telemetry = {
                "_frame_type": "TEL",
                "session_id": "DEMO",
                "received_at": utc_timestamp(),
                "system_state": "SYSTEM_EMERGENCY" if estop else "SYSTEM_THERAPY" if running else "SYSTEM_READY_TO_START",
                "therapy_running": running,
                "selected_mode": normalize_selected_mode(demo.get("mode")),
                "current_cmd_ma": round(max(0.0, current), 3),
                "current_set_ma": round(float(demo.get("current_target", PROJECT_FIXED_CURRENT_MA)), 3),
                "angle_deg": round(max(0.0, angle + random.uniform(-0.2, 0.2)), 2),
                "angle_target_deg": round(angle_target, 2),
                "pulse_width_us": round(max(0.0, pwm), 1),
                "pwm_pct": round(pwm_us_to_pct(max(PROJECT_PWM_MIN_US, pwm)) if pwm > 0.0 else 0.0, 2),
                "pwm_command_pct": round(pwm_us_to_pct(float(demo.get("pwm_target", PROJECT_PWM_DEFAULT_US))), 2),
                "emg_rms_mv": round(emg, 4),
                "emg_mav_mv": round(emg * 0.90, 4),
                "mav_ratio": round((emg * 0.90) / max(0.001, float(demo.get("mvc_value_mv", 1.20))), 4),
                "fatigue_flag": False,
                "fatigue_count": 0,
                "clipping_percent_1s": 0.0,
                "emg_error_flags": 0,
                "signal_quality": "BAIK",
                "phase": fsm_state,
                "fsm_state": fsm_state,
                "output_active": output,
                "therapy_timer_ms": int(round(state_elapsed_s * 1000.0)) if running else 0,
                "state_remaining_ms": int(round(max(0.0, state_duration_s - state_elapsed_s) * 1000.0)) if running else 0,
                "stop_reason": "",
                "fault": "NONE",
                "emergency": bool(estop),
                "emergency_source": "GUI" if estop else "NONE",
                "frequency_set_hz": frequency,
                "frequency_output_hz": frequency if output else 0.0,
                "active_duration_s": active_s,
                "rest_duration_s": rest_s,
                "imu_a_status": "OK",
                "imu_b_status": "OK",
                "imu_a_angle_deg": round(10.0 + angle * 0.35, 2),
                "imu_b_angle_deg": round(10.0 - angle * 0.65, 2),
                "angle_error_deg": round(angle_error_now, 2),
                "delta_error_deg": round(delta_error_now, 2),
                "mcp4725_status": "OK",
                "hbridge_status": "READY",  # mengikuti status MCP4725 seperti firmware
                "dac_raw": int(round(max(0.0, min(4095.0, target_current / PROJECT_CURRENT_MAX_MA * 4095.0)))),
                "dac_voltage_v": round(max(0.0, min(3.3, target_current / PROJECT_CURRENT_MAX_MA * 3.3)), 3),
                "fes_status": "ACTIVE" if output else "READY" if running else "OFF",
                "start_block": "BUSY" if running else "OK",
                "angle_calibrated": bool(demo.get("angle_calibrated", True)),
                "mvc_ready": bool(demo.get("mvc_ready", True)),
                "mvc_value_mv": float(demo.get("mvc_value_mv", 1.20)),
                "mcu_status": "ONLINE",
                "emg_status": "READY",
            }
            self.events.put(("telemetry", telemetry))

    def _send_raw(self, payload: Mapping[str, Any]) -> Tuple[bool, str]:
        serial_obj = self._serial
        if self.connection_kind != "SERIAL" or serial_obj is None or not self.connected:
            return False, "Serial tidak terhubung."
        wire = (json.dumps(dict(payload), separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self._write_lock:
                serial_obj.write(wire)
                serial_obj.flush()
        except Exception as exc:
            return False, f"Gagal mengirim perintah: {exc}"
        return True, "Perintah terkirim."

    def send_heartbeat(self) -> Tuple[bool, str]:
        """Send the V1 keepalive; callers must invoke this from the Tk loop."""

        if not (
            self.connection_kind == "SERIAL"
            and self.connected
            and not self.estop_latched
        ):
            return False, "Heartbeat tidak diperlukan atau gate kontrol belum siap."
        return self._send_raw({
            "type": "HB",
            "pc_monotonic_ms": int(time.monotonic() * 1000),
        })

    def _send_safety_stop_wire(
        self, *, include_estop: bool, reason: str = "safety_stop",
    ) -> Tuple[bool, str]:
        """Send redundant de-energizing forms without conflating STOP and E-STOP.

        A routine STOP must not latch an MCU emergency state. Disconnect and
        E-STOP add the explicit latching forms because physical output can no
        longer be trusted. Every frame in this method can only turn output off.
        """

        serial_obj = self._serial
        if self.connection_kind != "SERIAL" or serial_obj is None or not self.port_open:
            return False, "Serial tidak terhubung; E-STOP lokal tetap dikunci."
        reason_text = re.sub(r"[^A-Za-z0-9_.-]", "_", str(reason))[:48] or "safety_stop"
        stop_payload: Dict[str, Any] = {"type": "CMD", "cmd": "STOP_THERAPY", "reason": reason_text}
        frames = [
            b"!STOP\n",
            (json.dumps(
                stop_payload,
                separators=(",", ":"),
            ) + "\n").encode("utf-8"),
            b"STOP\n",
            b"STIM_OFF\n",
        ]
        if include_estop:
            estop_payload: Dict[str, Any] = {"type": "CMD", "cmd": "ESTOP", "reason": reason_text}
            frames.extend([
                (json.dumps(
                    estop_payload,
                    separators=(",", ":"),
                ) + "\n").encode("utf-8"),
                b"EMERGENCY_STOP\n",
            ])
        wire = b"".join(frames)
        try:
            with self._write_lock:
                serial_obj.write(wire)
                serial_obj.flush()
        except Exception as exc:
            return False, f"Gagal mengirim safety stop: {exc}"
        stop_kind = "E-STOP" if include_estop else "STOP"
        return True, f"{stop_kind} redundan dikirim ke perangkat."

    def send_command(self, command: str, *, safety: bool = False, **parameters: Any) -> Tuple[bool, str]:
        command = command.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", command):
            return False, "Nama perintah tidak valid."
        deenergizing_commands = {"STOP_THERAPY", "ESTOP"}
        if safety and command not in deenergizing_commands:
            return False, "Flag safety hanya boleh untuk perintah yang mematikan keluaran."
        if self.connection_kind == "DEMO" and self.connected:
            with self._state_lock:
                if self.estop_latched and command not in {"ESTOP", "STOP", "STOP_THERAPY", "RESET_ESTOP"}:
                    return False, "E-STOP masih terkunci."
                if command == "CALIBRATE_ANGLE":
                    self._demo_state.update(angle_calibrated=True)
                elif command == "CALIBRATE_EMG":
                    self._demo_state.update(mvc_ready=False, mvc_value_mv=0.0)
                elif command == "CALIBRATE_ALL":
                    self._demo_state.update(angle_calibrated=True, emg_calibrated=True)
                elif command == "START_AUTO":
                    self._demo_state.update(
                        output=True,
                        mode="AUTO",
                        current_target=float(parameters.get("current_cmd_ma", parameters.get("current_ma", self._demo_state["current_target"]))),
                        frequency_target=float(parameters.get("frequency_set_hz", parameters.get("frequency_hz", self._demo_state["frequency_target"]))),
                        pwm_target=float(parameters.get(
                            "pulse_width_us",
                            pwm_pct_to_us(float(parameters["pwm_pct"])) if "pwm_pct" in parameters else self._demo_state["pwm_target"],
                        )),
                        angle_target=float(parameters.get("angle_target_deg", PROJECT_DEFAULT_TARGET_ANGLE_DEG)),
                        # ACTIVE/REST Auto ditentukan oleh logika/FSM MCU, bukan input GUI.
                        session_started=time.monotonic(),
                    )
                elif command in {"SET_MANUAL", "OUTPUT_ON"}:
                    output_requested = bool(parameters.get("output", True))
                    self._demo_state.update(
                        output=output_requested,
                        mode="MANUAL",
                        current_target=float(parameters.get("current_cmd_ma", parameters.get("current_ma", self._demo_state["current_target"]))),
                        frequency_target=float(parameters.get("frequency_set_hz", parameters.get("frequency_hz", self._demo_state["frequency_target"]))),
                        pwm_target=float(parameters.get(
                            "pulse_width_us",
                            pwm_pct_to_us(float(parameters["pwm_pct"])) if "pwm_pct" in parameters else self._demo_state["pwm_target"],
                        )),
                        active_duration=float(parameters.get("active_duration_s", self._demo_state["active_duration"])),
                        rest_duration=float(parameters.get("rest_duration_s", self._demo_state["rest_duration"])),
                        session_started=time.monotonic() if output_requested else None,
                    )
                elif command == "CAPTURE_MVC":
                    self._demo_state.update(mvc_ready=True, mvc_value_mv=1.20)
                elif command == "CALIBRATE_ANGLE":
                    self._demo_state.update(angle_calibrated=True)
                elif command in {"STOP_THERAPY", "STOP", "STOP_AUTO", "OUTPUT_OFF", "ESTOP"}:
                    self._demo_state.update(output=False, session_started=None)
            return True, f"Demo: {command} diterapkan."

        if not safety and not self.can_control():
            return False, "Kontrol belum siap atau E-STOP masih terkunci."
        if safety and command in deenergizing_commands:
            return self._send_safety_stop_wire(
                include_estop=command == "ESTOP",
                reason=str(parameters.get("reason", command.lower())),
            )
        return self._send_raw({
            "type": "CMD",
            "cmd": command,
            **parameters,
        })

    def emergency_stop(self, reason: str = "operator") -> Tuple[bool, str]:
        with self._state_lock:
            self.estop_latched = True
            self._reset_estop_requested = False
            if self.connection_kind == "DEMO":
                self._demo_state.update(output=False, session_started=None)
        # STOP safety commands are allowed even in monitor-only mode. This does not
        # unlock any energizing command and is safe to attempt if a serial link exists.
        if self.connection_kind == "SERIAL" and self.port_open:
            result = self._send_safety_stop_wire(include_estop=True, reason=reason)
        else:
            result = (True, "E-STOP lokal aktif.")
        self._status("E-STOP AKTIF - keluaran dikunci.")
        return result

    def reset_estop(self) -> Tuple[bool, str]:
        if self.connection_kind == "SERIAL":
            if not self.connected:
                return False, "Reset E-STOP memerlukan koneksi serial."
            sent, message = self._send_raw({
                "type": "CMD", "cmd": "RESET_ESTOP",
            })
            if not sent:
                return False, message
            with self._state_lock:
                self._reset_estop_requested = True
            # Jangan buka latch lokal sebelum STM32 mengirim emergency=0.
            return True, "RESET_ESTOP dikirim; menunggu status aman dari STM32."

        with self._state_lock:
            self.estop_latched = False
            self._reset_estop_requested = False
        self._status("E-STOP demo di-reset; keluaran tetap OFF.")
        return True, "E-STOP di-reset."

    def confirm_estop_reset(self) -> None:
        with self._state_lock:
            self.estop_latched = False
            self._reset_estop_requested = False
        self._status("RESET E-STOP dikonfirmasi STM32; sistem kembali IDLE.")


if tk is not None:
    class MetricCard(tk.Frame):
        def __init__(self, parent: tk.Misc, title: str, unit: str, accent: str) -> None:
            super().__init__(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
            self.accent = accent
            self.title = title
            tk.Frame(self, bg=accent, width=3).pack(side="left", fill="y")
            body = tk.Frame(self, bg=COLORS["panel"])
            body.pack(fill="both", expand=True, padx=11, pady=8)
            tk.Label(body, text=title.upper(), bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(anchor="w")
            value_row = tk.Frame(body, bg=COLORS["panel"])
            value_row.pack(anchor="w", pady=(3, 0))
            self.value_label = tk.Label(value_row, text="--", bg=COLORS["panel"], fg=COLORS["text"],
                                        font=("Segoe UI Semibold", 18))
            self.value_label.pack(side="left")
            self.unit_label = tk.Label(value_row, text=f"  {unit}" if unit else "", bg=COLORS["panel"],
                                       fg=COLORS["muted"], font=("Segoe UI", 9))
            self.unit_label.pack(side="left", anchor="s", pady=(0, 2))

        def set(self, value: str, *, color: Optional[str] = None, unit: Optional[str] = None) -> None:
            self.value_label.configure(text=value, fg=color or COLORS["text"])
            if unit is not None:
                self.unit_label.configure(text=f"  {unit}" if unit else "")


    class EMGPlot(tk.Canvas):
        def __init__(self, parent: tk.Misc) -> None:
            super().__init__(parent, bg=COLORS["panel"], highlightthickness=0, height=250)
            self.values: "deque[float]" = deque(maxlen=180)
            self.bind("<Configure>", lambda _event: self.redraw())

        def add(self, value: Optional[float]) -> None:
            if value is None:
                return
            self.values.append(float(value))
            self.redraw()

        def redraw(self) -> None:
            self.delete("all")
            width = max(40, self.winfo_width())
            height = max(40, self.winfo_height())
            pad_left, pad_right, pad_top, pad_bottom = 48, 20, 20, 34
            chart_w = width - pad_left - pad_right
            chart_h = height - pad_top - pad_bottom
            if chart_w <= 0 or chart_h <= 0:
                return
            for index in range(5):
                y = pad_top + chart_h * index / 4
                self.create_line(pad_left, y, width - pad_right, y, fill=COLORS["line"])
            self.create_text(pad_left, height - 12, text="waktu", fill=COLORS["muted"],
                             font=("Segoe UI", 9), anchor="w")
            self.create_text(12, pad_top, text="mV", fill=COLORS["muted"],
                             font=("Segoe UI", 9), anchor="nw")
            if len(self.values) < 2:
                self.create_text(width / 2, height / 2, text="Menunggu data EMG...", fill=COLORS["muted"],
                                 font=("Segoe UI", 11))
                return
            values = list(self.values)
            upper = max(0.25, max(values) * 1.15)
            points = []
            denominator = max(1, self.values.maxlen - 1)
            start_slot = self.values.maxlen - len(values)
            for idx, value in enumerate(values):
                x = pad_left + chart_w * (start_slot + idx) / denominator
                y = pad_top + chart_h * (1.0 - max(0.0, min(upper, value)) / upper)
                points.extend((x, y))
            self.create_line(*points, fill=COLORS["cyan"], width=2, smooth=True)
            self.create_text(width - pad_right, pad_top + 2, text=f"skala 0–{upper:.2f} mV",
                             fill=COLORS["muted"], font=("Segoe UI", 9), anchor="ne")


    class StimulatorApp:
        def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
            self.root = root
            self.args = args
            self.manager = SerialManager(hardware_control_requested=True)
            self.logger = CSVLogger()
            self.telemetry = Telemetry()
            self._last_monitor_angle_error: Optional[float] = None
            self.current_page = "PREPARATION"
            self.selected_mode = "NONE"
            self.system_mode = "WAIT"
            self.auto_running = False
            self.last_any_telemetry_monotonic: Optional[float] = None
            self.last_telemetry_monotonic: Optional[float] = None
            self.data_stale = True
            self.stale_stop_sent = False
            self.session_started_at: Optional[float] = None
            self.session_elapsed_frozen_s: Optional[int] = None
            self.session_time_known: bool = False
            self.current_therapy_session_id: Optional[str] = None
            self.last_therapy_session_id: Optional[str] = None
            self._prev_therapy_running: Optional[bool] = None
            self.pending_mode: Optional[str] = None
            self.pending_start_deadline: Optional[float] = None
            self.pending_stop_deadline: Optional[float] = None
            self.pending_calibration: Optional[str] = None
            self.pending_calibration_label: str = ""
            self.pending_calibration_deadline: Optional[float] = None
            self.pending_reset_estop = False
            self.pending_reset_deadline: Optional[float] = None
            self.last_heartbeat_sent = 0.0
            self.estop_output_confirmed = False
            self.last_estop_retry = 0.0
            self.last_ui_control_state: Optional[bool] = None
            self.control_widgets: list[Any] = []
            self.nav_buttons: Dict[str, tk.Button] = {}
            self.pages: Dict[str, tk.Frame] = {}
            self.scroll_containers: Dict[str, Dict[str, Any]] = {}

            root.title(APP_NAME)
            root.geometry("1280x720")
            root.minsize(1040, 640)
            root.configure(bg=COLORS["bg"])
            root.grid_rowconfigure(0, weight=1)
            root.grid_columnconfigure(1, weight=1)
            try:
                root.state("zoomed")
            except tk.TclError:
                pass
            root.protocol("WM_DELETE_WINDOW", self.close)
            root.bind_all("<Escape>", lambda _event: self.emergency_stop())
            self._configure_ttk()
            self._build_layout()
            self.show_page("CAL")
            self._poll_events()

            if args.port:
                self.port_var.set(args.port)
                ok, message = self.manager.connect_serial(args.port, args.baud)
                if not ok:
                    self._set_status(message, COLORS["red"])
            else:
                # Jangan otomatis masuk Demo. Port hasil scan tetap dipilih dan
                # operator tinggal menekan Hubungkan untuk koneksi MCU nyata.
                if self.port_var.get().strip():
                    self._set_status(f"Port {self.port_var.get().strip()} terdeteksi; tekan Hubungkan.", COLORS["muted"])
                else:
                    self._set_status("Belum ada port serial; tekan Scan setelah MCU tersambung.", COLORS["muted"])

        def _configure_ttk(self) -> None:
            style = ttk.Style(self.root)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("TEntry", fieldbackground=COLORS["panel_2"], foreground=COLORS["text"],
                            insertcolor=COLORS["text"], bordercolor=COLORS["line"], padding=8)
            style.configure("TSpinbox", fieldbackground=COLORS["panel_2"], foreground=COLORS["text"],
                            arrowsize=14, bordercolor=COLORS["line"], padding=7)
            style.configure("Horizontal.TScale", background=COLORS["panel"], troughcolor=COLORS["panel_2"])
            style.configure(
                "Dark.Vertical.TScrollbar", background=COLORS["line"], troughcolor=COLORS["panel"],
                bordercolor=COLORS["panel"], arrowcolor=COLORS["muted"], relief="flat",
            )
            style.map("Dark.Vertical.TScrollbar", background=[("active", COLORS["muted"])])

        def _build_layout(self) -> None:
            sidebar_bg = COLORS["sidebar"]
            self.sidebar = tk.Frame(self.root, bg=sidebar_bg, width=218)
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar.grid_propagate(False)

            brand = tk.Frame(self.sidebar, bg=sidebar_bg)
            brand.pack(fill="x", padx=18, pady=(18, 14))
            tk.Label(brand, text="FES REHAB", bg=sidebar_bg, fg=COLORS["text"],
                     font=("Segoe UI Semibold", 15)).pack(anchor="w")
            tk.Label(brand, text="IMU · EMG · FSM · Safety", bg=sidebar_bg, fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

            tk.Label(self.sidebar, text="NAVIGASI", bg=sidebar_bg, fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=18, pady=(8, 6))
            nav_items = (
                ("CAL", "Persiapan Sensor"),
                ("AUTO", "Mode Auto"),
                ("MANUAL", "Mode Manual"),
                ("EMG", "Monitoring EMG"),
            )
            for key, label in nav_items:
                button = tk.Button(
                    self.sidebar, text=label, anchor="w", relief="flat", bd=0,
                    bg=sidebar_bg, fg=COLORS["muted"], activebackground=COLORS["panel_2"],
                    activeforeground=COLORS["white"], font=("Segoe UI Semibold", 10),
                    padx=14, pady=9, command=lambda page=key: self.show_page(page), cursor="hand2",
                )
                button.pack(fill="x", padx=8, pady=2)
                self.nav_buttons[key] = button

            safety = tk.Frame(self.sidebar, bg=sidebar_bg)
            safety.pack(side="bottom", fill="x", padx=14, pady=14)
            self.estop_button = tk.Button(
                safety, text="EMERGENCY STOP  [ESC]", command=self.emergency_stop,
                bg=COLORS["red_dark"], fg=COLORS["white"], activebackground=COLORS["red"],
                activeforeground=COLORS["white"], relief="flat", bd=0,
                font=("Segoe UI Semibold", 10), pady=11, cursor="hand2",
            )
            self.estop_button.pack(fill="x")
            self.reset_estop_button = tk.Button(
                safety, text="Reset E-STOP", command=self.reset_estop,
                bg=COLORS["panel_2"], fg=COLORS["muted"], activebackground=COLORS["line"],
                activeforeground=COLORS["text"], relief="flat", bd=0,
                font=("Segoe UI", 9), pady=8, cursor="hand2",
            )
            self.reset_estop_button.pack(fill="x", pady=(7, 0))

            connection = tk.Frame(self.sidebar, bg=sidebar_bg)
            connection.pack(side="bottom", fill="x", padx=14, pady=(4, 0))
            tk.Label(connection, text="KONEKSI MCU", bg=sidebar_bg, fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 7))
            self.port_var = tk.StringVar(value=self.args.port or "")
            port_row = tk.Frame(connection, bg=sidebar_bg)
            port_row.pack(fill="x")
            self.port_combo = ttk.Combobox(
                port_row, textvariable=self.port_var, state="normal", width=14,
            )
            self.port_combo.pack(side="left", fill="x", expand=True)
            self.scan_port_button = tk.Button(
                port_row, text="Scan", command=self.refresh_ports,
                bg=COLORS["panel_2"], fg=COLORS["text"],
                activebackground=COLORS["line"], activeforeground=COLORS["white"],
                relief="flat", bd=0, font=("Segoe UI Semibold", 8),
                padx=8, pady=6, cursor="hand2",
            )
            self.scan_port_button.pack(side="left", padx=(6, 0))
            self.refresh_ports(show_status=False)
            row = tk.Frame(connection, bg=sidebar_bg)
            row.pack(fill="x", pady=(7, 0))
            self.connect_button = tk.Button(
                row, text="Hubungkan", command=self.toggle_connection, bg=COLORS["blue"], fg="#07111F",
                activebackground="#7EC0FF", relief="flat", bd=0, font=("Segoe UI Semibold", 9),
                padx=9, pady=8, cursor="hand2",
            )
            self.connect_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
            tk.Button(
                row, text="Demo", command=self.start_demo, bg=COLORS["panel_2"], fg=COLORS["text"],
                activebackground=COLORS["line"], activeforeground=COLORS["white"], relief="flat", bd=0,
                font=("Segoe UI Semibold", 9), padx=9, pady=8, cursor="hand2",
            ).pack(side="left", fill="x", expand=True, padx=(4, 0))

            self.main = tk.Frame(self.root, bg=COLORS["bg"])
            self.main.grid(row=0, column=1, sticky="nsew")
            self.main.grid_columnconfigure(0, weight=1)
            self.main.grid_rowconfigure(4, weight=1)

            header = tk.Frame(self.main, bg=COLORS["bg"])
            header.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 7))
            title_box = tk.Frame(header, bg=COLORS["bg"])
            title_box.pack(side="left", fill="y")
            self.page_title = tk.Label(title_box, text="Persiapan Sensor", bg=COLORS["bg"], fg=COLORS["text"],
                                       font=("Segoe UI Semibold", 19))
            self.page_title.pack(anchor="w")
            self.page_subtitle = tk.Label(title_box, text="Kalibrasi sudut dan pengambilan nilai MVC", bg=COLORS["bg"],
                                          fg=COLORS["muted"], font=("Segoe UI", 9))
            self.page_subtitle.pack(anchor="w", pady=(2, 0))
            actions = tk.Frame(header, bg=COLORS["bg"])
            actions.pack(side="right", anchor="n")
            self.safety_badge = tk.Label(actions, text="DEMO AMAN", bg=COLORS["ready_bg"], fg=COLORS["green"],
                                         font=("Segoe UI Semibold", 9), padx=11, pady=6)
            self.safety_badge.pack(side="left", padx=(0, 8))
            self.log_button = tk.Button(
                actions, text="Mulai CSV", command=self.toggle_logging, bg=COLORS["panel_2"],
                fg=COLORS["text"], activebackground=COLORS["line"], activeforeground=COLORS["white"],
                relief="flat", bd=0, font=("Segoe UI Semibold", 9), padx=11, pady=6, cursor="hand2",
            )
            self.log_button.pack(side="left")

            health = tk.Frame(self.main, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
            health.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 7))
            tk.Label(health, text="SYSTEM HEALTH", bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(side="left", padx=(12, 10), pady=7)
            chips = tk.Frame(health, bg=COLORS["panel"])
            chips.pack(side="left", fill="x", expand=True, pady=4)
            self.health_labels: Dict[str, tk.Label] = {}
            for index, (key, label) in enumerate((
                ("MCU", "MCU"), ("IMU_A", "IMU A"), ("IMU_B", "IMU B"), ("EMG", "EMG"),
                ("MCP", "MCP4725"), ("HBRIDGE", "H-BRIDGE"), ("FES", "FES"),
                ("SAFETY", "SAFETY"), ("DATA", "DATA"),
            )):
                chip = tk.Frame(chips, bg=COLORS["panel"])
                chip.pack(side="left", padx=(0 if index == 0 else 5, 5), pady=1)
                if index:
                    tk.Frame(chip, bg=COLORS["line"], width=1).pack(side="left", fill="y", padx=(0, 8))
                tk.Label(chip, text=label, bg=COLORS["panel"], fg=COLORS["muted"],
                         font=("Segoe UI Semibold", 7)).pack(side="left", padx=(0, 4), pady=3)
                value = tk.Label(chip, text="--", bg=COLORS["panel"], fg=COLORS["muted"],
                                  font=("Segoe UI Semibold", 8))
                value.pack(side="left", pady=3)
                self.health_labels[key] = value

            metrics = tk.Frame(self.main, bg=COLORS["bg"])
            metrics.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 7))
            for index in range(6):
                metrics.grid_columnconfigure(index, weight=1, uniform="metric")
            self.angle_card = MetricCard(metrics, "Angle", "°", COLORS["cyan"])
            self.emg_card = MetricCard(metrics, "EMG RMS", "mV", COLORS["yellow"])
            self.mav_card = MetricCard(metrics, "MAV", "mV", COLORS["green"])
            self.pwm_card = MetricCard(metrics, "Pulse Width", "µs", COLORS["blue"])
            self.frequency_card = MetricCard(metrics, "Frequency", "Hz", COLORS["cyan"])
            self.current_card = MetricCard(metrics, "FES Current", "mA", COLORS["green"])
            cards = (
                self.angle_card, self.emg_card, self.mav_card, self.pwm_card,
                self.frequency_card, self.current_card,
            )
            for index, card in enumerate(cards):
                card.grid(
                    row=0, column=index, sticky="nsew",
                    padx=(0 if index == 0 else 3, 0 if index == len(cards) - 1 else 3),
                )

            state_band = tk.Frame(self.main, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
            state_band.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 7))
            tk.Label(state_band, text="MODE", bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(side="left", padx=(12, 10), pady=6)
            self.mode_state_labels: Dict[str, tk.Label] = {}
            for mode_name in ("WAIT", "STANDBY", "AUTO", "MANUAL", "EMERGENCY"):
                chip = tk.Label(state_band, text=mode_name, bg=COLORS["panel_2"], fg=COLORS["muted"],
                                font=("Segoe UI Semibold", 8), padx=11, pady=4)
                chip.pack(side="left", padx=(0, 5), pady=4)
                self.mode_state_labels[mode_name] = chip
            self.mode_state_labels["WAIT"].configure(bg=COLORS["ready_bg"], fg=COLORS["green"])

            session_time_box = tk.Frame(state_band, bg=COLORS["panel"])
            session_time_box.pack(side="right", padx=(0, 12), pady=4)
            tk.Label(session_time_box, text="SESSION TIME", bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(side="left", padx=(0, 8))
            self.session_time_label = tk.Label(session_time_box, text="--- s", bg=COLORS["panel_2"],
                                               fg=COLORS["cyan"], font=("Segoe UI Semibold", 9),
                                               padx=10, pady=4)
            self.session_time_label.pack(side="left")

            self.page_host = tk.Frame(self.main, bg=COLORS["bg"])
            self.page_host.grid(row=4, column=0, sticky="nsew", padx=18)
            self.page_host.grid_rowconfigure(0, weight=1)
            self.page_host.grid_columnconfigure(0, weight=1)
            self._build_calibration_page()
            self._build_auto_page()
            self._build_manual_page()
            self._build_emg_page()

            footer = tk.Frame(self.main, bg=COLORS["bg"])
            footer.grid(row=5, column=0, sticky="ew", padx=18, pady=(6, 8))
            self.status_dot = tk.Label(footer, text="●", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9))
            self.status_dot.pack(side="left")
            self.status_label = tk.Label(footer, text="Menyiapkan aplikasi...", bg=COLORS["bg"],
                                         fg=COLORS["muted"], font=("Segoe UI", 9))
            self.status_label.pack(side="left", padx=(6, 0))
            self.mode_label = tk.Label(footer, text="MODE: WAIT", bg=COLORS["bg"], fg=COLORS["muted"],
                                       font=("Segoe UI Semibold", 9))
            self.mode_label.pack(side="right")
            self.timer_label = tk.Label(footer, text="--- s", bg=COLORS["bg"], fg=COLORS["muted"],
                                        font=("Segoe UI", 9))
            self.timer_label.pack(side="right", padx=(0, 18))

        def _panel(self, parent: tk.Misc) -> tk.Frame:
            return tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])

        def _section_header(self, parent: tk.Misc, title: str, description: str = "") -> None:
            tk.Label(parent, text=title, bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=16, pady=(14, 2 if description else 10))
            if description:
                tk.Label(parent, text=description, bg=COLORS["panel"], fg=COLORS["muted"],
                         font=("Segoe UI", 9), justify="left", wraplength=560).pack(
                             anchor="w", fill="x", padx=16, pady=(0, 9),
                         )

        def _scrollable_info_body(self, parent: tk.Misc, key: str) -> tk.Frame:
            container = tk.Frame(parent, bg=COLORS["panel"])
            container.pack(fill="both", expand=True)
            container.grid_rowconfigure(0, weight=1)
            container.grid_columnconfigure(0, weight=1)

            canvas = tk.Canvas(
                container, bg=COLORS["panel"], highlightthickness=0,
                bd=0, yscrollincrement=24,
            )
            scrollbar = ttk.Scrollbar(
                container, orient="vertical", command=canvas.yview,
                style="Dark.Vertical.TScrollbar",
            )
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            body = tk.Frame(canvas, bg=COLORS["panel"])
            window_id = canvas.create_window((0, 0), window=body, anchor="nw")

            def sync_scroll_region(_event: Any = None) -> None:
                canvas.configure(scrollregion=canvas.bbox("all"))
                if body.winfo_reqheight() > canvas.winfo_height():
                    scrollbar.grid()
                else:
                    scrollbar.grid_remove()
                    canvas.yview_moveto(0.0)

            def size_body(event: Any) -> None:
                canvas.itemconfigure(window_id, width=event.width)
                sync_scroll_region()

            def scroll(event: Any) -> str:
                if body.winfo_reqheight() > canvas.winfo_height():
                    steps = -1 if event.delta > 0 else 1
                    canvas.yview_scroll(steps, "units")
                return "break"

            body.bind("<Configure>", sync_scroll_region)
            canvas.bind("<Configure>", size_body)
            canvas.bind("<MouseWheel>", scroll)
            body.bind("<MouseWheel>", scroll)
            body.mousewheel_handler = scroll
            self.scroll_containers[key] = {
                "container": container, "canvas": canvas, "body": body, "scrollbar": scrollbar,
            }
            return body

        def _action_row(
            self, parent: tk.Misc, title: str, description: str, button_text: str,
            command: Callable[[], None], accent: str,
        ) -> tk.Button:
            row = tk.Frame(parent, bg=COLORS["panel"])
            row.pack(fill="x")
            tk.Frame(row, bg=accent, width=3).pack(side="left", fill="y", padx=(0, 12))
            body = tk.Frame(row, bg=COLORS["panel"])
            body.pack(side="left", fill="both", expand=True, pady=9)
            tk.Label(body, text=title, bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 10)).pack(anchor="w")
            tk.Label(body, text=description, bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI", 9), wraplength=470, justify="left").pack(anchor="w", pady=(2, 0))
            button = tk.Button(
                row, text=button_text, command=command, bg=COLORS["panel_2"], fg=COLORS["text"],
                activebackground=COLORS["line"], activeforeground=COLORS["white"],
                relief="flat", bd=0, font=("Segoe UI Semibold", 9), padx=12, pady=8, cursor="hand2",
            )
            button.pack(side="right", padx=(12, 0))
            tk.Frame(parent, bg=COLORS["line"], height=1).pack(fill="x")
            return button

        def _build_calibration_page(self) -> None:
            page = tk.Frame(self.page_host, bg=COLORS["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=3)
            page.grid_columnconfigure(1, weight=2)
            page.grid_rowconfigure(0, weight=1)

            choices = self._panel(page)
            choices.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            self._section_header(
                choices, "Persiapan sensor",
                "Selesaikan proses sensor yang diperlukan sebelum sesi terapi.",
            )

            options = tk.Frame(choices, bg=COLORS["panel"])
            options.pack(fill="both", expand=True, padx=16, pady=(2, 10))
            option_specs = (
                ("SUDUT / IMU", "Set referensi dua IMU dan validasi sudut.", "Kalibrasi Sudut", self.calibrate_angle, COLORS["cyan"]),
                ("MVC / EMG", "Ambil nilai Maximum Voluntary Contraction (MVC) sebagai referensi EMG setelah EMG siap.", "Ambil Nilai MVC", self.capture_mvc, COLORS["green"]),
                ("REKALIBRASI EMG", "Ulangi kalibrasi baseline/filter EMG jika sinyal bermasalah. Nilai MVC lama akan dibatalkan.", "Rekalibrasi EMG", self.calibrate_emg, COLORS["yellow"]),
            )
            self.calibration_buttons = []
            for title, description, button_text, command, accent in option_specs:
                self.calibration_buttons.append(
                    self._action_row(options, title, description, button_text, command, accent),
                )

            self.calibration_message = tk.Label(choices, text="Jika EMG direkalibrasi, nilai MVC harus diambil ulang sebelum Mode Auto.",
                                                bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9))
            self.calibration_message.pack(anchor="w", padx=16, pady=(0, 13))

            live = self._panel(page)
            live.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            self._section_header(live, "Monitoring Information")
            self.cal_imu_a = self._status_value(live, "IMU A", "--", COLORS["cyan"])
            self.cal_imu_b = self._status_value(live, "IMU B", "--", COLORS["cyan"])
            self.cal_offset = self._status_value(live, "Offset", "--- °", COLORS["cyan"])
            self.cal_mvc = self._status_value(live, "MVC", "--- mV", COLORS["green"])
            self.cal_imu_cal = self._status_value(live, "IMU Calibration", "---", COLORS["muted"])
            self.cal_mvc_cal = self._status_value(live, "MVC Calibration", "---", COLORS["muted"])
            self.pages["CAL"] = page

        def _status_value(self, parent: tk.Misc, title: str, value: str, accent: str) -> tk.Label:
            row = tk.Frame(parent, bg=COLORS["panel"])
            row.pack(fill="x", padx=16)
            title_label = tk.Label(row, text=title, bg=COLORS["panel"], fg=COLORS["muted"],
                                   font=("Segoe UI", 9))
            title_label.pack(side="left", pady=6)
            lbl = tk.Label(row, text=value, bg=COLORS["panel"], fg=accent,
                           font=("Segoe UI Semibold", 9))
            lbl.pack(side="right", pady=6)
            separator = tk.Frame(parent, bg=COLORS["line"], height=1)
            separator.pack(fill="x", padx=16)
            wheel_handler = getattr(parent, "mousewheel_handler", None)
            if wheel_handler is not None:
                for widget in (row, title_label, lbl, separator):
                    widget.bind("<MouseWheel>", wheel_handler)
            lbl.info_title = title
            lbl.info_row = row
            return lbl

        def _send_calibration(self, command: str, label: str) -> None:
            if not self.manager.connected:
                self._set_status("Hubungkan MCU atau gunakan Demo sebelum kalibrasi.", COLORS["red"])
                return
            ok, message = self.manager.send_command(command)
            if ok:
                self.pending_calibration = command
                self.pending_calibration_label = label
                self.pending_calibration_deadline = time.monotonic() + 8.0
                self.calibration_message.configure(
                    text=f"{label} sedang berjalan di STM32.",
                    fg=COLORS["yellow"],
                )
                self._set_status(f"{label} dimulai.", COLORS["yellow"])
            else:
                self._set_status(message, COLORS["red"])

        def calibrate_angle(self) -> None:
            self._send_calibration("CALIBRATE_ANGLE", "Kalibrasi sudut")

        def capture_mvc(self) -> None:
            # Firmware mensyaratkan MVC diambil setelah kalibrasi IMU selesai.
            if self.manager.connection_kind == "SERIAL" and self.telemetry.angle_calibrated is not True:
                self._set_status("Ambil MVC ditolak: lakukan Kalibrasi Sudut terlebih dahulu.", COLORS["red"])
                self.calibration_message.configure(
                    text="Urutan firmware: Kalibrasi Sudut IMU → Ambil Nilai MVC.",
                    fg=COLORS["yellow"],
                )
                return
            self._send_calibration("CAPTURE_MVC", "Pengambilan nilai MVC")

        def calibrate_emg(self) -> None:
            if not self.manager.connected:
                self._set_status("Hubungkan MCU atau gunakan Demo sebelum rekalibrasi EMG.", COLORS["red"])
                return
            if self.telemetry.output_active is True or self.system_mode in {"AUTO", "MANUAL"}:
                self._set_status("Rekalibrasi EMG ditolak: hentikan terapi terlebih dahulu.", COLORS["red"])
                return
            if self.manager.estop_latched:
                self._set_status("Rekalibrasi EMG ditolak: Reset E-STOP terlebih dahulu.", COLORS["red"])
                return

            ok, message = self.manager.send_command("CALIBRATE_EMG")
            if not ok:
                self._set_status(message, COLORS["red"])
                return

            # Firmware membatalkan MVC lama ketika rekalibrasi EMG dimulai.
            # Update lokal langsung agar GUI tidak menampilkan MVC lama selama
            # menunggu telemetry berikutnya dari STM32.
            self.telemetry.mvc_ready = False
            self.telemetry.emg_calibrated = False
            self.telemetry.mvc_value_mv = 0.0
            self.pending_calibration = "CALIBRATE_EMG"
            self.pending_calibration_label = "Rekalibrasi EMG"
            self.pending_calibration_deadline = time.monotonic() + 8.0
            self.cal_mvc.configure(text="--- mV")
            self.cal_mvc_cal.configure(text="BELUM")
            self.calibration_message.configure(
                text="Rekalibrasi EMG berjalan. Setelah status EMG READY, ambil Nilai MVC kembali.",
                fg=COLORS["yellow"],
            )
            self._set_status("Rekalibrasi EMG diminta; MVC lama dibatalkan.", COLORS["yellow"])

        def calibrate_all(self) -> None:
            # Dipertahankan hanya untuk kompatibilitas pemanggilan lama; opsi UI sudah dihapus.
            self._set_status("Kalibrasi lengkap sudah dihapus. Jalankan Kalibrasi Sudut atau Ambil Nilai MVC.", COLORS["yellow"])

        def _build_auto_page(self) -> None:
            page = tk.Frame(self.page_host, bg=COLORS["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=3)
            page.grid_columnconfigure(1, weight=2)
            page.grid_rowconfigure(0, weight=1)

            control = self._panel(page)
            control.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            self._section_header(
                control, "Set parameter awal",
                "Mode Auto mengendalikan stimulasi menuju target sudut berdasarkan logika kontrol pada MCU.",
            )

            self.auto_current_var = tk.DoubleVar(value=PROJECT_FIXED_CURRENT_MA)
            self.auto_frequency_var = tk.DoubleVar(value=PROJECT_FIXED_FREQUENCY_HZ)
            self.auto_pwm_var = tk.DoubleVar(value=PROJECT_PWM_DEFAULT_US)
            self.auto_angle_var = tk.DoubleVar(value=PROJECT_DEFAULT_TARGET_ANGLE_DEG)

            form = tk.Frame(control, bg=COLORS["panel"])
            form.pack(fill="x", padx=16, pady=(8, 12))
            for col in range(4):
                form.grid_columnconfigure(col, weight=1, uniform="auto_params")
            widgets = (
                self._number_input_at(form, 0, 0, "Arus", "mA", self.auto_current_var, 0, PROJECT_CURRENT_MAX_MA, 0.5),
                self._number_input_at(form, 0, 1, "Frekuensi", "Hz", self.auto_frequency_var, PROJECT_FREQUENCY_MIN_HZ, PROJECT_FREQUENCY_MAX_HZ, 1),
                self._number_input_at(form, 0, 2, "PW", "µs", self.auto_pwm_var, PROJECT_PWM_MIN_US, PROJECT_PWM_MAX_US, 10),
                self._number_input_at(form, 0, 3, "Target sudut", "°", self.auto_angle_var, 0, 90, 1),
            )
            self.control_widgets.extend(widgets)

            button_row = tk.Frame(control, bg=COLORS["panel"])
            button_row.pack(fill="x", padx=16, pady=(0, 14))
            self.auto_start_button = tk.Button(button_row, text="Mulai Auto", command=self.start_auto,
                                               bg=COLORS["blue"], fg="#061120", activebackground="#7EC0FF",
                                               relief="flat", bd=0, font=("Segoe UI Semibold", 10), pady=11, cursor="hand2")
            self.auto_start_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.control_widgets.append(self.auto_start_button)
            tk.Button(button_row, text="Stop Sesi", command=self.stop_session, bg=COLORS["panel_2"], fg=COLORS["text"],
                      activebackground=COLORS["line"], activeforeground=COLORS["white"], relief="flat", bd=0,
                      font=("Segoe UI Semibold", 10), pady=11, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(5, 0))

            status = self._panel(page)
            status.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            self._section_header(status, "Auto Information")
            self.auto_message_label = tk.Label(status, text="Hubungkan perangkat atau gunakan demo.", bg=COLORS["panel"],
                                                 fg=COLORS["muted"], justify="left", wraplength=330, font=("Segoe UI", 9))
            self.auto_message_label.pack(anchor="w", fill="x", padx=16, pady=(0, 7))
            auto_info_body = self._scrollable_info_body(status, "auto_page")
            self.auto_info_fsm = self._status_value(auto_info_body, "FSM State", "---", COLORS["muted"])
            self.auto_info_target = self._status_value(auto_info_body, "Target Angle", "--- °", COLORS["cyan"])
            self.auto_info_error = self._status_value(auto_info_body, "Angle Error", "--- °", COLORS["yellow"])
            self.auto_info_derror = self._status_value(auto_info_body, "Delta Error", "--- °", COLORS["blue"])
            self.auto_info_mvc = self._status_value(auto_info_body, "MVC", "--- mV", COLORS["green"])
            self.auto_info_fatigue = self._status_value(auto_info_body, "Fatigue", "---", COLORS["muted"])
            self.auto_info_fatigue_count = self._status_value(auto_info_body, "Fatigue Count", "---", COLORS["muted"])
            self.auto_info_rem_dur = self._status_value(auto_info_body, "Remaining / Duration", "---", COLORS["muted"])
            self.auto_info_dac_v = self._status_value(auto_info_body, "DAC Voltage", "--- V", COLORS["cyan"])
            self.fes_output_label = self._status_value(auto_info_body, "FES Output", "---", COLORS["muted"])
            # Existing command callbacks still write transient phase text here.
            # The sink stays unplaced so it cannot overwrite raw telemetry in
            # the visible FSM State row or recreate the duplicate large state.
            self.auto_phase_label = tk.Label(status, text="", bg=COLORS["panel"])
            # Compatibility aliases keep non-command callback references valid.
            self.auto_fsm_value = self.auto_info_fsm
            self.target_angle_value = self.auto_info_target
            self.error_angle_value = self.auto_info_error
            self.pages["AUTO"] = page

        def _mini_metric(self, parent: tk.Misc, column: int, title: str, value: str) -> tk.Label:
            box = tk.Frame(parent, bg=COLORS["panel_2"], highlightthickness=1, highlightbackground=COLORS["line"])
            box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0 if column == 2 else 4))
            tk.Label(box, text=title, bg=COLORS["panel_2"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=10, pady=(8, 1))
            lbl = tk.Label(box, text=value, bg=COLORS["panel_2"], fg=COLORS["text"], font=("Segoe UI Semibold", 15))
            lbl.pack(anchor="w", padx=10, pady=(0, 8))
            return lbl

        def _number_input_at(
            self, parent: tk.Misc, row_index: int, column: int, label: str, unit: str,
            variable: tk.DoubleVar, minimum: float, maximum: float, increment: float,
        ) -> Any:
            box = tk.Frame(parent, bg=COLORS["panel"])
            box.grid(row=row_index, column=column, sticky="ew", padx=5, pady=(0, 10))
            tk.Label(box, text=label, bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 5))
            row = tk.Frame(box, bg=COLORS["panel"])
            row.pack(fill="x")
            widget = ttk.Spinbox(row, from_=minimum, to=maximum, increment=increment,
                                 textvariable=variable, font=("Segoe UI Semibold", 11), width=8)
            widget.pack(side="left", fill="x", expand=True)
            tk.Label(row, text=unit, bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))
            return widget

        def _number_input(
            self, parent: tk.Misc, column: int, label: str, unit: str, variable: tk.DoubleVar,
            minimum: float, maximum: float, increment: float,
        ) -> Any:
            box = tk.Frame(parent, bg=COLORS["panel"])
            box.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 6, 0 if column >= 1 else 6),
            )
            tk.Label(box, text=label, bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))
            row = tk.Frame(box, bg=COLORS["panel"])
            row.pack(fill="x")
            widget = ttk.Spinbox(row, from_=minimum, to=maximum, increment=increment, textvariable=variable,
                                 font=("Segoe UI Semibold", 12), width=9)
            widget.pack(side="left", fill="x", expand=True)
            tk.Label(row, text=unit, bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))
            return widget

        def _build_manual_page(self) -> None:
            page = tk.Frame(self.page_host, bg=COLORS["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=3)
            page.grid_columnconfigure(1, weight=2)
            page.grid_rowconfigure(0, weight=1)

            control = self._panel(page)
            control.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            self._section_header(
                control, "Set parameter awal",
                "Mode Manual menjalankan parameter FES sesuai nilai operator dengan siklus ACTIVE/REST.",
            )

            self.manual_current_var = tk.DoubleVar(value=PROJECT_FIXED_CURRENT_MA)
            self.manual_frequency_var = tk.DoubleVar(value=PROJECT_FIXED_FREQUENCY_HZ)
            self.manual_pwm_var = tk.DoubleVar(value=PROJECT_PWM_DEFAULT_US)
            self.manual_active_var = tk.DoubleVar(value=5.0)
            self.manual_rest_var = tk.DoubleVar(value=5.0)

            form = tk.Frame(control, bg=COLORS["panel"])
            form.pack(fill="x", padx=16, pady=(8, 10))
            for col in range(3):
                form.grid_columnconfigure(col, weight=1, uniform="manual_params")
            widgets = (
                self._number_input_at(form, 0, 0, "Arus", "mA", self.manual_current_var, 0, PROJECT_CURRENT_MAX_MA, 0.5),
                self._number_input_at(form, 0, 1, "Frekuensi", "Hz", self.manual_frequency_var, PROJECT_FREQUENCY_MIN_HZ, PROJECT_FREQUENCY_MAX_HZ, 1),
                self._number_input_at(form, 0, 2, "PW", "µs", self.manual_pwm_var, PROJECT_PWM_MIN_US, PROJECT_PWM_MAX_US, 10),
                self._number_input_at(form, 1, 0, "Durasi ACTIVE", "s", self.manual_active_var, 0.5, 120, 0.5),
                self._number_input_at(form, 1, 1, "Durasi REST", "s", self.manual_rest_var, 0.5, 120, 0.5),
            )
            self.control_widgets.extend(widgets)

            row = tk.Frame(control, bg=COLORS["panel"])
            row.pack(fill="x", padx=16, pady=(0, 14))
            self.manual_apply_button = tk.Button(row, text="Mulai Manual", command=self.apply_manual, bg=COLORS["blue"], fg="#061120",
                                                 activebackground="#7EC0FF", relief="flat", bd=0, font=("Segoe UI Semibold", 10), pady=12, cursor="hand2")
            self.manual_apply_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.control_widgets.append(self.manual_apply_button)
            tk.Button(row, text="Stop Sesi", command=self.stop_session, bg=COLORS["panel_2"], fg=COLORS["text"],
                      activebackground=COLORS["line"], activeforeground=COLORS["white"], relief="flat", bd=0,
                      font=("Segoe UI Semibold", 10), pady=12, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(6, 0))

            status = self._panel(page)
            status.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            self._section_header(status, "Manual Information")
            self.manual_kondisi_live = self._status_value(status, "Condition", "---", COLORS["green"])
            self.manual_rem_dur_live = self._status_value(status, "Remaining / Duration", "---", COLORS["muted"])
            self.manual_dac_v_live = self._status_value(status, "DAC Voltage", "--- V", COLORS["cyan"])
            self.manual_output_live = self._status_value(status, "FES Output", "---", COLORS["muted"])
            self.pages["MANUAL"] = page

        def _slider(self, parent: tk.Misc, label: str, unit: str, variable: tk.DoubleVar,
                    minimum: float, maximum: float) -> Any:
            box = tk.Frame(parent, bg=COLORS["panel"])
            box.pack(fill="x", pady=(0, 23))
            header = tk.Frame(box, bg=COLORS["panel"])
            header.pack(fill="x")
            tk.Label(header, text=label, bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(side="left")
            value_label = tk.Label(header, text=f"{variable.get():.1f} {unit}", bg=COLORS["panel"],
                                   fg=COLORS["text"], font=("Segoe UI Semibold", 11))
            value_label.pack(side="right")
            variable.trace_add("write", lambda *_args, v=variable, lbl=value_label, u=unit:
                               lbl.configure(text=f"{v.get():.1f} {u}"))
            scale = ttk.Scale(box, from_=minimum, to=maximum, orient="horizontal", variable=variable)
            scale.pack(fill="x", pady=(10, 0))
            return scale

        def _build_emg_page(self) -> None:
            page = tk.Frame(self.page_host, bg=COLORS["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=3)
            page.grid_columnconfigure(1, weight=2)
            page.grid_rowconfigure(0, weight=1)

            panel = self._panel(page)
            panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            heading = tk.Frame(panel, bg=COLORS["panel"])
            heading.pack(fill="x", padx=16, pady=(13, 3))
            tk.Label(heading, text="Sinyal EMG", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(side="left")
            self.quality_label = tk.Label(panel, text="Signal quality: menunggu", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9))
            self.quality_label.pack(anchor="w", padx=16)
            self.movement_wait_label = tk.Label(panel, text="MENUNGGU GERAKAN", bg=COLORS["panel"], fg=COLORS["yellow"],
                                                font=("Segoe UI Semibold", 14))
            self.movement_wait_label.pack(anchor="w", padx=16, pady=(5, 0))
            self.emg_plot = EMGPlot(panel)
            self.emg_plot.pack(fill="both", expand=True, padx=10, pady=(6, 10))

            states = self._panel(page)
            states.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            self.emg_right_host = tk.Frame(states, bg=COLORS["panel"])
            self.emg_right_host.pack(fill="both", expand=True)
            self.emg_right_host.grid_rowconfigure(0, weight=1)
            self.emg_right_host.grid_columnconfigure(0, weight=1)

            # --- WAIT panel (Monitoring Information) ---
            wp = tk.Frame(self.emg_right_host, bg=COLORS["panel"])
            wp.grid(row=0, column=0, sticky="nsew")
            self._section_header(wp, "Monitoring Information")
            tk.Label(wp, text="Menunggu sensor siap. Hubungkan MCU atau gunakan Demo.",
                     bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9),
                     wraplength=300, justify="left").pack(anchor="w", padx=16, pady=(0, 7))
            wait_info_body = self._scrollable_info_body(wp, "emg_wait")
            self.emg_wait_imu_a = self._status_value(wait_info_body, "IMU A", "--", COLORS["cyan"])
            self.emg_wait_imu_b = self._status_value(wait_info_body, "IMU B", "--", COLORS["cyan"])
            self.emg_wait_offset = self._status_value(wait_info_body, "Offset", "--- °", COLORS["cyan"])
            self.emg_wait_mvc = self._status_value(wait_info_body, "MVC", "--- mV", COLORS["green"])
            self.emg_wait_imu_cal = self._status_value(wait_info_body, "IMU Calibration", "---", COLORS["muted"])
            self.emg_wait_mvc_cal = self._status_value(wait_info_body, "MVC Calibration", "---", COLORS["muted"])
            self.emg_wait_quality = self._status_value(wait_info_body, "Signal quality", "---", COLORS["green"])

            # --- STANDBY panel (Monitoring Information) ---
            sp = tk.Frame(self.emg_right_host, bg=COLORS["panel"])
            sp.grid(row=0, column=0, sticky="nsew")
            self._section_header(sp, "Monitoring Information")
            tk.Label(sp, text="Sistem siap. Pilih Mode Auto atau Manual untuk memulai sesi.",
                     bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9),
                     wraplength=300, justify="left").pack(anchor="w", padx=16, pady=(0, 7))
            standby_info_body = self._scrollable_info_body(sp, "emg_standby")
            self.emg_standby_imu_a = self._status_value(standby_info_body, "IMU A", "--", COLORS["cyan"])
            self.emg_standby_imu_b = self._status_value(standby_info_body, "IMU B", "--", COLORS["cyan"])
            self.emg_standby_offset = self._status_value(standby_info_body, "Offset", "--- °", COLORS["cyan"])
            self.emg_standby_mvc = self._status_value(standby_info_body, "MVC", "--- mV", COLORS["green"])
            self.emg_standby_imu_cal = self._status_value(standby_info_body, "IMU Calibration", "---", COLORS["muted"])
            self.emg_standby_mvc_cal = self._status_value(standby_info_body, "MVC Calibration", "---", COLORS["muted"])
            self.emg_standby_fes = self._status_value(standby_info_body, "FES Output", "---", COLORS["muted"])
            self.emg_standby_quality = self._status_value(standby_info_body, "Signal quality", "---", COLORS["green"])

            # --- AUTO panel (Auto Information) ---
            ap = tk.Frame(self.emg_right_host, bg=COLORS["panel"])
            ap.grid(row=0, column=0, sticky="nsew")
            self._section_header(ap, "Auto Information")
            emg_auto_body = self._scrollable_info_body(ap, "emg_auto")
            self.emg_auto_fsm = self._status_value(emg_auto_body, "FSM State", "---", COLORS["muted"])
            self.emg_auto_target = self._status_value(emg_auto_body, "Target Angle", "--- °", COLORS["cyan"])
            self.emg_auto_error = self._status_value(emg_auto_body, "Angle Error", "--- °", COLORS["yellow"])
            self.emg_auto_derror = self._status_value(emg_auto_body, "Delta Error", "--- °", COLORS["blue"])
            self.emg_auto_mvc = self._status_value(emg_auto_body, "MVC", "--- mV", COLORS["green"])
            self.emg_auto_fatigue = self._status_value(emg_auto_body, "Fatigue", "---", COLORS["muted"])
            self.emg_auto_fatigue_count = self._status_value(emg_auto_body, "Fatigue Count", "---", COLORS["muted"])
            self.emg_auto_rem_dur = self._status_value(emg_auto_body, "Remaining / Duration", "---", COLORS["muted"])
            self.emg_auto_dac_v = self._status_value(emg_auto_body, "DAC Voltage", "--- V", COLORS["cyan"])
            self.emg_auto_fes = self._status_value(emg_auto_body, "FES Output", "---", COLORS["green"])
            self.emg_auto_quality = self._status_value(emg_auto_body, "Signal quality", "---", COLORS["green"])

            # --- MANUAL panel (Manual Information) ---
            mp = tk.Frame(self.emg_right_host, bg=COLORS["panel"])
            mp.grid(row=0, column=0, sticky="nsew")
            self._section_header(mp, "Manual Information")
            emg_manual_body = self._scrollable_info_body(mp, "emg_manual")
            self.emg_manual_kondisi = self._status_value(emg_manual_body, "Condition", "---", COLORS["green"])
            self.emg_manual_rem_dur = self._status_value(emg_manual_body, "Remaining / Duration", "---", COLORS["muted"])
            self.emg_manual_dac_v = self._status_value(emg_manual_body, "DAC Voltage", "--- V", COLORS["cyan"])
            self.emg_manual_fes = self._status_value(emg_manual_body, "FES Output", "---", COLORS["green"])
            self.emg_manual_quality = self._status_value(emg_manual_body, "Signal quality", "---", COLORS["green"])

            # --- EMERGENCY panel (Emergency Information) ---
            ep = tk.Frame(self.emg_right_host, bg=COLORS["panel"])
            ep.grid(row=0, column=0, sticky="nsew")
            tk.Label(ep, text="Emergency Information", bg=COLORS["panel"], fg=COLORS["red"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=16, pady=(14, 8))
            tk.Label(ep, text="Emergency aktif. Periksa hardware sebelum reset.",
                     bg=COLORS["panel"], fg=COLORS["red"], font=("Segoe UI", 9),
                     wraplength=300, justify="left").pack(anchor="w", padx=16, pady=(0, 7))
            emg_emergency_body = self._scrollable_info_body(ep, "emg_emergency")
            self.emg_emg_source = self._status_value(emg_emergency_body, "Safety Trigger", "---", COLORS["red"])
            self.emg_emg_fault = self._status_value(emg_emergency_body, "Fault Code", "---", COLORS["red"])
            self.emg_emg_fes = self._status_value(emg_emergency_body, "FES Output", "---", COLORS["red"])
            self.emg_emg_fsm = self._status_value(emg_emergency_body, "FSM State", "---", COLORS["red"])
            self.emg_emg_status = self._status_value(emg_emergency_body, "Status", "---", COLORS["red"])

            self.emg_right_panels = {
                "WAIT": wp, "STANDBY": sp, "AUTO": ap,
                "MANUAL": mp, "EMERGENCY": ep,
            }
            self._emg_right_mode = "WAIT"
            wp.tkraise()
            self.pages["EMG"] = page

        def show_page(self, page: str) -> None:
            if page not in self.pages:
                return
            self.current_page = {
                "CAL": "PREPARATION",
                "AUTO": "AUTO",
                "MANUAL": "MANUAL",
                "EMG": "MONITORING_EMG",
            }[page]
            self.pages[page].tkraise()
            titles = {
                "CAL": ("Persiapan Sensor", "Kalibrasi sudut IMU atau pengambilan nilai MVC EMG"),
                "AUTO": ("Mode Auto", "Set arus, frekuensi, PW, target sudut, dan pantau FSM"),
                "MANUAL": ("Mode Manual", "Parameter FES manual dengan durasi ACTIVE dan REST"),
                "EMG": ("Monitoring EMG", "Pantau sinyal EMG, sudut, error sudut, delta error, MVC, dan durasi ACTIVE/REST"),
            }
            title, subtitle = titles[page]
            self.page_title.configure(text=title)
            self.page_subtitle.configure(text=subtitle)
            for key, button in self.nav_buttons.items():
                selected = key == page
                button.configure(bg=COLORS["panel_2"] if selected else COLORS["sidebar"],
                                 fg=COLORS["white"] if selected else COLORS["muted"])

        def _validated_setpoints(
            self, current_var: tk.DoubleVar, frequency_var: tk.DoubleVar, pwm_var: tk.DoubleVar,
            active_var: tk.DoubleVar, rest_var: tk.DoubleVar,
        ) -> Optional[Tuple[float, float, float, float, float]]:
            try:
                current = float(current_var.get())
                frequency = float(frequency_var.get())
                pwm = float(pwm_var.get())
                active_s = float(active_var.get())
                rest_s = float(rest_var.get())
            except (ValueError, tk.TclError):
                messagebox.showerror("Nilai tidak valid", "Arus, frekuensi, PW, ACTIVE, dan REST harus berupa angka.")
                return None
            if not 0.0 <= current <= PROJECT_CURRENT_MAX_MA:
                messagebox.showerror("Nilai di luar rentang", f"Arus harus 0–{PROJECT_CURRENT_MAX_MA:.0f} mA.")
                return None
            if not PROJECT_FREQUENCY_MIN_HZ <= frequency <= PROJECT_FREQUENCY_MAX_HZ:
                messagebox.showerror("Nilai di luar rentang", f"Frekuensi harus {PROJECT_FREQUENCY_MIN_HZ:.0f}–{PROJECT_FREQUENCY_MAX_HZ:.0f} Hz.")
                return None
            if not PROJECT_PWM_MIN_US <= pwm <= PROJECT_PWM_MAX_US:
                messagebox.showerror(
                    "Nilai di luar rentang",
                    f"PW / pulse width harus {PROJECT_PWM_MIN_US:.0f}–{PROJECT_PWM_MAX_US:.0f} µs.",
                )
                return None
            if not 0.5 <= active_s <= 120.0 or not 0.5 <= rest_s <= 120.0:
                messagebox.showerror("Nilai di luar rentang", "Durasi ACTIVE dan REST harus 0.5–120 detik.")
                return None
            return current, frequency, pwm, active_s, rest_s

        def _validated_auto_settings(self) -> Optional[Tuple[float, float, float, float]]:
            try:
                current = float(self.auto_current_var.get())
                frequency = float(self.auto_frequency_var.get())
                pwm = float(self.auto_pwm_var.get())
                angle = float(self.auto_angle_var.get())
            except (ValueError, tk.TclError):
                messagebox.showerror("Nilai tidak valid", "Arus, frekuensi, PW, dan target sudut harus berupa angka.")
                return None
            if not 0.0 <= current <= PROJECT_CURRENT_MAX_MA:
                messagebox.showerror("Nilai di luar rentang", f"Arus harus 0–{PROJECT_CURRENT_MAX_MA:.0f} mA.")
                return None
            if not PROJECT_FREQUENCY_MIN_HZ <= frequency <= PROJECT_FREQUENCY_MAX_HZ:
                messagebox.showerror("Nilai di luar rentang", f"Frekuensi harus {PROJECT_FREQUENCY_MIN_HZ:.0f}–{PROJECT_FREQUENCY_MAX_HZ:.0f} Hz.")
                return None
            if not PROJECT_PWM_MIN_US <= pwm <= PROJECT_PWM_MAX_US:
                messagebox.showerror(
                    "Nilai di luar rentang",
                    f"PW / pulse width harus {PROJECT_PWM_MIN_US:.0f}–{PROJECT_PWM_MAX_US:.0f} µs.",
                )
                return None
            if not 0.0 <= angle <= 90.0:
                messagebox.showerror("Nilai di luar rentang", "Target sudut harus 0–90°.")
                return None
            return angle, current, frequency, pwm

        def _current_fsm_state(self) -> str:
            raw = self.telemetry.fsm_state or self.telemetry.phase or "IDLE"
            return raw_fsm_state(raw)

        def _update_mode_indicator(self) -> None:
            for name, label in self.mode_state_labels.items():
                active = name == self.system_mode
                label.configure(
                    bg=COLORS["red_dark"] if active and name == "EMERGENCY" else COLORS["ready_bg"] if active else COLORS["panel_2"],
                    fg=COLORS["red"] if active and name == "EMERGENCY" else COLORS["green"] if active else COLORS["muted"],
                )

        def _start_snapshot_safe(self) -> bool:
            fsm = self._current_fsm_state()
            return bool(
                self.telemetry.output_active is False
                and fsm_is_safe_stopped(fsm)
                and self.telemetry.current_cmd_ma is not None
                and self.telemetry.current_cmd_ma <= 1.0
            )

        def _control_ready_for_start(
            self, *, require_emg_quality: bool, allow_calibration_fault: bool = False,
        ) -> bool:
            if not self.manager.can_control():
                self._set_status("Kontrol belum siap: hubungkan MCU atau gunakan Demo.", COLORS["red"])
                return False
            if self.data_stale:
                self._set_status("Kontrol dikunci karena telemetry belum aktif atau sudah stale.", COLORS["red"])
                return False
            if self.telemetry.output_active is not False:
                self._set_status("START ditolak: MCU belum mengonfirmasi keluaran OFF.", COLORS["red"])
                return False
            if not fsm_is_safe_stopped(self._current_fsm_state()):
                self._set_status(f"START ditolak: FSM belum safe-stopped ({self._current_fsm_state()}).", COLORS["red"])
                return False
            if self.telemetry.current_cmd_ma is None or self.telemetry.current_cmd_ma > 1.0:
                self._set_status("START ditolak: perintah arus saat output OFF belum 0 mA.", COLORS["red"])
                return False
            fault = (self.telemetry.fault or "NONE").strip().upper()
            fault_clear = fault in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"}
            if not fault_clear and not (allow_calibration_fault and fault.startswith("CAL_")):
                self._set_status(f"START ditolak: fault MCU aktif ({fault}).", COLORS["red"])
                return False
            quality = (self.telemetry.signal_quality or "UNKNOWN").strip().upper()
            if require_emg_quality and quality not in {"GOOD", "BAIK", "OK", "VALID"}:
                self._set_status(f"START ditolak: kualitas EMG tidak valid ({quality}).", COLORS["red"])
                return False
            return True

        def _send_serial_start_sequence(
            self, config_command: str, parameters: Mapping[str, Any],
        ) -> Tuple[bool, str]:
            steps = (
                (config_command, dict(parameters)),
                ("FES_ON", {}),
                ("START_THERAPY", {}),
            )
            for command, payload in steps:
                ok, message = self.manager.send_command(command, **payload)
                if not ok:
                    self.manager.send_command(
                        "STOP_THERAPY", safety=True, reason=f"{command.lower()}_failed",
                    )
                    return False, f"{command} gagal: {message}"
            return True, "Parameter diterapkan, FES siap, dan START dikirim."

        def start_auto(self) -> None:
            if not self._control_ready_for_start(require_emg_quality=True):
                return
            mvc_ready = self.telemetry.mvc_ready if self.telemetry.mvc_ready is not None else self.telemetry.emg_calibrated
            if self.manager.connection_kind == "SERIAL" and self.telemetry.angle_calibrated is not True:
                self._set_status("START Auto ditolak: kalibrasi sudut IMU belum selesai.", COLORS["red"])
                return
            if self.manager.connection_kind == "SERIAL" and mvc_ready is not True:
                self._set_status("START Auto ditolak: nilai MVC belum tersedia.", COLORS["red"])
                return
            settings = self._validated_auto_settings()
            if settings is None:
                return
            angle, current, frequency, pwm = settings
            parameters = {
                "angle_target_deg": round(angle, 2),
                "current_cmd_ma": round(current, 3),
                "frequency_set_hz": round(frequency, 2),
                "pulse_width_us": round(pwm, 1),
            }
            if self.manager.connection_kind == "SERIAL":
                ok, message = self._send_serial_start_sequence("SET_AUTO", parameters)
            else:
                ok, message = self.manager.send_command("START_AUTO", **parameters)
            self._set_status(message, COLORS["green"] if ok else COLORS["red"])
            if ok:
                self.pending_mode = "AUTO"
                self.pending_start_deadline = time.monotonic() + 1.5
                self.auto_running = False
                self.auto_phase_label.configure(text="MENUNGGU GERAKAN", fg=COLORS["yellow"])
                self.auto_message_label.configure(text="START Auto dikirim. FSM boleh tetap IDLE sampai niat gerak terdeteksi.")
                self._refresh_mode_label()
                self._refresh_control_state(force=True)

        def apply_manual(self) -> None:
            if not self._control_ready_for_start(
                require_emg_quality=False,
                allow_calibration_fault=True,
            ):
                return
            setpoints = self._validated_setpoints(
                self.manual_current_var, self.manual_frequency_var, self.manual_pwm_var,
                self.manual_active_var, self.manual_rest_var,
            )
            if setpoints is None:
                return
            current, frequency, pwm, active_s, rest_s = setpoints
            parameters = {
                "current_cmd_ma": round(current, 3),
                "frequency_set_hz": round(frequency, 2),
                "pulse_width_us": round(pwm, 1),
                "active_duration_s": round(active_s, 2),
                "rest_duration_s": round(rest_s, 2),
                "output": False,
            }
            if self.manager.connection_kind == "SERIAL":
                ok, message = self._send_serial_start_sequence("SET_MANUAL", parameters)
            else:
                parameters["output"] = True
                ok, message = self.manager.send_command("SET_MANUAL", **parameters)
            self._set_status(message, COLORS["green"] if ok else COLORS["red"])
            if ok:
                self.pending_mode = "MANUAL"
                self.pending_start_deadline = time.monotonic() + 1.5
                self.auto_running = False
                self._refresh_mode_label()
                self._set_status("START Manual dikirim; status terapi mengikuti telemetry STM32.", COLORS["yellow"])
                self._refresh_control_state(force=True)

        def stop_session(self) -> None:
            if self.manager.estop_latched:
                self._set_status("E-STOP sudah aktif; keluaran tetap terkunci.", COLORS["red"])
                return
            if self.system_mode in {"WAIT", "STANDBY"} and self.pending_mode is None and self.telemetry.output_active is False:
                self._set_status("Keluaran sudah OFF.", COLORS["muted"])
                return
            ok, message = self.manager.send_command("STOP_THERAPY", safety=True, reason="operator_stop")
            self.auto_running = False
            self.pending_mode = None
            self.pending_start_deadline = None
            if not ok:
                self.emergency_stop("stop_send_failed")
                self._set_status(f"STOP gagal dikirim ({message}); status keluaran tidak diketahui.", COLORS["red"])
                return
            self.pending_stop_deadline = time.monotonic() + 1.0
            self.auto_phase_label.configure(text="MENUNGGU OFF", fg=COLORS["yellow"])
            self.auto_message_label.configure(text="STOP dikirim; menunggu konfirmasi output OFF dari telemetry.")
            self._refresh_mode_label()
            self._set_status(message, COLORS["yellow"])
            self._refresh_control_state(force=True)

        def emergency_stop(self, reason: str = "operator") -> None:
            ok, message = self.manager.emergency_stop(reason)
            self.estop_output_confirmed = False
            self.last_estop_retry = time.monotonic()
            self.system_mode = "EMERGENCY"
            self.auto_running = False
            if self.session_started_at is not None and self.session_time_known:
                self.session_elapsed_frozen_s = max(0, int(time.monotonic() - self.session_started_at))
            self.session_started_at = None
            self.last_therapy_session_id = self.current_therapy_session_id
            self.current_therapy_session_id = None
            self._prev_therapy_running = False
            self.pending_mode = None
            self.pending_start_deadline = None
            self.pending_stop_deadline = None
            self.auto_phase_label.configure(text="E-STOP", fg=COLORS["red"])
            self.auto_message_label.configure(text="Keluaran terkunci. Periksa hardware sebelum reset.")
            self._refresh_mode_label()
            self._set_status(message, COLORS["red"])
            self.root.bell()
            self._refresh_control_state(force=True)

        def _fresh_estop_off_confirmation(self) -> bool:
            state = self.manager.state()
            phase = (self.telemetry.phase or "").strip().upper()
            fault = (self.telemetry.fault or "").strip().upper()
            emergency_reported = (
                self.telemetry.emergency is True
                or phase in {"E_STOP", "ESTOP"}
                or fault == "EMERGENCY"
            )
            return bool(
                state.get("connected")
                and state.get("kind") in {"DEMO", "SERIAL"}
                and not self.data_stale
                and self.last_telemetry_monotonic is not None
                and time.monotonic() - self.last_telemetry_monotonic <= DATA_STALE_SECONDS
                and emergency_reported
                and self.telemetry.output_active is False
            )

        def reset_estop(self) -> None:
            if not self._fresh_estop_off_confirmation():
                self._set_status(
                    "Reset belum tersedia: STM32 harus melaporkan emergency aktif dan output OFF.",
                    COLORS["red"],
                )
                return
            if not messagebox.askyesno(
                "Reset E-STOP",
                "Pastikan penyebab emergency sudah diperiksa dan keluaran hardware aman.\n\nKirim RESET_ESTOP ke STM32?",
                icon="warning",
            ):
                return
            ok, message = self.manager.reset_estop()
            if not ok:
                self._set_status(message, COLORS["red"])
                return
            self.pending_reset_estop = True
            self.pending_reset_deadline = time.monotonic() + 3.0
            self.auto_phase_label.configure(text="RESET E-STOP...", fg=COLORS["yellow"])
            self.auto_message_label.configure(text="Reset dikirim. Output tetap OFF sampai STM32 kembali IDLE.")
            self._set_status(message, COLORS["yellow"])
            self._refresh_control_state(force=True)

        def _clear_confirmed_estop_reset_state(self) -> None:
            """Clear only GUI session state after safe telemetry confirms RESET."""

            self.manager.confirm_estop_reset()
            self.pending_reset_estop = False
            self.pending_reset_deadline = None
            self.pending_mode = None
            self.pending_start_deadline = None
            self.pending_stop_deadline = None
            self.pending_calibration = None
            self.pending_calibration_label = ""
            self.pending_calibration_deadline = None
            self.session_started_at = None
            self.current_therapy_session_id = None
            self.selected_mode = normalize_selected_mode(self.telemetry.selected_mode)
            self.system_mode = derive_system_mode(self.telemetry)
            self.auto_running = False

        def refresh_ports(self, show_status: bool = True) -> None:
            devices: list[str] = []
            detected = []
            list_ports_error: Optional[Exception] = None

            # Jalur utama: pyserial, karena memberi deskripsi VID/PID/manufacturer.
            if list_ports is not None:
                try:
                    detected = list(list_ports.comports())
                    for item in detected:
                        device = str(getattr(item, "device", "")).strip().upper()
                        if re.fullmatch(r"COM\d+", device) and device not in devices:
                            devices.append(device)
                except Exception as exc:
                    list_ports_error = exc

            # Fallback Windows: Device Manager mendaftarkan COM di Registry.
            # Gabungkan hasilnya agar COM3 tetap muncul walaupun list_ports gagal.
            for device in _windows_registry_com_ports():
                if device not in devices:
                    devices.append(device)

            def port_number(value: str) -> int:
                match = re.search(r"(\d+)$", value)
                return int(match.group(1)) if match else 9999

            devices.sort(key=port_number)
            self.port_combo.configure(values=devices)

            current = self.port_var.get().strip().upper()
            if current not in devices:
                preferred = None

                # Prioritaskan USB-UART/STM32 yang umum dipakai proyek ini jika
                # metadata pyserial tersedia.
                preferred_tokens = (
                    "CH340", "CH341", "USB-SERIAL", "USB SERIAL",
                    "STM32", "ST-LINK", "STLINK", "VCP",
                )
                for item in detected:
                    haystack = (
                        f"{getattr(item, 'description', '')} "
                        f"{getattr(item, 'manufacturer', '')} "
                        f"{getattr(item, 'hwid', '')}"
                    ).upper()
                    device = str(getattr(item, "device", "")).strip().upper()
                    if device in devices and any(token in haystack for token in preferred_tokens):
                        preferred = device
                        break

                # Kalau COM3 ada, pilih COM3 karena itu port MCU yang dipakai user.
                if preferred is None and "COM3" in devices:
                    preferred = "COM3"
                if preferred is None and devices:
                    preferred = devices[0]

                if preferred:
                    self.port_var.set(preferred)

            if show_status:
                if devices:
                    source = "pyserial/Windows"
                    self._set_status(
                        f"Port terdeteksi ({source}): " + ", ".join(devices),
                        COLORS["green"],
                    )
                else:
                    if serial is None:
                        detail = "pyserial belum terpasang pada Python yang menjalankan GUI. Jalankan: python -m pip install pyserial"
                    elif list_ports_error is not None:
                        detail = f"Scanner pyserial error: {list_ports_error}"
                    elif list_ports is None:
                        detail = "serial.tools.list_ports tidak tersedia. Pastikan paket yang terpasang adalah pyserial, bukan paket 'serial'."
                    else:
                        detail = "Windows juga tidak mendaftarkan COM apa pun. Cek Device Manager > Ports (COM & LPT), kabel data, dan driver CH340."
                    self._set_status("COM tidak ditemukan. " + detail, COLORS["red"])

        def toggle_connection(self) -> None:
            if self.manager.port_open or self.manager.connected:
                self.manager.disconnect()
                return
            if not self.port_var.get().strip():
                self.refresh_ports(show_status=True)
            port = self.port_var.get().strip().upper()
            if not port:
                self._set_status("Pilih port COM terlebih dahulu.", COLORS["red"])
                return
            if not re.fullmatch(r"COM\d+", port):
                self._set_status(f"Nama port tidak valid: {port}. Contoh: COM3", COLORS["red"])
                return
            self.port_var.set(port)
            if serial is None:
                self._set_status(
                    "pyserial belum terpasang pada interpreter Python ini. Jalankan: python -m pip install pyserial",
                    COLORS["red"],
                )
                return
            ok, message = self.manager.connect_serial(port, self.args.baud)
            self._set_status(message, COLORS["green"] if ok else COLORS["red"])

        def start_demo(self) -> None:
            self.manager.start_demo()
            self.selected_mode = "NONE"
            self.system_mode = "WAIT"
            self.auto_running = False
            self.session_started_at = None
            self.pending_mode = None
            self.pending_start_deadline = None
            self.pending_stop_deadline = None
            self._refresh_mode_label()

        def toggle_logging(self) -> None:
            if self.logger.active:
                prior_path = self.logger.path
                self.logger.stop()
                self.log_button.configure(text="Mulai CSV", bg=COLORS["panel_2"], fg=COLORS["text"])
                self._set_status(f"Logging selesai: {prior_path}", COLORS["green"])
                return
            default_name = datetime.now().strftime("stimulator_%Y%m%d_%H%M%S.csv")
            path = filedialog.asksaveasfilename(
                title="Simpan log CSV", defaultextension=".csv", initialfile=default_name,
                filetypes=(("CSV", "*.csv"), ("Semua file", "*.*")),
            )
            if not path:
                return
            try:
                self.logger.start(path)
            except OSError as exc:
                messagebox.showerror("Gagal membuat log", str(exc))
                return
            self.log_button.configure(text="Stop CSV", bg=COLORS["ready_bg"], fg=COLORS["green"])
            self._set_status(f"Merekam CSV: {path}", COLORS["green"])

        def _poll_events(self) -> None:
            try:
                # Bound work per tick so a noisy port cannot starve Tk/Escape.
                for _event_index in range(200):
                    kind, payload = self.manager.events.get_nowait()
                    if kind == "telemetry":
                        self._handle_telemetry(payload)
                    elif kind == "status":
                        self._handle_connection_status(payload)
                    elif kind == "error":
                        self._set_status(str(payload), COLORS["red"])
            except queue.Empty:
                pass
            self._check_data_health()
            self._check_pending_start()
            self._check_pending_stop()
            self._check_pending_calibration()
            self._check_pending_reset_estop()
            self._send_heartbeat_if_due()
            self._update_timer()
            self._refresh_control_state()
            self.root.after(80, self._poll_events)

        def _handle_connection_status(self, status: Mapping[str, Any]) -> None:
            connected = bool(status.get("connected"))
            port_open = bool(status.get("port_open", connected))
            kind = str(status.get("kind", "DISCONNECTED"))
            estop = bool(status.get("estop"))
            if not connected:
                self.estop_output_confirmed = False
                if not estop:
                    self.system_mode = "WAIT"
                    self._refresh_mode_label()
            self.connect_button.configure(text="Putus" if port_open else "Hubungkan")
            if estop and not connected:
                self.safety_badge.configure(text="OUTPUT UNKNOWN · E-STOP LOKAL", bg=COLORS["red_dark"], fg=COLORS["white"])
            elif estop:
                badge_text = "OUTPUT OFF · E-STOP" if self.estop_output_confirmed else "OUTPUT UNKNOWN · E-STOP"
                self.safety_badge.configure(text=badge_text, bg=COLORS["red_dark"], fg=COLORS["white"])
            elif self.system_mode == "EMERGENCY":
                self.safety_badge.configure(text="TUNGGU SAFE_IDLE", bg="#3B3220", fg=COLORS["yellow"])
            elif kind == "DEMO":
                self.safety_badge.configure(text="DEMO AMAN", bg=COLORS["ready_bg"], fg=COLORS["green"])
            elif kind == "SERIAL" and connected:
                self.safety_badge.configure(text="KONTROL SERIAL", bg=COLORS["ready_bg"], fg=COLORS["green"])
            else:
                badge = "MENUNGGU TELEMETRY" if port_open else "TERPUTUS"
                self.safety_badge.configure(text=badge, bg=COLORS["panel_2"], fg=COLORS["muted"])
                self.data_stale = True
                self.last_any_telemetry_monotonic = None
                self.last_telemetry_monotonic = None
                self.current_therapy_session_id = None
                self._prev_therapy_running = None
            message = str(status.get("message", ""))
            if message:
                message_lower = message.lower()
                if estop or any(token in message_lower for token in ("ditolak", "tidak valid", "terputus", "kesalahan")):
                    status_color = COLORS["red"]
                else:
                    status_color = COLORS["green"] if connected else COLORS["muted"]
                self._set_status(message, status_color)
            if kind == "DEMO" and connected and not estop:
                self.auto_message_label.configure(text="Mode demo siap. Kalibrasi sensor atau pilih mode operasi.")
            elif kind == "SERIAL" and connected and not estop:
                self.auto_message_label.configure(text="Telemetry STM32 aktif. Kontrol serial siap.")
            elif kind == "SERIAL" and port_open and not estop:
                self.auto_message_label.configure(text="Port serial terbuka. Menunggu telemetry kontrol STM32.")
            self._refresh_system_health()

        def _handle_session_time_lifecycle(self, t: Telemetry, control_frame: bool) -> None:
            if not control_frame:
                return

            therapy_running_now = bool(
                t.therapy_running is True
                and t.system_state == "SYSTEM_THERAPY"
                and (t.selected_mode in {"AUTO", "MANUAL"} or self.system_mode in {"AUTO", "MANUAL"})
                and self.system_mode != "EMERGENCY"
            )

            prev_running = self._prev_therapy_running

            if prev_running is None:
                # First control telemetry frame observed
                if therapy_running_now:
                    # Connected mid-session: start time and session ID unknown
                    self.session_started_at = None
                    self.session_elapsed_frozen_s = None
                    self.session_time_known = False
                    self.current_therapy_session_id = None
                else:
                    # Connected while stopped/idle
                    self.session_started_at = None
                    self.session_elapsed_frozen_s = None
                    self.session_time_known = False
                    self.current_therapy_session_id = None
            elif not prev_running and therapy_running_now:
                # Fresh therapy session start transition observed
                self.session_started_at = time.monotonic()
                self.session_elapsed_frozen_s = None
                self.session_time_known = True
                self.current_therapy_session_id = generate_therapy_session_id()
                self.last_therapy_session_id = self.current_therapy_session_id
            elif prev_running and not therapy_running_now:
                # Session ended (stop, completion, or emergency)
                if self.session_started_at is not None and self.session_time_known:
                    self.session_elapsed_frozen_s = max(0, int(time.monotonic() - self.session_started_at))
                self.session_started_at = None
                self.last_therapy_session_id = self.current_therapy_session_id
                self.current_therapy_session_id = None

            self._prev_therapy_running = therapy_running_now

        def _handle_telemetry(self, update: Mapping[str, Any]) -> None:
            now = time.monotonic()
            self.last_any_telemetry_monotonic = now
            control_frame = is_complete_control_telemetry(update)

            if control_frame:
                self.last_telemetry_monotonic = now
                self.data_stale = False
                self.stale_stop_sent = False
                fresh = Telemetry()
                fresh.merge(update)
                # FSM firmware adalah sumber utama. Phase hanya fallback jika key FSM tidak ada.
                fresh.fsm_state = telemetry_fsm_state(update)
                self.telemetry = fresh
            else:
                # Partial/legacy frames may update non-safety fields such as RMS/status.
                self.telemetry.merge(update)

            t = self.telemetry
            previous_system_mode = self.system_mode
            fsm = raw_fsm_state(t.fsm_state or telemetry_fsm_state(update))
            reset_confirmed = telemetry_confirms_estop_reset(t.emergency, t.output_active, fsm)
            if control_frame:
                self.selected_mode = normalize_selected_mode(t.selected_mode)
                derived_mode = derive_system_mode(t)
                if self.manager.estop_latched and not (self.pending_reset_estop and reset_confirmed):
                    self.system_mode = "EMERGENCY"
                else:
                    self.system_mode = derived_mode
                self._update_mode_indicator()
                self._refresh_mode_label()

            # Kalibrasi tidak memakai handshake. Command dikirim langsung dan
            # penyelesaian dibaca dari telemetry nyata STM32.
            if control_frame and self.pending_calibration is not None:
                pending_cal = self.pending_calibration
                mvc_ready_now = t.mvc_ready if t.mvc_ready is not None else t.emg_calibrated
                done = False
                done_text = ""
                if pending_cal == "CALIBRATE_ANGLE" and t.angle_calibrated is True:
                    done = True
                    done_text = "Kalibrasi sudut selesai. IMU siap digunakan."
                elif pending_cal == "CAPTURE_MVC" and mvc_ready_now is True:
                    done = True
                    mvc_text = "" if t.mvc_value_mv is None else f" ({t.mvc_value_mv:.3f} mV)"
                    done_text = f"Pengambilan nilai MVC selesai{mvc_text}."
                elif pending_cal == "CALIBRATE_EMG" and (t.emg_status or "").upper() == "READY":
                    done = True
                    done_text = "Rekalibrasi EMG selesai. Ambil Nilai MVC kembali sebelum Mode Auto."

                cal_fault = (t.fault or "").upper()
                emg_state_now = (t.emg_status or "").upper()
                failed = (
                    (cal_fault not in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"} and "CAL" in cal_fault)
                    or "FAULT" in emg_state_now
                )
                if done:
                    self.pending_calibration = None
                    self.pending_calibration_label = ""
                    self.pending_calibration_deadline = None
                    self.calibration_message.configure(text=done_text, fg=COLORS["green"])
                    self._set_status(done_text, COLORS["green"])
                elif failed:
                    label = self.pending_calibration_label or "Kalibrasi"
                    self.pending_calibration = None
                    self.pending_calibration_label = ""
                    self.pending_calibration_deadline = None
                    detail = cal_fault if cal_fault not in {"", "NONE"} else emg_state_now
                    text = f"{label} gagal: {detail}."
                    self.calibration_message.configure(text=text, fg=COLORS["red"])
                    self._set_status(text, COLORS["red"])

            # STM32 adalah sumber kebenaran status emergency.
            phase_upper = (t.phase or "").strip().upper()
            fault_upper = (t.fault or "").strip().upper()
            emergency_active = (
                t.emergency is True
                or t.system_state == "SYSTEM_EMERGENCY"
                or (t.emergency is None and (phase_upper in {"E_STOP", "ESTOP"} or fault_upper == "EMERGENCY"))
            )
            if control_frame and emergency_active:
                self.manager.estop_latched = True
                self.system_mode = "EMERGENCY"
                self.auto_running = False
                self.pending_mode = None
                self.pending_start_deadline = None
                self.pending_stop_deadline = None
                self.estop_output_confirmed = (t.output_active is False)
                source = t.emergency_source or "--"
                self.safety_badge.configure(
                    text="OUTPUT OFF · E-STOP" if t.output_active is False else "E-STOP",
                    bg=COLORS["red_dark"], fg=COLORS["white"],
                )
                self.auto_phase_label.configure(text="E-STOP · OFF" if t.output_active is False else "E-STOP", fg=COLORS["red"])
                self.auto_message_label.configure(text=f"Emergency aktif · source={source}. Reset tersedia setelah output OFF.")
                self._refresh_mode_label()
                self._refresh_control_state(force=True)

            elif (
                control_frame
                and self.pending_reset_estop
                and reset_confirmed
            ):
                self._clear_confirmed_estop_reset_state()
                self.estop_output_confirmed = True
                self.auto_phase_label.configure(text="IDLE", fg=COLORS["green"])
                self.auto_message_label.configure(text="Emergency OFF. Sistem kembali IDLE dan output tetap OFF.")
                self.safety_badge.configure(text="SAFE · OUTPUT OFF", bg=COLORS["ready_bg"], fg=COLORS["green"])
                self._set_status("RESET E-STOP dikonfirmasi STM32.", COLORS["green"])
                self._refresh_mode_label()
                self._refresh_control_state(force=True)

            # Session confirmation and stop handling.
            if (
                control_frame
                and self.pending_stop_deadline is not None
                and self.system_mode in {"WAIT", "STANDBY"}
                and t.output_active is False
                and fsm_is_safe_stopped(fsm)
            ):
                self.pending_stop_deadline = None
                self.auto_running = False
                self.auto_phase_label.configure(text="IDLE", fg=COLORS["green"])
                self.auto_message_label.configure(text="Sesi berhenti; output OFF dikonfirmasi MCU.")
                self._set_status("STOP dikonfirmasi: FSM safe-stopped dan output OFF.", COLORS["green"])
                self._refresh_mode_label()
            elif control_frame and self.pending_mode is not None and self.system_mode == self.pending_mode:
                confirmed_mode = self.pending_mode
                self.pending_mode = None
                self.pending_start_deadline = None
                self.auto_running = confirmed_mode == "AUTO"
                if confirmed_mode == "AUTO" and fsm == "WAITING_INTENT":
                    self._set_status("Mode Auto aktif; FSM menunggu niat gerak.", COLORS["green"])
                else:
                    self._set_status(f"Mode {confirmed_mode.title()} aktif; FSM {fsm}.", COLORS["green"])
                self._refresh_mode_label()
            elif (
                control_frame
                and self.pending_mode is not None
                and (t.start_block or "").upper() not in {"", "OK", "NONE", "0"}
                and t.output_active is False
                and fsm_is_safe_stopped(fsm)
            ):
                rejected_mode = self.pending_mode
                reason = t.start_block.upper()
                self.pending_mode = None
                self.pending_start_deadline = None
                self.auto_running = False
                self._set_status(f"START {rejected_mode} ditolak MCU: {reason}.", COLORS["red"])
                self.auto_message_label.configure(text=f"START ditolak. Alasan MCU: {reason}.")
                self._refresh_mode_label()
            elif (
                control_frame
                and previous_system_mode in {"AUTO", "MANUAL"}
                and self.system_mode in {"WAIT", "STANDBY"}
                and fsm_is_safe_stopped(fsm)
                and t.output_active is False
                and phase_confirms_stopped(t.phase)
            ):
                prior = previous_system_mode
                self.auto_running = False
                self._set_status(f"Mode {prior.title()} selesai; MCU kembali IDLE.", COLORS["green"])
                self._refresh_mode_label()
            elif (
                control_frame
                and self.system_mode in {"WAIT", "STANDBY"}
                and self.pending_mode is None
                and t.output_active is True
            ):
                self.emergency_stop("unexpected_output_active")
                self._set_status("Output aktif tanpa START GUI; E-STOP dikirim.", COLORS["red"])

            self._handle_session_time_lifecycle(t, control_frame)

            # Main metrics.
            if t.current_cmd_ma is not None:
                self.current_card.set(f"{t.current_cmd_ma:.2f}")
            if t.angle_deg is not None:
                self.angle_card.set(f"{t.angle_deg:.1f}")
            if t.emg_rms_mv is not None:
                self.emg_card.set(f"{t.emg_rms_mv:.3f}")
            if t.emg_mav_mv is not None:
                self.mav_card.set(f"{t.emg_mav_mv:.3f}")
            if t.frequency_output_hz is not None:
                self.frequency_card.set(f"{t.frequency_output_hz:.1f}")
            pulse_width_value = t.pulse_width_us
            if pulse_width_value is None:
                pwm_compat = t.pwm_pct if t.pwm_pct is not None else t.pwm_command_pct
                if pwm_compat is not None:
                    pulse_width_value = pwm_pct_to_us(pwm_compat)
            if pulse_width_value is not None:
                self.pwm_card.set(f"{pulse_width_value:.1f}")
            target_angle = t.angle_target_deg
            angle_error = t.angle_error_deg
            fsm_color = (
                COLORS["red"] if fsm == "EMERGENCY"
                else COLORS["blue"] if fsm in FSM_ACTIVE_FAMILY
                else COLORS["green"] if fsm in FSM_REST_FAMILY or fsm_is_safe_stopped(fsm)
                else COLORS["yellow"]
            )

            # Formatted values for display
            target_str = f"{target_angle:.1f} °" if target_angle is not None else "--- °"
            error_str = f"{angle_error:.1f} °" if angle_error is not None else "--- °"
            
            # Delta error strictly from STM32 telemetry (no local calculation fallback)
            delta_error = t.delta_error_deg
            derror_str = f"{delta_error:.2f} °" if delta_error is not None else "--- °"

            mvc_str = f"{t.mvc_value_mv:.3f} mV" if t.mvc_value_mv is not None else "--- mV"
            angle_str = f"{t.angle_deg:.1f} °" if t.angle_deg is not None else "--- °"
            rms_str = f"{t.emg_rms_mv:.3f} mV" if t.emg_rms_mv is not None else "--- mV"
            mav_str = f"{t.emg_mav_mv:.3f} mV" if t.emg_mav_mv is not None else "--- mV"

            # Fatigue formatting
            if t.fatigue_flag is True:
                fatigue_text = "FATIGUE"
                fatigue_color = COLORS["red"]
            elif t.fatigue_state and str(t.fatigue_state).upper() != "WAITING":
                fatigue_text = str(t.fatigue_state).upper()
                fatigue_color = COLORS["red"] if fatigue_text in {"CONFIRMED", "DETECTED", "FATIGUE"} else COLORS["green"]
            elif t.fatigue_flag is False:
                fatigue_text = "NORMAL"
                fatigue_color = COLORS["green"]
            elif "fatigue_state" in update:
                fatigue_text = str(t.fatigue_state).upper()
                fatigue_color = COLORS["yellow"]
            else:
                fatigue_text = "---"
                fatigue_color = COLORS["muted"]
            fatigue_count_str = str(t.fatigue_count) if t.fatigue_count is not None else "---"

            # Timer & remaining formatting (Integer seconds only, no decimals)
            is_therapy_running = bool(t.therapy_running is True and self.system_mode in {"AUTO", "MANUAL"})
            if is_therapy_running:
                timer_str = format_elapsed_ms(t.therapy_timer_ms)
                remaining_str = format_remaining_ms(t.state_remaining_ms)
            elif self.system_mode in {"STANDBY", "WAIT"}:
                timer_str = "0 s"
                remaining_str = "0 s"
            else:
                timer_str = format_elapsed_ms(t.therapy_timer_ms)
                remaining_str = format_remaining_ms(t.state_remaining_ms)

            # FES Output uses only explicit output telemetry. Health remains
            # sourced separately and strictly from fes_status.
            if t.output_active is True:
                fes_text = "ACTIVE"
                fes_color = COLORS["blue"]
            elif t.output_active is False:
                fes_text = "OFF"
                fes_color = COLORS["green"]
            else:
                fes_text = "---"
                fes_color = COLORS["muted"]

            # Signal quality
            excessive_clipping = has_excessive_clipping(t.emg_error_flags)
            if excessive_clipping:
                clipping_text = (
                    "CLIPPING"
                    if t.clipping_percent_1s is None
                    else f"CLIPPING {t.clipping_percent_1s:.2f}%"
                )
                quality_text = clipping_text
                quality_color = COLORS["red"]
            else:
                quality_text = t.signal_quality or "--"
                quality_color = COLORS["green"] if quality_text.upper() in {"GOOD", "BAIK", "OK", "VALID"} else COLORS["yellow"]

            # FSM display formatting (e.g. ACTIVE_NORMAL -> ACTIVE NORMAL)
            display_fsm = fsm.replace("_", " ")

            # H-Bridge status - strictly use telemetry, never infer from MCP4725
            raw_hbridge = (t.hbridge_status or "").strip().upper()
            if raw_hbridge in {"", "WAITING", "UNKNOWN", "--"}:
                hbridge_text = "---"
            else:
                hbridge_text = t.hbridge_status

            # Manual kondisi derived strictly from Manual state:
            # MANUAL_ACTIVE -> ACTIVE, MANUAL_REST -> REST, IDLE/safe stopped -> IDLE, AUTO states -> "---"
            if fsm == "MANUAL_ACTIVE":
                manual_kondisi = "ACTIVE"
                manual_kondisi_color = COLORS["blue"]
            elif fsm in {"MANUAL_REST", "REST"} and (t.phase or "").upper().startswith("MANUAL"):
                manual_kondisi = "REST"
                manual_kondisi_color = COLORS["green"]
            elif fsm == "MANUAL_REST":
                manual_kondisi = "REST"
                manual_kondisi_color = COLORS["green"]
            elif fsm in FSM_SAFE_STOPPED or fsm == "IDLE":
                manual_kondisi = "IDLE"
                manual_kondisi_color = COLORS["muted"]
            else:
                # AUTO FSM states (WAITING_INTENT, ACTIVE_NORMAL, ACTIVE_FATIGUE, FATIGUE_REST, etc.)
                # must NOT display as Manual Kondisi.
                manual_kondisi = "---"
                manual_kondisi_color = COLORS["muted"]

            # Remaining / Duration formatting
            is_therapy_running = bool(t.therapy_running is True and self.system_mode in {"AUTO", "MANUAL"})
            if is_therapy_running:
                rem_dur_str = format_remaining_duration(t.therapy_timer_ms, t.state_remaining_ms)
            else:
                rem_dur_str = "---"

            # DAC Command Voltage formatting (real firmware does not provide yet -> "--- V")
            dac_v_str = f"{t.dac_voltage_v:.3f} V" if t.dac_voltage_v is not None else "--- V"

            # IMU / MVC Calibration text
            imu_cal_str = "SUDAH" if t.angle_calibrated is True else "BELUM" if t.angle_calibrated is False else "--"
            mvc_ready = t.mvc_ready if t.mvc_ready is not None else t.emg_calibrated
            mvc_cal_str = "SUDAH" if mvc_ready is True else "BELUM" if mvc_ready is False else "--"

            # IMU angle strings (value only, no status prefix)
            imu_a_str = f"{t.imu_a_angle_deg:+.1f}°" if t.imu_a_angle_deg is not None else "-- °"
            imu_b_str = f"{t.imu_b_angle_deg:+.1f}°" if t.imu_b_angle_deg is not None else "-- °"

            # Offset from STM32 g_zero_offset
            if t.angle_calibrated is True and t.imu_zero_offset_deg is not None:
                offset_str = f"{t.imu_zero_offset_deg:+.1f}°"
            else:
                offset_str = "--- °"

            # Emergency source string
            src = t.emergency_source
            if src in {3, "3"} or str(src).strip().upper() == "GUI":
                emergency_source_str = "GUI"
            elif src in {2, "2"} or str(src).strip().upper() == "FSM":
                emergency_source_str = "FSM"
            elif src and str(src).strip().upper() not in {"", "0", "NONE", "NULL"}:
                emergency_source_str = str(src).strip().upper()
            else:
                emergency_source_str = "---"

            # Fault code string (no invented values)
            fault_raw = (t.fault or "").strip()
            if fault_raw and fault_raw.upper() not in {"", "NONE", "0", "OK", "NULL"}:
                fault_code_str = fault_raw
            else:
                fault_code_str = "---"
            actual_system_state = (t.system_state or "---").strip() or "---"

            # -------------------------------------------------------------
            # 1. AUTO PAGE (Right panel always shows Auto Information)
            # -------------------------------------------------------------
            if self.system_mode == "AUTO" and fsm == "WAITING_INTENT":
                self.auto_message_label.configure(text="Auto aktif. FSM menunggu niat gerak dari EMG.")

            self.auto_info_fsm.configure(text=display_fsm, fg=fsm_color)
            self.auto_info_target.configure(text=target_str)
            self.auto_info_error.configure(text=error_str)
            self.auto_info_derror.configure(text=derror_str)
            self.auto_info_mvc.configure(text=mvc_str)
            self.auto_info_fatigue.configure(text=fatigue_text, fg=fatigue_color)
            self.auto_info_fatigue_count.configure(text=fatigue_count_str)
            self.auto_info_rem_dur.configure(text=rem_dur_str)
            self.auto_info_dac_v.configure(text=dac_v_str)
            self.fes_output_label.configure(text=fes_text, fg=fes_color)

            # -------------------------------------------------------------
            # 2. MANUAL PAGE (Right panel always shows Manual Information)
            # -------------------------------------------------------------
            self.manual_kondisi_live.configure(text=manual_kondisi, fg=manual_kondisi_color)
            self.manual_rem_dur_live.configure(text=rem_dur_str)
            self.manual_dac_v_live.configure(text=dac_v_str)
            self.manual_output_live.configure(text=fes_text, fg=fes_color)

            # -------------------------------------------------------------
            # 3. SENSOR PREPARATION PAGE (Always shows Monitoring Information)
            # -------------------------------------------------------------
            self.cal_imu_a.configure(text=imu_a_str)
            self.cal_imu_b.configure(text=imu_b_str)
            self.cal_offset.configure(text=offset_str)
            self.cal_mvc.configure(text=mvc_str)
            self.cal_imu_cal.configure(text=imu_cal_str)
            self.cal_mvc_cal.configure(text=mvc_cal_str)

            # -------------------------------------------------------------
            # 4. EMG MONITORING PAGE (Right panel adapts by system_mode)
            # -------------------------------------------------------------
            # Update WAIT panel (Monitoring Information)
            self.emg_wait_imu_a.configure(text=imu_a_str)
            self.emg_wait_imu_b.configure(text=imu_b_str)
            self.emg_wait_offset.configure(text=offset_str)
            self.emg_wait_mvc.configure(text=mvc_str)
            self.emg_wait_imu_cal.configure(text=imu_cal_str)
            self.emg_wait_mvc_cal.configure(text=mvc_cal_str)
            self.emg_wait_quality.configure(text=quality_text, fg=quality_color)

            # Update STANDBY panel (Monitoring Information)
            self.emg_standby_imu_a.configure(text=imu_a_str)
            self.emg_standby_imu_b.configure(text=imu_b_str)
            self.emg_standby_offset.configure(text=offset_str)
            self.emg_standby_mvc.configure(text=mvc_str)
            self.emg_standby_imu_cal.configure(text=imu_cal_str)
            self.emg_standby_mvc_cal.configure(text=mvc_cal_str)
            self.emg_standby_fes.configure(text=fes_text, fg=fes_color)
            self.emg_standby_quality.configure(text=quality_text, fg=quality_color)

            # Update AUTO panel (Auto Information)
            self.emg_auto_fsm.configure(text=display_fsm, fg=fsm_color)
            self.emg_auto_target.configure(text=target_str)
            self.emg_auto_error.configure(text=error_str)
            self.emg_auto_derror.configure(text=derror_str)
            self.emg_auto_mvc.configure(text=mvc_str)
            self.emg_auto_fatigue.configure(text=fatigue_text, fg=fatigue_color)
            self.emg_auto_fatigue_count.configure(text=fatigue_count_str)
            self.emg_auto_rem_dur.configure(text=rem_dur_str)
            self.emg_auto_dac_v.configure(text=dac_v_str)
            self.emg_auto_fes.configure(text=fes_text, fg=fes_color)
            self.emg_auto_quality.configure(text=quality_text, fg=quality_color)

            # Update MANUAL panel (Manual Information)
            self.emg_manual_kondisi.configure(text=manual_kondisi, fg=manual_kondisi_color)
            self.emg_manual_rem_dur.configure(text=rem_dur_str)
            self.emg_manual_dac_v.configure(text=dac_v_str)
            self.emg_manual_fes.configure(text=fes_text, fg=fes_color)
            self.emg_manual_quality.configure(text=quality_text, fg=quality_color)

            # Update EMERGENCY panel (Emergency Information)
            self.emg_emg_source.configure(text=emergency_source_str)
            self.emg_emg_fault.configure(text=fault_code_str)
            self.emg_emg_fes.configure(text=fes_text, fg=COLORS["red"])
            self.emg_emg_fsm.configure(text=display_fsm, fg=COLORS["red"])
            self.emg_emg_status.configure(text=actual_system_state, fg=COLORS["red"])

            # Raise the appropriate adaptive EMG right panel according to system_mode
            emg_mode = self.system_mode if self.system_mode in self.emg_right_panels else "WAIT"
            self.emg_right_panels[emg_mode].tkraise()

            # Green EMG status text (inside graph area)
            if fsm == "EMERGENCY":
                movement_text = "EMERGENCY"
                movement_color = COLORS["red"]
            elif fsm in FSM_ACTIVE_FAMILY:
                movement_text = "KONTRAKSI · ACTIVE"
                movement_color = COLORS["blue"]
            elif fsm in FSM_REST_FAMILY:
                movement_text = "RELAKSASI · REST"
                movement_color = COLORS["green"]
            elif fsm in FSM_SAFE_STOPPED or fsm == "WAITING_INTENT":
                movement_text = "MENUNGGU GERAKAN"
                movement_color = COLORS["yellow"]
            else:
                movement_text = display_fsm
                movement_color = COLORS["yellow"]
            self.movement_wait_label.configure(text=movement_text, fg=movement_color)
            self.quality_label.configure(text=f"Signal quality: {quality_text}", fg=quality_color)
            self.emg_plot.add(t.emg_rms_mv)

            # Safety checks retained, fatigue logic removed.
            fault = (t.fault or "").strip().upper()
            calibration_fault_bypassed = self.system_mode == "MANUAL" and fault.startswith("CAL_")
            if (
                control_frame
                and fault not in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"}
                and not calibration_fault_bypassed
                and (self.system_mode in {"AUTO", "MANUAL"} or self.pending_stop_deadline is not None)
            ):
                self.emergency_stop("mcu_fault")
                self._set_status(f"Fault MCU aktif: {fault}.", COLORS["red"])
            quality = (t.signal_quality or "").strip().upper()
            if (
                control_frame
                and should_estop_for_emg_quality(quality, t.emg_error_flags)
                and self.system_mode == "AUTO"
            ):
                self.emergency_stop("emg_quality_invalid")
                self._set_status(f"Kualitas EMG {quality}; E-STOP aktif.", COLORS["red"])
            self._refresh_system_health()
            log_sample = Telemetry()
            log_sample.merge(update)
            log_sample.fsm_state = raw_fsm_state(t.fsm_state or telemetry_fsm_state(update))

            log_session_id = self.current_therapy_session_id or ""
            if self.session_started_at is not None and self.session_time_known:
                log_session_time: Union[int, str] = max(0, int(time.monotonic() - self.session_started_at))
            else:
                log_session_time = ""

            self.logger.log(
                log_sample,
                source="demo" if self.manager.connection_kind == "DEMO" else "serial",
                connection=self.manager.port_name or "none",
                mode=self.system_mode,
                session_id=log_session_id,
                session_time_s=log_session_time,
            )

        def _set_health(self, key: str, text: str, level: str = "muted") -> None:
            color = {"ok": COLORS["green"], "warn": COLORS["yellow"], "bad": COLORS["red"], "muted": COLORS["muted"]}.get(level, COLORS["muted"])
            label = self.health_labels.get(key)
            if label is not None:
                label.configure(text=text, fg=color)

        def _refresh_system_health(self) -> None:
            state = self.manager.state()
            connected = bool(state.get("connected"))
            kind = str(state.get("kind", "DISCONNECTED"))
            now = time.monotonic()
            link_live = bool(
                connected
                and self.last_any_telemetry_monotonic is not None
                and now - self.last_any_telemetry_monotonic <= DATA_STALE_SECONDS
            )

            t = self.telemetry
            if not connected:
                self._set_health("MCU", "OFFLINE", "bad")
            elif kind == "DEMO":
                self._set_health("MCU", "DEMO", "ok")
            elif link_live or (t.mcu_status or "").upper() in {"ONLINE", "OK", "READY"}:
                self._set_health("MCU", "ONLINE", "ok")
            else:
                self._set_health("MCU", "PORT OPEN", "warn")

            if not connected:
                self._set_health("DATA", "OFF", "bad")
            elif link_live:
                self._set_health("DATA", "LIVE", "ok")
            else:
                self._set_health("DATA", "WAIT", "warn")

            def sensor_level(text: str) -> str:
                u = (text or "").upper()
                if u in {"READY", "ACTIVE", "ONLINE", "LIVE", "GOOD", "BAIK", "VALID", "OK", "RUNNING"}: return "ok"
                if u in {"WAITING", "WAIT", "CALIBRATING", "INIT", "UNKNOWN", "--", "", "PORT OPEN", "OFF", "NOT_READY", "BYPASS"}: return "warn"
                return "bad"

            def normalize_healthy(status_str: str) -> str:
                u = (status_str or "").strip().upper()
                if u in {"OK", "READY", "GOOD", "BAIK", "VALID"}:
                    return "READY"
                return status_str or "--"

            imu_a_health = normalize_healthy(t.imu_a_status)
            self._set_health("IMU_A", imu_a_health, sensor_level(imu_a_health))
            imu_b_health = normalize_healthy(t.imu_b_status)
            self._set_health("IMU_B", imu_b_health, sensor_level(imu_b_health))

            if has_excessive_clipping(t.emg_error_flags):
                emg_text = (
                    "CLIPPING"
                    if t.clipping_percent_1s is None
                    else f"CLIPPING {t.clipping_percent_1s:.2f}%"
                )
            elif t.emg_status:
                emg_text = normalize_healthy(t.emg_status)
            elif (t.signal_quality or "").upper() in {"GOOD", "BAIK", "OK", "VALID"}:
                emg_text = "READY"
            elif t.emg_rms_mv is not None and link_live:
                emg_text = "LIVE"
            else:
                emg_text = t.signal_quality or "--"
            self._set_health("EMG", emg_text, sensor_level(emg_text))

            # MCP health: normalize OK -> READY, preserve BYPASS and ERROR truthfully
            mcp_health = (t.mcp4725_status or "--").strip()
            if mcp_health.upper() in {"OK", "READY"}:
                mcp_health = "READY"
            self._set_health("MCP", mcp_health, sensor_level(mcp_health))
            
            # H-Bridge health: normalize OK -> READY, preserve RUNNING / NOT_READY / FAULT
            hbridge_health = (t.hbridge_status or "--").strip()
            if hbridge_health.upper() in {"OK", "READY"}:
                hbridge_health = "READY"
            elif hbridge_health.upper() in {"", "WAITING", "UNKNOWN"}:
                hbridge_health = "--"
            self._set_health("HBRIDGE", hbridge_health, sensor_level(hbridge_health))
            
            # FES health: normalize OK -> READY, preserve ACTIVE / FAULT / OFF
            raw_fes_health = (t.fes_status or "").strip().upper()
            if raw_fes_health in {"", "WAITING", "UNKNOWN", "--"}:
                fes_health = "--"
            elif raw_fes_health in {"OK", "READY"}:
                fes_health = "READY"
            else:
                fes_health = t.fes_status
            self._set_health("FES", fes_health, sensor_level(fes_health))

            fault = (t.fault or "").upper()
            if self.manager.estop_latched or self.system_mode == "EMERGENCY":
                self._set_health("SAFETY", "E-STOP", "bad")
            elif fault not in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"}:
                self._set_health("SAFETY", "FAULT", "bad")
            elif not self.data_stale and (t.phase or "").upper() in {"IDLE", "SAFE_IDLE", "AUTO", "RUNNING_AUTO", "AUTO_RUNNING", "MANUAL", "RUNNING_MANUAL", "MANUAL_RUNNING"}:
                self._set_health("SAFETY", "SAFE", "ok")
            elif connected:
                self._set_health("SAFETY", "MONITOR", "warn")
            else:
                self._set_health("SAFETY", "WAIT", "warn")

        def _refresh_control_state(self, force: bool = False) -> None:
            allowed = (
                self.manager.can_control()
                and not self.data_stale
                and self.pending_mode is None
                and self.pending_stop_deadline is None
                and self.system_mode == "STANDBY"
                and self._start_snapshot_safe()
            )
            reset_allowed = self._fresh_estop_off_confirmation() and not self.pending_reset_estop
            self.reset_estop_button.configure(
                state="normal" if reset_allowed else "disabled",
                bg=COLORS["yellow"] if reset_allowed else COLORS["panel_2"],
                fg="#231A00" if reset_allowed else COLORS["muted"],
            )
            if not force and allowed == self.last_ui_control_state:
                return
            self.last_ui_control_state = allowed
            state = "normal" if allowed else "disabled"
            for widget in self.control_widgets:
                try:
                    widget.configure(state=state)
                except tk.TclError:
                    pass

        def _mark_control_values_stale(self) -> None:
            if self.system_mode == "EMERGENCY":
                self.estop_output_confirmed = False
                self.safety_badge.configure(text="OUTPUT UNKNOWN · E-STOP", bg=COLORS["red_dark"], fg=COLORS["white"])
            self.current_card.set("--")
            self.angle_card.set("--")
            self.emg_card.set("--")
            self.mav_card.set("--")
            self.pwm_card.set("--")
            self.frequency_card.set("--")
            self.quality_label.configure(text="Signal quality: data stale")
            self.movement_wait_label.configure(text="MENUNGGU DATA", fg=COLORS["muted"])
            self._refresh_system_health()

        def _check_data_health(self) -> None:
            state = self.manager.state()
            output_may_be_active = bool(
                self.system_mode in {"AUTO", "MANUAL"}
                or self.pending_mode is not None
                or self.pending_stop_deadline is not None
            )
            if not state.get("connected"):
                self.data_stale = True
                if not self.manager.estop_latched and not output_may_be_active:
                    self.system_mode = "WAIT"
                    self._refresh_mode_label()
                self._mark_control_values_stale()
                if output_may_be_active and not self.stale_stop_sent:
                    self.stale_stop_sent = True
                    self.emergency_stop("link_lost")
                    self.safety_badge.configure(
                        text="OUTPUT UNKNOWN", bg=COLORS["red_dark"], fg=COLORS["white"],
                    )
                return
            if self.last_telemetry_monotonic is None:
                self.data_stale = True
                if not self.manager.estop_latched:
                    self.system_mode = "WAIT"
                    self._refresh_mode_label()
                self._mark_control_values_stale()
                return
            age = time.monotonic() - self.last_telemetry_monotonic
            was_stale = self.data_stale
            self.data_stale = age > DATA_STALE_SECONDS
            if self.data_stale and not was_stale:
                self._set_status(f"DATA STALE {age:.1f} s · kontrol dikunci.", COLORS["red"])
                if not self.manager.estop_latched and not output_may_be_active:
                    self.system_mode = "WAIT"
                    self._refresh_mode_label()
                self._mark_control_values_stale()
            if (
                self.data_stale
                and output_may_be_active
                and not self.stale_stop_sent
            ):
                self.stale_stop_sent = True
                self.emergency_stop("telemetry_stale")
            if age > DATA_ABORT_SECONDS and self.manager.connection_kind == "SERIAL":
                self.safety_badge.configure(text="OUTPUT UNKNOWN", bg=COLORS["red_dark"], fg=COLORS["white"])

        def _check_pending_calibration(self) -> None:
            if self.pending_calibration is None or self.pending_calibration_deadline is None:
                return
            if time.monotonic() < self.pending_calibration_deadline:
                return
            label = self.pending_calibration_label or "Kalibrasi"
            self.pending_calibration = None
            self.pending_calibration_label = ""
            self.pending_calibration_deadline = None
            text = (
                f"{label}: belum ada perubahan status dari STM32. "
                "Cek jalur UART TX/RX dan baud 115200; bila perlu tekan RESET STM32 sekali."
            )
            self.calibration_message.configure(text=text, fg=COLORS["red"])
            self._set_status(text, COLORS["red"])

        def _check_pending_reset_estop(self) -> None:
            if not self.pending_reset_estop or self.pending_reset_deadline is None:
                return
            if time.monotonic() < self.pending_reset_deadline:
                return
            self.pending_reset_estop = False
            self.pending_reset_deadline = None
            self._set_status("RESET E-STOP tidak dikonfirmasi STM32.", COLORS["red"])
            self.auto_phase_label.configure(text="E-STOP", fg=COLORS["red"])
            self.auto_message_label.configure(
                text="STM32 masih melaporkan emergency. Periksa tombol fisik/penyebab emergency lalu coba Reset E-STOP lagi.",
            )
            self._refresh_control_state(force=True)

        def _check_pending_start(self) -> None:
            if self.pending_mode is None or self.pending_start_deadline is None:
                return
            if time.monotonic() < self.pending_start_deadline:
                return
            pending = self.pending_mode
            self.pending_mode = None
            self.pending_start_deadline = None
            if self.telemetry.output_active is False and phase_confirms_stopped(self.telemetry.phase):
                self.auto_running = False
                self._refresh_mode_label()
                self._set_status(
                    f"START {pending} tidak diterima MCU; output tetap OFF. Periksa status kalibrasi/parameter.",
                    COLORS["red"],
                )
                return
            self.emergency_stop("start_unconfirmed")
            self._set_status(
                f"START {pending} tidak dikonfirmasi; status output tidak aman sehingga E-STOP dikirim.",
                COLORS["red"],
            )

        def _check_pending_stop(self) -> None:
            if self.pending_stop_deadline is None:
                return
            if time.monotonic() < self.pending_stop_deadline:
                return
            self.pending_stop_deadline = None
            self.emergency_stop("stop_unconfirmed")
            self._set_status(
                "STOP tidak dikonfirmasi dalam 1 s; E-STOP dikirim dan output dianggap UNKNOWN.",
                COLORS["red"],
            )

        def _send_heartbeat_if_due(self) -> None:
            if self.data_stale or self.manager.connection_kind != "SERIAL":
                return
            now = time.monotonic()
            if now - self.last_heartbeat_sent < HEARTBEAT_INTERVAL_SECONDS:
                return
            sent, message = self.manager.send_heartbeat()
            if sent:
                self.last_heartbeat_sent = now
            elif self.system_mode in {"AUTO", "MANUAL"} or self.pending_stop_deadline is not None:
                self.emergency_stop("heartbeat_write_failed")
                self._set_status(f"Heartbeat gagal ({message}); E-STOP aktif.", COLORS["red"])

        def _update_timer(self) -> None:
            if self.session_started_at is not None and self.session_time_known:
                elapsed = max(0, int(time.monotonic() - self.session_started_at))
                text = f"{elapsed} s"
            elif self.session_elapsed_frozen_s is not None and self.session_time_known:
                text = f"{self.session_elapsed_frozen_s} s"
            else:
                text = "--- s"

            if hasattr(self, "session_time_label"):
                self.session_time_label.configure(text=text)
            if hasattr(self, "timer_label"):
                self.timer_label.configure(text=text)

        def _refresh_mode_label(self) -> None:
            self.mode_label.configure(text=f"MODE: {self.system_mode}",
                                      fg=COLORS["red"] if self.system_mode == "EMERGENCY" else COLORS["muted"])
            self._update_mode_indicator()
            if hasattr(self, "emg_right_panels"):
                emg_mode = self.system_mode if self.system_mode in self.emg_right_panels else "WAIT"
                self.emg_right_panels[emg_mode].tkraise()

        def _set_status(self, message: str, color: str) -> None:
            self.status_dot.configure(fg=color)
            self.status_label.configure(text=message, fg=color if color == COLORS["red"] else COLORS["muted"])

        def close(self) -> None:
            if self.logger.active:
                self.logger.stop()
            self.manager.disconnect()
            self.root.destroy()


def run_self_test() -> int:
    """Exercise parser, direct serial gate, FSM, and CSV without opening Tk."""
    checks = 0

    parsed = parse_telemetry_line(
        '{"type":"TEL","system_state":"SYSTEM_THERAPY","therapy_running":true,"mode":"AUTO",'
        '"current_cmd_ma":12.5,"angle_deg":42,"pw_pct":33,"pw_command_pct":31,"pulse_width_us":199,'
        '"frequency_set_hz":35,"frequency_output_hz":35,"fsm_state":"ACTIVE_NORMAL",'
        '"emg_rms_mv":0.48,"emg_mav_mv":0.42,"mav_ratio":0.35,"fatigue_flag":false,"fatigue_count":2,'
        '"therapy_timer_ms":7000,"state_remaining_ms":3000,'
        '"clipping_percent_1s":6.25,"emg_error_flags":64,"emg_status":"READY","signal_quality":"CLIPPING",'
        '"phase":"AUTO","output_active":true,"fault":"NONE","emergency":0,"emergency_source":0,'
        '"mcp4725_status":"OK","hbridge_status":"READY","fes_status":"ACTIVE","start_block":"BUSY",'
        '"active_duration_s":5,"rest_duration_s":4,"mvc_value_mv":1.2,"mvc_ready":true}'
    )
    assert parsed["current_cmd_ma"] == 12.5
    assert parsed["angle_deg"] == 42.0
    assert parsed["pwm_pct"] == 33.0
    assert parsed["pwm_command_pct"] == 31.0
    assert parsed["pulse_width_us"] == 199.0
    assert parsed["emergency"] is False
    assert parsed["system_state"] == "SYSTEM_THERAPY"
    assert parsed["therapy_running"] is True
    assert parsed["selected_mode"] == "AUTO"
    assert parsed["fsm_state"] == "ACTIVE_NORMAL"
    assert parsed["emg_mav_mv"] == 0.42
    assert parsed["mav_ratio"] == 0.35
    assert parsed["fatigue_flag"] is False
    assert parsed["fatigue_count"] == 2
    assert parsed["therapy_timer_ms"] == 7000
    assert parsed["state_remaining_ms"] == 3000
    assert parsed["active_duration_s"] == 5.0
    assert parsed["mvc_ready"] is True
    assert parsed["hbridge_status"] == "READY"
    assert parsed["frequency_set_hz"] == 35.0
    assert parsed["frequency_output_hz"] == 35.0
    assert parsed["start_block"] == "BUSY"
    assert parsed["clipping_percent_1s"] == 6.25
    assert should_estop_for_emg_quality("INVALID", 0)
    assert is_complete_control_telemetry(parsed)
    checks += 1

    # Current STM32 frames are larger than 1024 bytes. Verify both the parser
    # and the serial reader preserve one realistic 1266-byte TEL frame intact.
    large_payload: Dict[str, Any] = {
        "type": "TEL",
        "system_state": "SYSTEM_THERAPY",
        "therapy_running": True,
        "mode": "AUTO",
        "fsm_state": "ACTIVE_NORMAL",
        "current_cmd_ma": 12.5,
        "angle_deg": 42.0,
        "pw_pct": 33.0,
        "signal_quality": "GOOD",
        "phase": "AUTO",
        "output_active": True,
        "fault": "NONE",
        "padding": "",
    }
    base_large_frame = (json.dumps(large_payload, separators=(",", ":")) + "\n").encode("utf-8")
    large_payload["padding"] = "X" * (1266 - len(base_large_frame))
    large_frame = (json.dumps(large_payload, separators=(",", ":")) + "\n").encode("utf-8")
    assert len(large_frame) == 1266
    assert 1024 < len(large_frame) < SERIAL_FRAME_MAX_BYTES
    assert is_complete_control_telemetry(parse_telemetry_line(large_frame.decode("utf-8")))

    class ScriptedSerial:
        def __init__(self) -> None:
            self.incoming: "queue.Queue[bytes]" = queue.Queue()
            self.closed = threading.Event()
            self.read_sizes: list[int] = []
            self.writes: list[bytes] = []

        def reset_input_buffer(self) -> None:
            return None

        def read_until(self, expected: bytes = b"\n", size: Optional[int] = None) -> bytes:
            del expected
            if size is not None:
                self.read_sizes.append(size)
            try:
                return self.incoming.get(timeout=0.05)
            except queue.Empty:
                return b""

        def write(self, data: bytes) -> int:
            self.writes.append(bytes(data))
            return len(data)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            self.closed.set()

    class SerialFactory:
        def __init__(self, device: ScriptedSerial) -> None:
            self.device = device

        def Serial(self, **_kwargs: Any) -> ScriptedSerial:
            return self.device

    original_serial_module = serial
    reader_manager: Optional[SerialManager] = None
    try:
        reader_device = ScriptedSerial()
        globals()["serial"] = SerialFactory(reader_device)
        reader_manager = SerialManager(hardware_control_requested=False)
        opened, _ = reader_manager.connect_serial("COM_TEST", BAUD_RATE)
        assert opened
        assert reader_manager.port_open is True
        assert reader_manager.connected is False
        assert reader_manager.state()["telemetry_live"] is False
        calibration_sent, _ = reader_manager.send_command("CALIBRATE_ANGLE")
        assert calibration_sent is False
        assert not reader_device.writes

        reader_device.incoming.put(large_frame)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and not reader_manager.connected:
            time.sleep(0.005)
        assert reader_manager.connected is True
        assert reader_manager.state()["telemetry_live"] is True
        assert reader_device.read_sizes and set(reader_device.read_sizes) == {SERIAL_FRAME_MAX_BYTES}

        telemetry_seen = False
        while not reader_manager.events.empty():
            kind, payload = reader_manager.events.get_nowait()
            if kind == "telemetry" and is_complete_control_telemetry(payload):
                telemetry_seen = True
        assert telemetry_seen
    finally:
        if reader_manager is not None:
            reader_manager.disconnect()
        globals()["serial"] = original_serial_module

    truncated_manager: Optional[SerialManager] = None
    try:
        truncated_device = ScriptedSerial()
        globals()["serial"] = SerialFactory(truncated_device)
        truncated_manager = SerialManager(hardware_control_requested=False)
        opened, _ = truncated_manager.connect_serial("COM_TEST", BAUD_RATE)
        assert opened and truncated_manager.port_open and not truncated_manager.connected
        truncated_device.incoming.put(b"{" + (b"X" * (SERIAL_FRAME_MAX_BYTES - 1)))
        deadline = time.monotonic() + 1.0
        diagnostic = ""
        while time.monotonic() < deadline and not diagnostic:
            try:
                kind, payload = truncated_manager.events.get(timeout=0.05)
            except queue.Empty:
                continue
            if kind == "error":
                diagnostic = str(payload)
        assert "exceeded" in diagnostic and "truncated" in diagnostic
        assert truncated_manager.connected is False
    finally:
        if truncated_manager is not None:
            truncated_manager.disconnect()
        globals()["serial"] = original_serial_module

    malformed_manager: Optional[SerialManager] = None
    try:
        malformed_device = ScriptedSerial()
        globals()["serial"] = SerialFactory(malformed_device)
        malformed_manager = SerialManager(hardware_control_requested=False)
        opened, _ = malformed_manager.connect_serial("COM_TEST", BAUD_RATE)
        assert opened
        malformed_device.incoming.put(b'{"type":"TEL","broken":}\n')
        deadline = time.monotonic() + 1.0
        diagnostic = ""
        while time.monotonic() < deadline and not diagnostic:
            try:
                kind, payload = malformed_manager.events.get(timeout=0.05)
            except queue.Empty:
                continue
            if kind == "error":
                diagnostic = str(payload)
        assert "JSON malformed" in diagnostic
        assert malformed_manager.connected is False
    finally:
        if malformed_manager is not None:
            malformed_manager.disconnect()
        globals()["serial"] = original_serial_module

    parser_failure_manager: Optional[SerialManager] = None
    original_parser = parse_telemetry_line
    try:
        parser_failure_device = ScriptedSerial()
        globals()["serial"] = SerialFactory(parser_failure_device)

        def raising_parser(_line: str) -> Dict[str, Any]:
            raise RuntimeError("synthetic parser failure")

        globals()["parse_telemetry_line"] = raising_parser
        parser_failure_manager = SerialManager(hardware_control_requested=False)
        opened, _ = parser_failure_manager.connect_serial("COM_TEST", BAUD_RATE)
        assert opened
        parser_failure_device.incoming.put(large_frame)
        deadline = time.monotonic() + 1.0
        diagnostic = ""
        while time.monotonic() < deadline and not diagnostic:
            try:
                kind, payload = parser_failure_manager.events.get(timeout=0.05)
            except queue.Empty:
                continue
            if kind == "error":
                diagnostic = str(payload)
        assert "parser error" in diagnostic
        assert parser_failure_manager._thread is not None and parser_failure_manager._thread.is_alive()
        assert parser_failure_manager.connected is False
    finally:
        globals()["parse_telemetry_line"] = original_parser
        if parser_failure_manager is not None:
            parser_failure_manager.disconnect()
        globals()["serial"] = original_serial_module
    checks += 1

    assert normalize_fsm_state("contraction") == "KONTRAKSI"
    assert normalize_fsm_state("rest") == "RELAKSASI"
    assert normalize_fsm_state("safe_idle") == "IDLE"
    assert normalize_fsm_state("MANUAL_STOPPED") == "IDLE"
    assert normalize_fsm_state("E_STOP") == "EMERGENCY"
    assert telemetry_fsm_state({"fsm_state": "IDLE", "phase": "AUTO"}) == "IDLE"
    assert telemetry_fsm_state({"fsm_state": "MANUAL_STOPPED", "phase": "IDLE"}) == "MANUAL_STOPPED"
    assert telemetry_fsm_state({"fsm_state": "THERAPY_STOP", "phase": "IDLE"}) == "THERAPY_STOP"
    assert telemetry_fsm_state({"phase": "AUTO"}) == "UNKNOWN"
    assert telemetry_confirms_estop_reset(False, False, "IDLE")
    assert telemetry_confirms_estop_reset(False, False, "MANUAL_STOPPED")
    assert telemetry_confirms_estop_reset(False, False, "THERAPY_STOP")
    assert not telemetry_confirms_estop_reset(True, False, "IDLE")
    assert not telemetry_confirms_estop_reset(False, True, "IDLE")
    assert not telemetry_confirms_estop_reset(False, False, "ACTIVE_NORMAL")

    auto_reset = parse_telemetry_line(
        '{"type":"TEL","system_state":"SYSTEM_CONFIG","therapy_running":false,"mode":"AUTO",'
        '"current_cmd_ma":0,"angle_deg":0,"pw_pct":0,'
        '"fsm_state":"IDLE","signal_quality":"GOOD","phase":"IDLE",'
        '"output_active":false,"fault":"NONE","emergency":false}'
    )
    manual_reset = parse_telemetry_line(
        '{"type":"TEL","system_state":"SYSTEM_CONFIG","therapy_running":false,"mode":"MANUAL",'
        '"current_cmd_ma":0,"angle_deg":0,"pw_pct":0,'
        '"fsm_state":"MANUAL_STOPPED","signal_quality":"GOOD","phase":"IDLE",'
        '"output_active":false,"fault":"NONE","emergency":false}'
    )
    rejected_reset = parse_telemetry_line(
        '{"type":"TEL","system_state":"SYSTEM_EMERGENCY","therapy_running":false,"mode":"AUTO",'
        '"current_cmd_ma":0,"angle_deg":0,"pw_pct":0,'
        '"fsm_state":"EMERGENCY","signal_quality":"GOOD","phase":"E_STOP",'
        '"output_active":false,"fault":"EMERGENCY","emergency":true}'
    )
    for reset_frame in (auto_reset, manual_reset, rejected_reset):
        assert is_complete_control_telemetry(reset_frame)
    assert telemetry_confirms_estop_reset(
        auto_reset["emergency"], auto_reset["output_active"], telemetry_fsm_state(auto_reset),
    )
    assert telemetry_confirms_estop_reset(
        manual_reset["emergency"], manual_reset["output_active"], telemetry_fsm_state(manual_reset),
    )
    assert not telemetry_confirms_estop_reset(
        rejected_reset["emergency"], rejected_reset["output_active"], telemetry_fsm_state(rejected_reset),
    )
    auto_running = Telemetry(
        system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="AUTO",
        emergency=False, output_active=False, fsm_state="WAITING_INTENT",
    )
    manual_running = Telemetry(
        system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="MANUAL",
        emergency=False, output_active=True, fsm_state="MANUAL_ACTIVE",
    )
    completed = Telemetry(
        system_state="SYSTEM_COMPLETED", therapy_running=False, selected_mode="AUTO",
        emergency=False, output_active=False, fsm_state="THERAPY_STOP",
    )
    waiting = Telemetry(
        system_state="SYSTEM_WAIT_READY", therapy_running=False, selected_mode="NONE",
        emergency=False, output_active=False, fsm_state="IDLE",
    )
    emergency = Telemetry(
        system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="AUTO",
        emergency=True, output_active=True, fsm_state="ACTIVE_NORMAL",
    )
    assert derive_system_mode(auto_running) == "AUTO"
    assert derive_system_mode(manual_running) == "MANUAL"
    assert derive_system_mode(completed) == "STANDBY"
    assert derive_system_mode(waiting) == "WAIT"
    assert derive_system_mode(emergency) == "EMERGENCY"
    assert SYSTEM_MODES == {"WAIT", "STANDBY", "AUTO", "MANUAL", "EMERGENCY"}
    checks += 1

    parsed_legacy = parse_telemetry_line("EMG_RMS_MV,0.512")
    assert parsed_legacy["emg_rms_mv"] == 0.512
    checks += 1

    manager = SerialManager(hardware_control_requested=False)
    manager.connected = True
    manager.connection_kind = "SERIAL"
    assert manager.can_control(), "Direct serial harus tersedia tanpa CLI gate"
    manager.estop_latched = True
    assert not manager.can_control(), "E-STOP harus selalu mengunci kontrol"
    manager.confirm_estop_reset()
    assert manager.can_control(), "Kontrol harus pulih setelah firmware mengonfirmasi reset"
    checks += 1

    reset_gate = SerialManager(hardware_control_requested=False)
    reset_gate.connected = True
    reset_gate.connection_kind = "SERIAL"
    reset_gate.estop_latched = True
    reset_wire: list[Mapping[str, Any]] = []
    reset_gate._send_raw = lambda payload: (reset_wire.append(dict(payload)) is None, "ok")
    reset_sent, _ = reset_gate.reset_estop()
    assert reset_sent
    assert reset_wire == [{"type": "CMD", "cmd": "RESET_ESTOP"}]
    assert reset_gate.estop_latched, "Tombol RESET tidak boleh membuka latch lokal"
    assert reset_gate._reset_estop_requested
    checks += 1

    if tk is not None:
        reset_manager = SerialManager(hardware_control_requested=False)
        reset_manager.connected = True
        reset_manager.connection_kind = "DEMO"
        reset_manager.estop_latched = True

        reset_app = object.__new__(StimulatorApp)
        reset_app.manager = reset_manager
        reset_app.pending_reset_estop = True
        reset_app.pending_reset_deadline = time.monotonic() + 3.0
        reset_app.pending_mode = "AUTO"
        reset_app.pending_start_deadline = time.monotonic() + 1.5
        reset_app.pending_stop_deadline = time.monotonic() + 1.0
        reset_app.pending_calibration = "CALIBRATE_ANGLE"
        reset_app.pending_calibration_label = "Kalibrasi sudut"
        reset_app.pending_calibration_deadline = time.monotonic() + 8.0
        reset_app.session_started_at = time.monotonic()
        reset_app.current_page = "EMG_MONITOR"
        reset_app.selected_mode = "AUTO"
        reset_app.system_mode = "EMERGENCY"
        reset_app.telemetry = Telemetry(
            system_state="SYSTEM_CONFIG", therapy_running=False, selected_mode="MANUAL",
            current_cmd_ma=0.0, output_active=False, fsm_state="MANUAL_STOPPED",
            phase="IDLE", fault="NONE", emergency=False, signal_quality="GOOD",
        )
        reset_app.auto_running = True

        reset_app._clear_confirmed_estop_reset_state()
        assert not reset_manager.estop_latched
        assert reset_app.pending_reset_estop is False
        assert reset_app.pending_reset_deadline is None
        assert reset_app.pending_mode is None
        assert reset_app.pending_start_deadline is None
        assert reset_app.pending_stop_deadline is None
        assert reset_app.pending_calibration is None
        assert reset_app.pending_calibration_label == ""
        assert reset_app.pending_calibration_deadline is None
        assert reset_app.session_started_at is None
        assert reset_app.system_mode == "STANDBY"
        assert reset_app.selected_mode == "MANUAL"
        assert reset_app.current_page == "EMG_MONITOR"
        assert reset_app.auto_running is False
        for calibration_command in ("CALIBRATE_ANGLE", "CAPTURE_MVC", "CALIBRATE_EMG"):
            calibrated, _ = reset_manager.send_command(calibration_command)
            assert calibrated, f"{calibration_command} harus dapat dikirim lagi setelah reset dikonfirmasi"

        reset_app.telemetry = Telemetry(
            system_state="SYSTEM_CONFIG", therapy_running=False, selected_mode="MANUAL",
            current_cmd_ma=0.0, output_active=False, fsm_state="MANUAL_STOPPED",
            phase="IDLE", fault="NONE", emergency=False, signal_quality="GOOD",
        )
        reset_app.system_mode = derive_system_mode(reset_app.telemetry)
        reset_app.data_stale = False
        assert reset_app._control_ready_for_start(require_emg_quality=True)

        class RecordingManager:
            def __init__(self) -> None:
                self.commands: list[Tuple[str, Dict[str, Any]]] = []

            def send_command(self, command: str, **parameters: Any) -> Tuple[bool, str]:
                self.commands.append((command, dict(parameters)))
                return True, "ok"

        recorder = RecordingManager()
        reset_app.manager = recorder
        started, _ = reset_app._send_serial_start_sequence(
            "SET_MANUAL", {"current_cmd_ma": 8.0, "frequency_set_hz": 35.0, "output": False},
        )
        assert started
        assert [command for command, _ in recorder.commands] == [
            "SET_MANUAL", "FES_ON", "START_THERAPY",
        ]
        assert recorder.commands[0][1]["output"] is False

        rejected_manager = SerialManager(hardware_control_requested=False)
        rejected_manager.connected = True
        rejected_manager.connection_kind = "DEMO"
        rejected_manager.estop_latched = True
        assert not telemetry_confirms_estop_reset(True, False, "EMERGENCY")
        calibrate_sent, _ = rejected_manager.send_command("CALIBRATE_ANGLE")
        start_sent, _ = rejected_manager.send_command("START_THERAPY")
        assert not calibrate_sent and not start_sent
        assert rejected_manager.estop_latched
        checks += 1

    demo_manager = SerialManager()
    demo_manager.start_demo()
    try:
        configured, _ = demo_manager.send_command(
            "SET_MANUAL", current_cmd_ma=8.0, frequency_set_hz=35, pulse_width_us=250,
            active_duration_s=0.5, rest_duration_s=0.5, output=False,
        )
        assert configured
        while True:
            kind, payload = demo_manager.events.get(timeout=0.5)
            if kind == "telemetry":
                assert payload.get("output_active") is False
                assert payload.get("fsm_state") == "IDLE"
                assert payload.get("frequency_output_hz") == 0.0
                break
        sent, _ = demo_manager.send_command(
            "SET_MANUAL", current_cmd_ma=8.0, frequency_set_hz=35, pulse_width_us=250,
            active_duration_s=0.5, rest_duration_s=0.5, output=True,
        )
        assert sent
        deadline = time.monotonic() + 1.5
        seen = set()
        while time.monotonic() < deadline and len(seen) < 2:
            try:
                kind, payload = demo_manager.events.get(timeout=0.2)
            except queue.Empty:
                continue
            if kind == "telemetry":
                seen.add(payload.get("fsm_state"))
        assert "KONTRAKSI" in seen or "RELAKSASI" in seen
    finally:
        demo_manager.disconnect()
    checks += 1

    logger = CSVLogger()
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
            temp_path = handle.name
        logger.start(temp_path)
        telemetry = Telemetry(
            received_at=utc_timestamp(), current_cmd_ma=3.2, fsm_state="IDLE",
            mvc_value_mv=1.2, clipping_percent_1s=6.25,
            emg_error_flags=EMG_ERROR_EXCESSIVE_CLIPPING,
            emg_mav_mv=0.42, mav_ratio=0.35, fatigue_flag=False, fatigue_count=2,
            therapy_timer_ms=7000, state_remaining_ms=3000,
            system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="AUTO",
        )
        logger.log(
            telemetry, source="self-test", connection="COM3", mode="AUTO",
            session_id="20260902_181530_A1B2", session_time_s=42,
        )
        logger.stop()
        with open(temp_path, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 1
        assert rows[0]["fsm_state"] == "IDLE"
        assert rows[0]["clipping_percent_1s"] == "6.25"
        assert rows[0]["emg_error_flags"] == str(EMG_ERROR_EXCESSIVE_CLIPPING)
        assert rows[0]["session_id"] == "20260902_181530_A1B2"
        assert rows[0]["session_time_s"] == "42"
        assert rows[0]["emg_mav_mv"] == "0.42"
        assert rows[0]["mav_ratio"] == "0.35"
        assert rows[0]["fatigue_flag"] == "False"
        assert rows[0]["fatigue_count"] == "2"
        assert rows[0]["therapy_timer_ms"] == "7000"
        assert rows[0]["state_remaining_ms"] == "3000"
        assert rows[0]["system_state"] == "SYSTEM_THERAPY"
        assert rows[0]["therapy_running"] == "True"
        assert rows[0]["selected_mode"] == "AUTO"
    finally:
        logger.stop()
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
    checks += 1

    # Check: State Timer & Remaining pure helpers formatting
    assert format_elapsed_ms(None) == "--- s"
    assert format_elapsed_ms(0) == "0 s"
    assert format_elapsed_ms(999) == "0 s"
    assert format_elapsed_ms(1000) == "1 s"
    assert format_elapsed_ms(7900) == "7 s"

    assert format_remaining_ms(None) == "--- s"
    assert format_remaining_ms(0) == "0 s"
    assert format_remaining_ms(1) == "1 s"
    assert format_remaining_ms(999) == "1 s"
    assert format_remaining_ms(1000) == "1 s"
    assert format_remaining_ms(2700) == "3 s"
    assert format_remaining_ms(3000) == "3 s"

    # Check: format_remaining_duration
    assert format_remaining_duration(None, None) == "---"
    assert format_remaining_duration(0, 0) == "---"
    assert format_remaining_duration(0, 10000) == "10/10 s"
    assert format_remaining_duration(1000, 9000) == "9/10 s"
    assert format_remaining_duration(2000, 8000) == "8/10 s"
    assert format_remaining_duration(0, 15000) == "15/15 s"
    assert format_remaining_duration(14500, 500) == "1/15 s"

    # Check: generate_therapy_session_id
    sid1 = generate_therapy_session_id()
    sid2 = generate_therapy_session_id()
    assert re.match(r"^\d{8}_\d{6}_[0-9A-F]{4}$", sid1)
    assert sid1 != sid2

    # Check: Session Time & Therapy Session ID lifecycle transitions
    test_app = object.__new__(StimulatorApp)
    test_app.session_started_at = None
    test_app.session_elapsed_frozen_s = None
    test_app.session_time_known = False
    test_app.current_therapy_session_id = None
    test_app.last_therapy_session_id = None
    test_app._prev_therapy_running = None
    test_app.system_mode = "STANDBY"

    # Initial connection in standby/idle:
    idle_frame = Telemetry(system_state="SYSTEM_CONFIG", therapy_running=False, selected_mode="NONE")
    test_app._handle_session_time_lifecycle(idle_frame, control_frame=True)
    assert test_app.session_started_at is None
    assert test_app.session_time_known is False
    assert test_app.current_therapy_session_id is None
    assert test_app._prev_therapy_running is False

    # Case A: Connect mid-session (first frame says therapy running) -> unknown start time and unknown session_id
    test_app_mid = object.__new__(StimulatorApp)
    test_app_mid.session_started_at = None
    test_app_mid.session_elapsed_frozen_s = None
    test_app_mid.session_time_known = False
    test_app_mid.current_therapy_session_id = None
    test_app_mid.last_therapy_session_id = None
    test_app_mid._prev_therapy_running = None
    test_app_mid.system_mode = "STANDBY"

    mid_frame = Telemetry(system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="AUTO")
    test_app_mid._handle_session_time_lifecycle(mid_frame, control_frame=True)
    assert test_app_mid.session_started_at is None
    assert test_app_mid.session_time_known is False
    assert test_app_mid.current_therapy_session_id is None
    assert test_app_mid.session_elapsed_frozen_s is None
    assert test_app_mid._prev_therapy_running is True

    # Case B: Mid-session stops -> remains unknown
    stop_frame = Telemetry(system_state="SYSTEM_CONFIG", therapy_running=False, selected_mode="NONE")
    test_app_mid.system_mode = "STANDBY"
    test_app_mid._handle_session_time_lifecycle(stop_frame, control_frame=True)
    assert test_app_mid.session_started_at is None
    assert test_app_mid.session_time_known is False
    assert test_app_mid.current_therapy_session_id is None
    assert test_app_mid._prev_therapy_running is False

    # Case C: Fresh session start transition observed -> starts at 0 s and generates unique session ID
    start_frame = Telemetry(system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="AUTO")
    test_app.system_mode = "AUTO"
    test_app._handle_session_time_lifecycle(start_frame, control_frame=True)
    assert test_app.session_started_at is not None
    assert test_app.session_time_known is True
    assert test_app.current_therapy_session_id is not None
    sess_id_1 = test_app.current_therapy_session_id
    assert test_app.last_therapy_session_id == sess_id_1
    assert test_app.session_elapsed_frozen_s is None
    assert test_app._prev_therapy_running is True

    # Case D: Normal stop freezes session duration and clears active session ID
    time.sleep(0.01)
    test_app.system_mode = "STANDBY"
    test_app._handle_session_time_lifecycle(stop_frame, control_frame=True)
    assert test_app.session_started_at is None
    assert test_app.session_time_known is True
    assert test_app.current_therapy_session_id is None
    assert test_app.last_therapy_session_id == sess_id_1
    assert test_app.session_elapsed_frozen_s is not None
    assert test_app._prev_therapy_running is False

    # Case E: Next fresh session resets to 0 s and generates new different session ID
    test_app.system_mode = "MANUAL"
    start_manual = Telemetry(system_state="SYSTEM_THERAPY", therapy_running=True, selected_mode="MANUAL")
    test_app._handle_session_time_lifecycle(start_manual, control_frame=True)
    assert test_app.session_started_at is not None
    assert test_app.session_time_known is True
    assert test_app.current_therapy_session_id is not None
    sess_id_2 = test_app.current_therapy_session_id
    assert sess_id_2 != sess_id_1
    assert test_app.last_therapy_session_id == sess_id_2
    assert test_app.session_elapsed_frozen_s is None
    assert test_app._prev_therapy_running is True
    checks += 1

    print(f"SELF-TEST PASS ({checks} kelompok pemeriksaan)")
    return 0


def run_ui_layout_test(root: Any, app: Any) -> int:
    """Check compact page reachability at a laptop-sized working area."""
    failures: list[str] = []
    sample = {
        "_frame_type": "TEL",
        "system_state": "SYSTEM_CONFIG",
        "therapy_running": False,
        "selected_mode": "NONE",
        "fsm_state": "IDLE",
        "current_cmd_ma": 0.0,
        "angle_deg": 0.0,
        "pwm_pct": 0.0,
        "signal_quality": "GOOD",
        "phase": "IDLE",
        "output_active": False,
        "fault": "NONE",
        "emergency": False,
        "fes_status": "READY",
        "hbridge_status": "OFF",
    }

    try:
        root.state("normal")
        root.geometry("1366x697+0+0")
        root.deiconify()
        root.update()
        app._handle_telemetry(sample)
        root.update()

        expected_pages = {
            "CAL": "PREPARATION",
            "AUTO": "AUTO",
            "MANUAL": "MANUAL",
            "EMG": "MONITORING_EMG",
        }
        for page_key, page_state in expected_pages.items():
            app.show_page(page_key)
            root.update()
            if app.current_page != page_state or not app.pages[page_key].winfo_ismapped():
                failures.append(f"{page_key} tidak dirender sebagai {page_state}")

        auto_rows = (
            (app.auto_info_fsm, "FSM State"),
            (app.auto_info_target, "Target Angle"),
            (app.auto_info_error, "Angle Error"),
            (app.auto_info_derror, "Delta Error"),
            (app.auto_info_mvc, "MVC"),
            (app.auto_info_fatigue, "Fatigue"),
            (app.auto_info_fatigue_count, "Fatigue Count"),
            (app.auto_info_rem_dur, "Remaining / Duration"),
            (app.auto_info_dac_v, "DAC Voltage"),
            (app.fes_output_label, "FES Output"),
        )
        manual_rows = (
            (app.manual_kondisi_live, "Condition"),
            (app.manual_rem_dur_live, "Remaining / Duration"),
            (app.manual_dac_v_live, "DAC Voltage"),
            (app.manual_output_live, "FES Output"),
        )
        preparation_rows = (
            (app.cal_imu_a, "IMU A"),
            (app.cal_imu_b, "IMU B"),
            (app.cal_offset, "Offset"),
            (app.cal_mvc, "MVC"),
            (app.cal_imu_cal, "IMU Calibration"),
            (app.cal_mvc_cal, "MVC Calibration"),
        )
        emg_panel_rows = {
            "WAIT": ("emg_wait", (app.emg_wait_imu_a, app.emg_wait_imu_b, app.emg_wait_offset,
                                    app.emg_wait_mvc, app.emg_wait_imu_cal, app.emg_wait_mvc_cal,
                                    app.emg_wait_quality)),
            "STANDBY": ("emg_standby", (app.emg_standby_imu_a, app.emg_standby_imu_b,
                                         app.emg_standby_offset, app.emg_standby_mvc,
                                         app.emg_standby_imu_cal, app.emg_standby_mvc_cal,
                                         app.emg_standby_fes, app.emg_standby_quality)),
            "AUTO": ("emg_auto", (app.emg_auto_fsm, app.emg_auto_target, app.emg_auto_error,
                                    app.emg_auto_derror, app.emg_auto_mvc, app.emg_auto_fatigue,
                                    app.emg_auto_fatigue_count, app.emg_auto_rem_dur,
                                    app.emg_auto_dac_v, app.emg_auto_fes, app.emg_auto_quality)),
            "MANUAL": ("emg_manual", (app.emg_manual_kondisi, app.emg_manual_rem_dur,
                                        app.emg_manual_dac_v, app.emg_manual_fes,
                                        app.emg_manual_quality)),
            "EMERGENCY": ("emg_emergency", (app.emg_emg_source, app.emg_emg_fault,
                                              app.emg_emg_fes, app.emg_emg_fsm,
                                              app.emg_emg_status)),
        }

        tested_work_areas = ((1366, 697), (1536, 793), (1920, 1009))
        for width, height in tested_work_areas:
            root.geometry(f"{width}x{height}+0+0")
            root.update()
            size_label = f"{width}x{height}"
            for page_key, rows in (("AUTO", auto_rows), ("MANUAL", manual_rows), ("CAL", preparation_rows)):
                app.show_page(page_key)
                root.update()
                host_top = app.page_host.winfo_rooty()
                host_bottom = host_top + app.page_host.winfo_height()
                initially_clipped: list[Tuple[Any, str]] = []
                for widget, expected_title in rows:
                    if getattr(widget, "info_title", None) != expected_title:
                        failures.append(f"{page_key}: baris {expected_title} hilang atau berubah")
                    widget_top = widget.winfo_rooty()
                    widget_bottom = widget.winfo_rooty() + widget.winfo_height()
                    if not widget.winfo_ismapped():
                        failures.append(f"{size_label} {page_key}: baris {expected_title} tidak dipetakan")
                    elif widget_top < host_top or widget_bottom > host_bottom:
                        initially_clipped.append((widget, expected_title))

                if initially_clipped and page_key == "AUTO":
                    scroll = app.scroll_containers["auto_page"]
                    if not scroll["scrollbar"].winfo_ismapped():
                        failures.append(f"{size_label} AUTO: scrollbar tidak tersedia saat dibutuhkan")
                    scroll["canvas"].yview_moveto(1.0)
                    root.update()
                    viewport_top = scroll["canvas"].winfo_rooty()
                    viewport_bottom = viewport_top + scroll["canvas"].winfo_height()
                    for widget, expected_title in initially_clipped:
                        widget_top = widget.winfo_rooty()
                        widget_bottom = widget_top + widget.winfo_height()
                        if widget_top < viewport_top or widget_bottom > viewport_bottom:
                            failures.append(f"{size_label} AUTO: baris {expected_title} tidak terjangkau lewat scroll")
                    scroll["canvas"].yview_moveto(0.0)
                elif initially_clipped:
                    for _widget, expected_title in initially_clipped:
                        failures.append(f"{size_label} {page_key}: baris {expected_title} terpotong")

            app.show_page("EMG")
            root.update()
            if app.emg_plot.winfo_height() < 120:
                failures.append(f"{size_label}: grafik EMG tidak mendapat ruang vertikal yang layak")
            for mode_name, (scroll_key, widgets) in emg_panel_rows.items():
                app.emg_right_panels[mode_name].tkraise()
                scroll = app.scroll_containers[scroll_key]
                scroll["canvas"].yview_moveto(0.0)
                root.update()
                viewport_top = scroll["canvas"].winfo_rooty()
                viewport_bottom = viewport_top + scroll["canvas"].winfo_height()
                clipped = [widget for widget in widgets if widget.winfo_rooty() < viewport_top
                           or widget.winfo_rooty() + widget.winfo_height() > viewport_bottom]
                if clipped:
                    if not scroll["scrollbar"].winfo_ismapped():
                        failures.append(f"{size_label} EMG {mode_name}: scrollbar tidak tersedia")
                    scroll["canvas"].yview_moveto(1.0)
                    root.update()
                    viewport_top = scroll["canvas"].winfo_rooty()
                    viewport_bottom = viewport_top + scroll["canvas"].winfo_height()
                    for widget in clipped:
                        if widget.winfo_rooty() < viewport_top or widget.winfo_rooty() + widget.winfo_height() > viewport_bottom:
                            failures.append(f"{size_label} EMG {mode_name}: {widget.info_title} tidak terjangkau")
            estop_bottom = app.estop_button.winfo_rooty() + app.estop_button.winfo_height()
            if not app.estop_button.winfo_ismapped() or estop_bottom > root.winfo_height():
                failures.append(f"{size_label}: Emergency Stop tidak terjangkau")

        if set(app.emg_right_panels) != {"WAIT", "STANDBY", "AUTO", "MANUAL", "EMERGENCY"}:
            failures.append("Mapping panel kanan Monitoring EMG berubah")

        if app.auto_info_target.cget("text") != "--- °":
            failures.append("Target Angle mengarang fallback tanpa telemetry")
        if app.auto_info_error.cget("text") != "--- °":
            failures.append("Angle Error dihitung lokal tanpa telemetry")
        if app.auto_info_dac_v.cget("text") != "--- V":
            failures.append("DAC Voltage mengarang nilai tanpa telemetry")
        if app.fes_output_label.cget("text") != "OFF":
            failures.append("FES Output tidak mengikuti output_active aktual")
        if app.emg_emg_status.cget("text") != "SYSTEM_CONFIG":
            failures.append("Emergency Status tidak mengikuti system_state aktual")
    except Exception as exc:
        failures.append(f"exception: {type(exc).__name__}: {exc}")

    if failures:
        print("UI LAYOUT TEST FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("UI LAYOUT TEST PASS (1366x697, 1536x793, 1920x1009 working areas)")
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GUI rehabilitasi FES: persiapan sensor, MVC EMG, Auto, Manual, FSM, monitoring, dan system health")
    parser.add_argument("--port", help="Port serial MCU, misalnya COM6. Tanpa port, aplikasi mulai dalam demo.")
    parser.add_argument("--baud", type=int, default=BAUD_RATE, help=f"Baud rate serial (default: {BAUD_RATE})")
    parser.add_argument("--enable-hardware-control", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="Uji parser/safety/logger lalu keluar tanpa GUI")
    parser.add_argument("--ui-smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ui-flow-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ui-layout-test", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_argument_parser().parse_args(list(argv) if argv is not None else None)
    if args.self_test:
        return run_self_test()
    if TK_IMPORT_ERROR is not None or tk is None:
        print(f"Tkinter tidak tersedia: {TK_IMPORT_ERROR}", file=sys.stderr)
        return 2
    root = tk.Tk()
    app = StimulatorApp(root, args)
    if args.ui_layout_test:
        result = run_ui_layout_test(root, app)
        app.close()
        return result
    flow_failures: list[str] = []
    if args.ui_smoke_test:
        root.withdraw()
        root.after(400, app.close)
    elif args.ui_flow_test:
        root.withdraw()
        app.start_demo()

        def flow_start() -> None:
            if app.data_stale or not app.manager.can_control():
                flow_failures.append("Demo control did not become ready")
            app.start_auto()

        def flow_check_running_and_stop() -> None:
            if app.system_mode != "AUTO":
                flow_failures.append(f"Expected AUTO, got {app.system_mode}")
            if app.selected_mode != "AUTO":
                flow_failures.append(f"Expected selected AUTO, got {app.selected_mode}")
            app.show_page("MANUAL")
            if app.current_page != "MANUAL" or app.selected_mode != "AUTO" or app.system_mode != "AUTO":
                flow_failures.append("Manual page navigation changed the selected or system mode")
            app.show_page("EMG")
            if app.current_page != "MONITORING_EMG" or app.selected_mode != "AUTO" or app.system_mode != "AUTO":
                flow_failures.append("EMG page navigation changed the selected or system mode")
            app.stop_session()

        def flow_check_stopped_and_estop() -> None:
            if app.system_mode != "STANDBY" or app.telemetry.output_active is not False:
                flow_failures.append(
                    f"Expected confirmed STANDBY/OFF, got {app.system_mode}/{app.telemetry.output_active}",
                )
            app.emergency_stop("ui_flow_test")

        def flow_check_estop_and_close() -> None:
            if not (
                app.system_mode == "EMERGENCY"
                and app.manager.estop_latched
                and app.estop_output_confirmed
                and app.telemetry.output_active is False
                and app._fresh_estop_off_confirmation()
            ):
                flow_failures.append(
                    "Expected latched E-STOP with telemetry-confirmed output OFF",
                )
            app.last_telemetry_monotonic = time.monotonic() - DATA_STALE_SECONDS - 0.2
            app._check_data_health()
            app._refresh_control_state()
            if app.estop_output_confirmed or app._fresh_estop_off_confirmation():
                flow_failures.append("Stale telemetry did not invalidate E-STOP OFF confirmation")
            if str(app.reset_estop_button.cget("state")) != "disabled":
                flow_failures.append("Reset E-STOP remained enabled after telemetry became stale")
            app.manager.disconnect()
            app._check_data_health()
            if app.estop_output_confirmed or app._fresh_estop_off_confirmation():
                flow_failures.append("Disconnect did not invalidate E-STOP OFF confirmation")
            app.close()

        root.after(500, flow_start)
        root.after(950, flow_check_running_and_stop)
        root.after(1450, flow_check_stopped_and_estop)
        root.after(1850, flow_check_estop_and_close)
    root.mainloop()
    if args.ui_smoke_test:
        print("UI SMOKE TEST PASS")
    if args.ui_flow_test:
        if flow_failures:
            print("UI FLOW TEST FAIL: " + "; ".join(flow_failures), file=sys.stderr)
            return 1
        print("UI FLOW TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

