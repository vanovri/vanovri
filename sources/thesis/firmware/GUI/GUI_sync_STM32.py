#!/usr/bin/env python3
"""GUI rehabilitasi FES dengan koneksi serial langsung.

Fokus antarmuka:
- Persiapan sensor: kalibrasi sudut IMU dan pengambilan nilai MVC EMG.
- Mode Auto dan Manual dengan parameter arus, frekuensi, PWM, durasi ACTIVE/REST.
- Mode Auto menambahkan target sudut.
- FSM sesi menggunakan state IDLE, KONTRAKSI, dan RELAKSASI.
- Monitoring EMG menampilkan RMS, sudut, error sudut, PWM, frekuensi, arus, FSM,
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
from collections import deque
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

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


COLORS = {
    "bg": "#0B1220",
    "panel": "#111B2E",
    "panel_2": "#17243A",
    "line": "#263650",
    "text": "#F5F7FB",
    "muted": "#94A3B8",
    "blue": "#45A3FF",
    "cyan": "#31D7C4",
    "green": "#3DDC97",
    "yellow": "#F6C85F",
    "red": "#FF5D6C",
    "red_dark": "#B52F43",
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


CURRENT_MA_KEYS = {
    "current_ma", "current_m_a", "i_ma", "ima", "arus_ma", "ampere_ma",
    "measured_current_ma", "current_measured_ma", "i_meas_ma",
}
CURRENT_A_KEYS = {"current_a", "i_a", "ampere", "amps", "measured_current_a"}
CURRENT_SET_KEYS = {"current_set_ma", "i_set_ma", "arus_set_ma", "target_current_ma"}
ANGLE_KEYS = {"angle", "angle_deg", "sudut", "sudut_deg", "theta", "joint_angle"}
ANGLE_TARGET_KEYS = {"angle_target_deg", "target_angle_deg", "sudut_target_deg"}
PWM_KEYS = {
    "pwm_pct", "pwm_percent", "pwm_out_pct", "duty_pct",
}
PWM_COMMAND_KEYS = {"pwm_cmd_pct", "pwm_command_pct", "pwm_set_pct"}
PWM_RAW_KEYS = {"pwm_raw", "duty_raw", "pwm_8bit"}
FATIGUE_SCORE_KEYS = {
    "fatigue_score", "fatigue_index", "fatigue_level", "fatigue_pct", "fatigue_percent",
}
FATIGUE_STATE_KEYS = {
    "fatigue_state", "fatigue_status", "fatigue_phase", "fatigue_detected", "fatigue",
}
EMG_KEYS = {"emg_rms_mv", "rms_mv", "emg_rms", "emg", "rms"}
QUALITY_KEYS = {"signal_quality", "emg_quality", "quality"}
PHASE_KEYS = {"phase", "session_phase", "stim_phase", "state"}
FATIGUE_THRESHOLD_KEYS = {"fatigue_threshold", "fatigue_threshold_score", "fatigue_limit"}
OUTPUT_KEYS = {"output", "output_active", "stim_active", "stimulation_active"}
STOP_REASON_KEYS = {"stop_reason", "reason_stop", "last_stop_reason"}
FAULT_KEYS = {"fault", "fault_code", "error_code"}
EMERGENCY_KEYS = {"emergency", "estop", "emergency_active"}
EMERGENCY_SOURCE_KEYS = {"emergency_source", "estop_source"}
PULSE_WIDTH_KEYS = {"pulse_width_us", "pulse_us", "pw_us"}
FREQUENCY_KEYS = {"frequency_hz", "freq_hz", "stim_frequency_hz"}
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
ANGLE_CAL_KEYS = {"angle_calibrated", "imu_calibrated", "angle_cal_ok"}
EMG_CAL_KEYS = {"emg_calibrated", "emg_cal_ok"}
FSM_STATE_KEYS = {"fsm", "fsm_state", "state_fsm", "rehab_state"}
MVC_VALUE_KEYS = {"mvc_mv", "mvc_value_mv", "mvc_value", "emg_mvc_mv"}
MVC_READY_KEYS = {"mvc_ready", "mvc_valid", "mvc_done", "mvc_ok"}
ACTIVE_DURATION_KEYS = {"active_duration_s", "duration_active_s", "active_s", "waktu_active_s"}
REST_DURATION_KEYS = {"rest_duration_s", "duration_rest_s", "rest_s", "waktu_rest_s"}
MODE_KEYS = {"mode", "therapy_mode", "selected_mode"}
ACTIVE_MODE_KEYS = {"active_mode", "fsm_active_mode"}
MAV_KEYS = {"emg_mav_mv", "mav_mv", "mav"}
MAV_RATIO_KEYS = {"mav_ratio", "emg_mav_ratio"}
FUZZY_OUTPUT_KEYS = {"fuzzy_output_us", "fuzzy_output", "pw_fuzzy_us"}
HBRIDGE_STATE_KEYS = {"hbridge_state", "h_bridge_state"}
FATIGUE_FLAG_KEYS = {"fatigue_flag", "fatigue_confirmed"}
FATIGUE_COUNT_KEYS = {"fatigue_count", "fatigue_rest_count"}
THERAPY_TIMER_KEYS = {"therapy_timer_ms", "state_elapsed_ms"}
STATE_REMAINING_KEYS = {"state_remaining_ms", "therapy_remaining_ms"}
# Firmware final memakai PW. Nama PWM hanya diterima sebagai kompatibilitas frame lama.
PWM_KEYS.update({"pw_pct"})
PWM_COMMAND_KEYS.update({"pw_command_pct", "pw_cmd_pct"})
FUZZY_PWM_KEYS.update({"fuzzy_pw_pct"})


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
    """Map label firmware without creating a GUI-side FSM."""
    text = _norm_key(value)
    mapping = {
        "idle": "IDLE", "safe_idle": "IDLE", "waiting_intent": "IDLE",
        "active": "ACTIVE / NORMAL", "active_normal": "ACTIVE / NORMAL",
        "normal_active": "ACTIVE / NORMAL", "kontraksi": "ACTIVE / NORMAL",
        "contraction": "ACTIVE / NORMAL", "manual_active": "ACTIVE / NORMAL",
        "active_fatigue": "ACTIVE / FATIGUE", "fatigue_active": "ACTIVE / FATIGUE",
        "rest": "REST", "relaksasi": "REST", "relaxation": "REST",
        "manual_rest": "REST", "fatigue_rest": "FATIGUE_REST",
        "therapy_stop": "THERAPY_STOP", "manual_stopped": "IDLE",
        "emergency": "EMERGENCY", "e_stop": "EMERGENCY", "estop": "EMERGENCY",
    }
    return mapping.get(text, str(value).strip().upper()[:32] if str(value).strip() else "IDLE")


def normalize_active_mode(value: Any) -> str:
    text = _norm_key(value)
    if text in {"normal", "active_normal", "1"}: return "NORMAL"
    if text in {"fatigue", "active_fatigue", "2"}: return "FATIGUE"
    return "NONE"


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
        if key in CURRENT_MA_KEYS:
            number = _float(value)
            if number is not None:
                normalized["current_ma"] = number
        elif key in CURRENT_A_KEYS:
            number = _float(value)
            if number is not None:
                normalized["current_ma"] = number * 1000.0
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
        elif key in FREQUENCY_KEYS:
            number = _float(value)
            if number is not None:
                normalized["frequency_hz"] = max(0.0, number)
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
        elif key in ANGLE_CAL_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["angle_calibrated"] = parsed_bool
        elif key in EMG_CAL_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None:
                normalized["emg_calibrated"] = parsed_bool
        elif key in FSM_STATE_KEYS:
            normalized["fsm_state"] = normalize_fsm_state(value)
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
        elif key in MODE_KEYS:
            normalized["mode"] = str(value).strip().upper()[:16]
        elif key in ACTIVE_MODE_KEYS:
            normalized["active_mode"] = normalize_active_mode(value)
        elif key in MAV_KEYS:
            number = _float(value)
            if number is not None: normalized["emg_mav_mv"] = max(0.0, number)
        elif key in MAV_RATIO_KEYS:
            number = _float(value)
            if number is not None: normalized["mav_ratio"] = max(0.0, number)
        elif key in FUZZY_OUTPUT_KEYS:
            number = _float(value)
            if number is not None: normalized["fuzzy_output_us"] = number
        elif key in HBRIDGE_STATE_KEYS:
            normalized["hbridge_state"] = str(value).strip().upper()[:24]
        elif key in FATIGUE_FLAG_KEYS:
            parsed_bool = _bool(value)
            if parsed_bool is not None: normalized["fatigue_flag"] = parsed_bool
        elif key in FATIGUE_COUNT_KEYS:
            number = _float(value)
            if number is not None and number >= 0.0: normalized["fatigue_count"] = int(number)
        elif key in THERAPY_TIMER_KEYS:
            number = _float(value)
            if number is not None and number >= 0.0: normalized["therapy_timer_ms"] = int(number)
        elif key in STATE_REMAINING_KEYS:
            number = _float(value)
            if number is not None and number >= 0.0: normalized["state_remaining_ms"] = int(number)

    telemetry_fields = {
        "current_ma", "current_set_ma", "angle_deg", "angle_target_deg", "pwm_pct",
        "pwm_command_pct", "pulse_width_us", "frequency_hz", "fatigue_score",
        "fatigue_threshold", "fatigue_state", "emg_rms_mv", "signal_quality",
        "phase", "output_active", "stop_reason", "fault", "emergency", "emergency_source",
        "imu_a_status", "imu_b_status", "imu_a_angle_deg", "imu_b_angle_deg",
        "angle_error_deg", "delta_error_deg", "fuzzy_pwm_pct", "intent_state", "intent_score",
        "mcp4725_status", "hbridge_status", "dac_raw", "dac_voltage_v", "fes_status",
        "angle_calibrated", "emg_calibrated", "mcu_status", "emg_status",
        "fsm_state", "mvc_value_mv", "mvc_ready", "active_duration_s", "rest_duration_s",
        "mode", "active_mode", "emg_mav_mv", "mav_ratio", "fuzzy_output_us",
        "hbridge_state", "fatigue_flag", "fatigue_count", "therapy_timer_ms", "state_remaining_ms",
    }
    if not telemetry_fields.intersection(normalized):
        return {}
    return normalized


CONTROL_TELEMETRY_FIELDS = {
    "current_ma", "angle_deg", "signal_quality", "phase", "fsm_state",
    "output_active", "fault", "pulse_width_us", "frequency_hz",
}


def is_complete_control_telemetry(update: Mapping[str, Any]) -> bool:
    """Only an atomic STM32 TEL frame can drive status/control freshness."""
    if update.get("_frame_type") != "TEL" or not CONTROL_TELEMETRY_FIELDS.issubset(update):
        return False
    current = update.get("current_ma")
    angle = update.get("angle_deg")
    return bool(
        isinstance(current, (int, float)) and not isinstance(current, bool)
        and math.isfinite(float(current)) and 0.0 <= float(current) <= 100.0
        and isinstance(angle, (int, float)) and not isinstance(angle, bool)
        and math.isfinite(float(angle)) and -180.0 <= float(angle) <= 180.0
        and isinstance(update.get("output_active"), bool)
        and bool(str(update.get("fsm_state", "")).strip())
    )


@dataclass
class Telemetry:
    received_at: str = ""
    session_id: str = ""
    mcu_status: str = ""
    emg_status: str = ""
    current_ma: Optional[float] = None
    current_set_ma: Optional[float] = None
    angle_deg: Optional[float] = None
    angle_target_deg: Optional[float] = None
    pwm_pct: Optional[float] = None
    pwm_command_pct: Optional[float] = None
    pulse_width_us: Optional[float] = None
    frequency_hz: Optional[float] = None
    fatigue_score: Optional[float] = None
    fatigue_threshold: Optional[float] = None
    fatigue_state: str = "WAITING"
    emg_rms_mv: Optional[float] = None
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
    angle_calibrated: Optional[bool] = None
    emg_calibrated: Optional[bool] = None
    fsm_state: str = "IDLE"
    mvc_value_mv: Optional[float] = None
    mvc_ready: Optional[bool] = None
    active_duration_s: Optional[float] = None
    rest_duration_s: Optional[float] = None
    mode: str = "NONE"
    active_mode: str = "NONE"
    emg_mav_mv: Optional[float] = None
    mav_ratio: Optional[float] = None
    fuzzy_output_us: Optional[float] = None
    hbridge_state: str = "OFF"
    fatigue_flag: Optional[bool] = None
    fatigue_count: Optional[int] = None
    therapy_timer_ms: Optional[int] = None
    state_remaining_ms: Optional[int] = None

    def merge(self, update: Mapping[str, Any]) -> None:
        allowed = {item.name for item in fields(self)}
        for key, value in update.items():
            if key in allowed:
                setattr(self, key, value)


class CSVLogger:
    FIELDNAMES = [
        "timestamp", "mode", "fsm_state", "active_mode", "MAV", "RMS", "MVC",
        "MAV_ratio", "IMU_A", "IMU_B", "joint_angle", "target_angle", "error",
        "delta_error", "fuzzy_output", "PW", "current", "frequency",
        "HBridge_state", "phase", "fatigue_flag", "fatigue_count",
        "therapy_timer", "fault_code", "source", "connection", "session_id",
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
        writer.writeheader(); file_obj.flush()
        with self._lock:
            self._file, self._writer, self.path = file_obj, writer, os.path.abspath(path)

    def log(self, telemetry: Telemetry, source: str, connection: str, mode: str = "") -> None:
        with self._lock:
            if self._file is None or self._writer is None: return
            t = telemetry
            row = {
                "timestamp": t.received_at or utc_timestamp(),
                "mode": t.mode or mode, "fsm_state": t.fsm_state,
                "active_mode": t.active_mode, "MAV": t.emg_mav_mv,
                "RMS": t.emg_rms_mv, "MVC": t.mvc_value_mv, "MAV_ratio": t.mav_ratio,
                "IMU_A": t.imu_a_angle_deg, "IMU_B": t.imu_b_angle_deg,
                "joint_angle": t.angle_deg, "target_angle": t.angle_target_deg,
                "error": t.angle_error_deg, "delta_error": t.delta_error_deg,
                "fuzzy_output": t.fuzzy_output_us, "PW": t.pulse_width_us,
                "current": t.current_ma, "frequency": t.frequency_hz,
                "HBridge_state": t.hbridge_state or t.hbridge_status,
                "phase": t.phase, "fatigue_flag": t.fatigue_flag,
                "fatigue_count": t.fatigue_count,
                "therapy_timer": t.therapy_timer_ms, "fault_code": t.fault,
                "source": source, "connection": connection, "session_id": t.session_id,
            }
            self._writer.writerow(row); self._file.flush()

    def stop(self) -> None:
        with self._lock:
            file_obj = self._file; self._file = None; self._writer = None; self.path = None
        if file_obj is not None: file_obj.close()


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
        self.connected = False  # komunikasi TEL aktual, bukan sekadar COM terbuka
        self.port_open = False
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
            "mode": "IDLE",
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
        was_connected = self.connected
        with self._state_lock:
            self.connected = False
            self.port_open = False
            self._session_id = ""
            self.connection_kind = "DISCONNECTED"
            self.port_name = ""
        if was_connected:
            self._status("Koneksi dihentikan.")

    def _serial_loop(self, stop_event: threading.Event) -> None:
        last_valid: Optional[float] = None
        while not stop_event.is_set():
            serial_obj = self._serial
            if serial_obj is None: break
            try:
                raw = serial_obj.read_until(expected=b"\n", size=2048)
            except Exception as exc:
                self.events.put(("error", f"Kesalahan serial: {exc}")); break
            now = time.monotonic()
            if not raw:
                if last_valid is not None and now - last_valid > DATA_STALE_SECONDS:
                    with self._state_lock:
                        was_connected = self.connected; self.connected = False
                    if was_connected: self._status("DISCONNECTED: telemetry STM32 timeout; port tetap terbuka.")
                continue
            if len(raw) >= 2048 and not raw.endswith(b"\n"):
                self.events.put(("error", "Baris serial terlalu panjang; paket dibuang.")); continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line: continue
            telemetry = parse_telemetry_line(line)
            if not telemetry: continue
            if is_complete_control_telemetry(telemetry):
                last_valid = now
                with self._state_lock:
                    newly_connected = not self.connected
                    self.connected = True
                if newly_connected: self._status("CONNECTED: telemetry STM32 aktif.")
            self.events.put(("telemetry", telemetry))
        if not stop_event.is_set():
            with self._state_lock:
                self.connected = False; self.port_open = False; self._session_id = ""
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
                "current_ma": round(max(0.0, current + random.uniform(-0.06, 0.06)), 3),
                "current_set_ma": round(float(demo.get("current_target", PROJECT_FIXED_CURRENT_MA)), 3),
                "angle_deg": round(max(0.0, angle + random.uniform(-0.2, 0.2)), 2),
                "angle_target_deg": round(angle_target, 2),
                "pulse_width_us": round(max(0.0, pwm), 1),
                "pwm_pct": round(pwm_us_to_pct(max(PROJECT_PWM_MIN_US, pwm)) if pwm > 0.0 else 0.0, 2),
                "pwm_command_pct": round(pwm_us_to_pct(float(demo.get("pwm_target", PROJECT_PWM_DEFAULT_US))), 2),
                "emg_rms_mv": round(emg, 4),
                "signal_quality": "BAIK",
                "phase": fsm_state,
                "fsm_state": fsm_state,
                "output_active": output,
                "stop_reason": "",
                "fault": "NONE",
                "emergency": bool(estop),
                "emergency_source": "GUI" if estop else "NONE",
                "frequency_hz": frequency,
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
                "fes_status": "ACTIVE" if output else "READY",
                "angle_calibrated": bool(demo.get("angle_calibrated", True)),
                "mvc_ready": bool(demo.get("mvc_ready", True)),
                "mvc_value_mv": float(demo.get("mvc_value_mv", 1.20)),
                "mcu_status": "ONLINE",
                "emg_status": "READY",
            }
            self.events.put(("telemetry", telemetry))

    def _send_raw(self, payload: Mapping[str, Any]) -> Tuple[bool, str]:
        serial_obj = self._serial
        if self.connection_kind != "SERIAL" or serial_obj is None or not self.port_open:
            return False, "Port serial tidak terbuka."
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
            return False, "Port serial tidak terbuka; E-STOP lokal tetap dikunci."
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
                        current_target=float(parameters.get("current_ma", self._demo_state["current_target"])),
                        frequency_target=float(parameters.get("frequency_hz", self._demo_state["frequency_target"])),
                        pwm_target=float(parameters.get(
                            "pulse_width_us",
                            pwm_pct_to_us(float(parameters["pwm_pct"])) if "pwm_pct" in parameters else self._demo_state["pwm_target"],
                        )),
                        angle_target=float(parameters.get("angle_target_deg", PROJECT_DEFAULT_TARGET_ANGLE_DEG)),
                        # ACTIVE/REST Auto ditentukan oleh logika/FSM MCU, bukan input GUI.
                        session_started=time.monotonic(),
                    )
                elif command in {"SET_MANUAL", "OUTPUT_ON"}:
                    self._demo_state.update(
                        output=True,
                        mode="MANUAL",
                        current_target=float(parameters.get("current_ma", self._demo_state["current_target"])),
                        frequency_target=float(parameters.get("frequency_hz", self._demo_state["frequency_target"])),
                        pwm_target=float(parameters.get(
                            "pulse_width_us",
                            pwm_pct_to_us(float(parameters["pwm_pct"])) if "pwm_pct" in parameters else self._demo_state["pwm_target"],
                        )),
                        active_duration=float(parameters.get("active_duration_s", self._demo_state["active_duration"])),
                        rest_duration=float(parameters.get("rest_duration_s", self._demo_state["rest_duration"])),
                        session_started=time.monotonic(),
                    )
                elif command == "CAPTURE_MVC":
                    self._demo_state.update(mvc_ready=True, mvc_value_mv=1.20)
                elif command == "CALIBRATE_ANGLE":
                    self._demo_state.update(angle_calibrated=True)
                elif command in {"STOP_THERAPY", "STOP", "STOP_AUTO", "OUTPUT_OFF", "ESTOP"}:
                    self._demo_state.update(output=False, mode="IDLE", session_started=None)
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
                self._demo_state.update(output=False, mode="IDLE", session_started=None)
        # STOP safety commands are allowed even in monitor-only mode. This does not
        # unlock any energizing command and is safe to attempt if a serial link exists.
        if self.connection_kind == "SERIAL" and self.port_open:
            result = self._send_safety_stop_wire(include_estop=True, reason=reason)
        else:
            result = (True, "E-STOP lokal aktif.")
        self._status("E-STOP AKTIF - keluaran dikunci.")
        return result

    def reset_estop(self) -> Tuple[bool, str]:
        """RESET/CLEAR emergency atau THERAPY_STOP; CSV tidak disentuh."""
        if self.connection_kind == "SERIAL":
            if not self.port_open: return False, "RESET memerlukan port serial terbuka."
            sent, message = self._send_raw({"type": "CMD", "cmd": "RESET_CLEAR"})
            if not sent: return False, message
            with self._state_lock: self._reset_estop_requested = True
            return True, "RESET_CLEAR dikirim; menunggu IDLE/OFF dari STM32."
        with self._state_lock:
            self.estop_latched = False; self._reset_estop_requested = False
        self._status("RESET demo; keluaran tetap OFF.")
        return True, "RESET dikirim."

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
            tk.Frame(self, bg=accent, width=4).pack(side="left", fill="y")
            body = tk.Frame(self, bg=COLORS["panel"])
            body.pack(fill="both", expand=True, padx=16, pady=13)
            tk.Label(body, text=title.upper(), bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 9)).pack(anchor="w")
            value_row = tk.Frame(body, bg=COLORS["panel"])
            value_row.pack(anchor="w", pady=(7, 0))
            self.value_label = tk.Label(value_row, text="--", bg=COLORS["panel"], fg=COLORS["text"],
                                        font=("Segoe UI Semibold", 23))
            self.value_label.pack(side="left")
            self.unit_label = tk.Label(value_row, text=f"  {unit}" if unit else "", bg=COLORS["panel"],
                                       fg=COLORS["muted"], font=("Segoe UI", 10))
            self.unit_label.pack(side="left", anchor="s", pady=(0, 4))

        def set(self, value: str, *, color: Optional[str] = None, unit: Optional[str] = None) -> None:
            self.value_label.configure(text=value, fg=color or COLORS["text"])
            if unit is not None:
                self.unit_label.configure(text=f"  {unit}" if unit else "")


    class EMGPlot(tk.Canvas):
        def __init__(self, parent: tk.Misc) -> None:
            super().__init__(parent, bg=COLORS["panel"], highlightthickness=0, height=330)
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
            self.active_page = "CAL"
            self.active_mode = "IDLE"
            self.auto_running = False
            self.last_any_telemetry_monotonic: Optional[float] = None
            self.last_telemetry_monotonic: Optional[float] = None
            self.data_stale = True
            self.stale_stop_sent = False
            self.session_started_at: Optional[float] = None
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

            root.title(APP_NAME)
            root.geometry("1380x860")
            root.minsize(1180, 740)
            root.configure(bg=COLORS["bg"])
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

        def _build_layout(self) -> None:
            self.sidebar = tk.Frame(self.root, bg="#0E1728", width=238)
            self.sidebar.pack(side="left", fill="y")
            self.sidebar.pack_propagate(False)

            brand = tk.Frame(self.sidebar, bg="#0E1728")
            brand.pack(fill="x", padx=20, pady=(22, 18))
            tk.Label(brand, text="FES REHAB", bg="#0E1728", fg=COLORS["text"],
                     font=("Segoe UI Semibold", 16)).pack(anchor="w")
            tk.Label(brand, text="IMU · EMG · FSM · Safety", bg="#0E1728", fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

            tk.Label(self.sidebar, text="NAVIGASI", bg="#0E1728", fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=20, pady=(8, 7))
            nav_items = (
                ("CAL", "Persiapan Sensor"),
                ("AUTO", "Mode Auto"),
                ("MANUAL", "Mode Manual"),
                ("EMG", "Monitoring EMG"),
            )
            for key, label in nav_items:
                button = tk.Button(
                    self.sidebar, text=label, anchor="w", relief="flat", bd=0,
                    bg="#0E1728", fg=COLORS["muted"], activebackground=COLORS["panel_2"],
                    activeforeground=COLORS["white"], font=("Segoe UI Semibold", 10),
                    padx=20, pady=11, command=lambda page=key: self.show_page(page), cursor="hand2",
                )
                button.pack(fill="x", padx=8, pady=2)
                self.nav_buttons[key] = button

            safety = tk.Frame(self.sidebar, bg="#0E1728")
            safety.pack(side="bottom", fill="x", padx=16, pady=16)
            self.estop_button = tk.Button(
                safety, text="EMERGENCY STOP  [ESC]", command=self.emergency_stop,
                bg=COLORS["red_dark"], fg=COLORS["white"], activebackground=COLORS["red"],
                activeforeground=COLORS["white"], relief="flat", bd=0,
                font=("Segoe UI Semibold", 10), pady=12, cursor="hand2",
            )
            self.estop_button.pack(fill="x")
            self.reset_estop_button = tk.Button(
                safety, text="Reset E-STOP", command=self.reset_estop,
                bg=COLORS["panel_2"], fg=COLORS["muted"], activebackground=COLORS["line"],
                activeforeground=COLORS["text"], relief="flat", bd=0,
                font=("Segoe UI", 9), pady=8, cursor="hand2",
            )
            self.reset_estop_button.pack(fill="x", pady=(7, 0))

            connection = tk.Frame(self.sidebar, bg="#0E1728")
            connection.pack(side="bottom", fill="x", padx=16, pady=(4, 0))
            tk.Label(connection, text="KONEKSI MCU", bg="#0E1728", fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 7))
            self.port_var = tk.StringVar(value=self.args.port or "")
            port_row = tk.Frame(connection, bg="#0E1728")
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
            row = tk.Frame(connection, bg="#0E1728")
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
            self.main.pack(side="left", fill="both", expand=True)

            header = tk.Frame(self.main, bg=COLORS["bg"], height=68)
            header.pack(fill="x", padx=22, pady=(16, 8))
            header.pack_propagate(False)
            title_box = tk.Frame(header, bg=COLORS["bg"])
            title_box.pack(side="left", fill="y")
            self.page_title = tk.Label(title_box, text="Persiapan Sensor", bg=COLORS["bg"], fg=COLORS["text"],
                                       font=("Segoe UI Semibold", 20))
            self.page_title.pack(anchor="w")
            self.page_subtitle = tk.Label(title_box, text="Kalibrasi sudut dan pengambilan nilai MVC", bg=COLORS["bg"],
                                          fg=COLORS["muted"], font=("Segoe UI", 9))
            self.page_subtitle.pack(anchor="w", pady=(2, 0))
            actions = tk.Frame(header, bg=COLORS["bg"])
            actions.pack(side="right", anchor="n")
            self.safety_badge = tk.Label(actions, text="DEMO AMAN", bg="#123B37", fg=COLORS["green"],
                                         font=("Segoe UI Semibold", 9), padx=12, pady=7)
            self.safety_badge.pack(side="left", padx=(0, 8))
            self.log_button = tk.Button(
                actions, text="Mulai CSV", command=self.toggle_logging, bg=COLORS["panel_2"],
                fg=COLORS["text"], activebackground=COLORS["line"], activeforeground=COLORS["white"],
                relief="flat", bd=0, font=("Segoe UI Semibold", 9), padx=12, pady=7, cursor="hand2",
            )
            self.log_button.pack(side="left")

            health = tk.Frame(self.main, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
            health.pack(fill="x", padx=22, pady=(0, 10))
            tk.Label(health, text="SYSTEM HEALTH", bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(side="left", padx=(14, 10), pady=10)
            chips = tk.Frame(health, bg=COLORS["panel"])
            chips.pack(side="left", fill="x", expand=True, pady=6)
            self.health_labels: Dict[str, tk.Label] = {}
            for index, (key, label) in enumerate((
                ("MCU", "MCU"), ("IMU_A", "IMU A"), ("IMU_B", "IMU B"), ("EMG", "EMG"),
                ("MCP", "MCP4725"), ("HBRIDGE", "H-BRIDGE"), ("FES", "FES"),
                ("SAFETY", "SAFETY"), ("DATA", "DATA"),
            )):
                chip = tk.Frame(chips, bg=COLORS["panel_2"], highlightthickness=1, highlightbackground=COLORS["line"])
                chip.pack(side="left", padx=(0 if index == 0 else 4, 4), pady=1)
                tk.Label(chip, text=label, bg=COLORS["panel_2"], fg=COLORS["muted"],
                         font=("Segoe UI Semibold", 7)).pack(side="left", padx=(7, 4), pady=5)
                value = tk.Label(chip, text="--", bg=COLORS["panel_2"], fg=COLORS["muted"],
                                 font=("Segoe UI Semibold", 8))
                value.pack(side="left", padx=(0, 7), pady=5)
                self.health_labels[key] = value

            metrics = tk.Frame(self.main, bg=COLORS["bg"])
            metrics.pack(fill="x", padx=22, pady=(0, 10))
            for index in range(6):
                metrics.grid_columnconfigure(index, weight=1, uniform="metric")
            self.angle_card = MetricCard(metrics, "Sudut", "°", COLORS["cyan"])
            self.emg_card = MetricCard(metrics, "EMG RMS", "mV", COLORS["yellow"])
            self.pwm_card = MetricCard(metrics, "Lebar Pulsa", "µs", COLORS["blue"])
            self.frequency_card = MetricCard(metrics, "Frekuensi", "Hz", COLORS["cyan"])
            self.current_card = MetricCard(metrics, "Arus FES", "mA", COLORS["green"])
            self.fsm_card = MetricCard(metrics, "FSM", "", COLORS["green"])
            cards = (
                self.angle_card, self.emg_card, self.pwm_card,
                self.frequency_card, self.current_card, self.fsm_card,
            )
            for index, card in enumerate(cards):
                card.grid(
                    row=0, column=index, sticky="nsew",
                    padx=(0 if index == 0 else 3, 0 if index == len(cards) - 1 else 3),
                )

            state_band = tk.Frame(self.main, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
            state_band.pack(fill="x", padx=22, pady=(0, 10))
            tk.Label(state_band, text="STATE", bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Segoe UI Semibold", 8)).pack(side="left", padx=(14, 12), pady=9)
            self.state_labels: Dict[str, tk.Label] = {}
            for state_name in ("IDLE", "KONTRAKSI", "RELAKSASI"):
                chip = tk.Label(state_band, text=state_name, bg=COLORS["panel_2"], fg=COLORS["muted"],
                                font=("Segoe UI Semibold", 9), padx=14, pady=5)
                chip.pack(side="left", padx=(0, 7), pady=5)
                self.state_labels[state_name] = chip
            self.state_labels["IDLE"].configure(bg="#123B37", fg=COLORS["green"])

            self.page_host = tk.Frame(self.main, bg=COLORS["bg"])
            self.page_host.pack(fill="both", expand=True, padx=22)
            self.page_host.grid_rowconfigure(0, weight=1)
            self.page_host.grid_columnconfigure(0, weight=1)
            self._build_calibration_page()
            self._build_auto_page()
            self._build_manual_page()
            self._build_emg_page()

            footer = tk.Frame(self.main, bg=COLORS["bg"], height=34)
            footer.pack(fill="x", padx=22, pady=(8, 10))
            self.status_dot = tk.Label(footer, text="●", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9))
            self.status_dot.pack(side="left")
            self.status_label = tk.Label(footer, text="Menyiapkan aplikasi...", bg=COLORS["bg"],
                                         fg=COLORS["muted"], font=("Segoe UI", 9))
            self.status_label.pack(side="left", padx=(6, 0))
            self.mode_label = tk.Label(footer, text="MODE: IDLE", bg=COLORS["bg"], fg=COLORS["muted"],
                                       font=("Segoe UI Semibold", 9))
            self.mode_label.pack(side="right")
            self.timer_label = tk.Label(footer, text="00:00", bg=COLORS["bg"], fg=COLORS["muted"],
                                        font=("Segoe UI", 9))
            self.timer_label.pack(side="right", padx=(0, 18))

        def _panel(self, parent: tk.Misc) -> tk.Frame:
            return tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])

        def _build_calibration_page(self) -> None:
            page = tk.Frame(self.page_host, bg=COLORS["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=3)
            page.grid_columnconfigure(1, weight=2)
            page.grid_rowconfigure(0, weight=1)

            choices = self._panel(page)
            choices.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            tk.Label(choices, text="Persiapan sensor", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=20, pady=(18, 3))
            tk.Label(choices, text="Pilih proses yang diperlukan sebelum sesi. Rekalibrasi EMG digunakan jika baseline/filter EMG perlu diulang.",
                     bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=20)

            options = tk.Frame(choices, bg=COLORS["panel"])
            options.pack(fill="both", expand=True, padx=20, pady=18)
            option_specs = (
                ("SUDUT / IMU", "Set referensi dua IMU dan validasi sudut.", "Kalibrasi Sudut", self.calibrate_angle, COLORS["cyan"]),
                ("REKALIBRASI EMG", "Ulangi kalibrasi baseline/filter EMG jika sinyal bermasalah. Nilai MVC lama akan dibatalkan.", "Rekalibrasi EMG", self.calibrate_emg, COLORS["yellow"]),
                ("MVC / EMG", "Ambil nilai Maximum Voluntary Contraction (MVC) sebagai referensi EMG setelah EMG siap.", "Ambil Nilai MVC", self.capture_mvc, COLORS["green"]),
            )
            self.calibration_buttons = []
            for title, description, button_text, command, accent in option_specs:
                card = tk.Frame(options, bg=COLORS["panel_2"], highlightthickness=1, highlightbackground=COLORS["line"])
                card.pack(fill="x", pady=(0, 12))
                tk.Frame(card, bg=accent, width=4).pack(side="left", fill="y")
                body = tk.Frame(card, bg=COLORS["panel_2"])
                body.pack(side="left", fill="both", expand=True, padx=14, pady=15)
                tk.Label(body, text=title, bg=COLORS["panel_2"], fg=COLORS["text"],
                         font=("Segoe UI Semibold", 10)).pack(anchor="w")
                tk.Label(body, text=description, bg=COLORS["panel_2"], fg=COLORS["muted"],
                         font=("Segoe UI", 9), wraplength=520, justify="left").pack(anchor="w", pady=(3, 0))
                btn = tk.Button(card, text=button_text, command=command, bg=COLORS["panel"], fg=COLORS["text"],
                                activebackground=COLORS["line"], activeforeground=COLORS["white"],
                                relief="flat", bd=0, font=("Segoe UI Semibold", 9), padx=12, pady=9, cursor="hand2")
                btn.pack(side="right", padx=12)
                self.calibration_buttons.append(btn)

            self.calibration_message = tk.Label(choices, text="Jika EMG direkalibrasi, nilai MVC harus diambil ulang sebelum Mode Auto.",
                                                bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9))
            self.calibration_message.pack(anchor="w", padx=20, pady=(0, 17))

            live = self._panel(page)
            live.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            tk.Label(live, text="Validasi sensor", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=18, pady=(18, 12))
            self.cal_imu_a = self._status_value(live, "IMU A", "--", COLORS["cyan"])
            self.cal_imu_b = self._status_value(live, "IMU B", "--", COLORS["cyan"])
            self.cal_joint = self._status_value(live, "Sudut", "-- °", COLORS["yellow"])
            self.cal_emg = self._status_value(live, "EMG RMS", "-- mV", COLORS["green"])
            self.cal_emg_state = self._status_value(live, "Status EMG", "--", COLORS["yellow"])
            self.cal_angle_state = self._status_value(live, "Kalibrasi sudut", "BELUM", COLORS["muted"])
            self.cal_mvc_value = self._status_value(live, "Nilai MVC", "-- mV", COLORS["green"])
            self.cal_mvc_state = self._status_value(live, "Status MVC", "BELUM", COLORS["muted"])
            self.pages["CAL"] = page

        def _status_value(self, parent: tk.Misc, title: str, value: str, accent: str) -> tk.Label:
            row = tk.Frame(parent, bg=COLORS["panel_2"], highlightthickness=1, highlightbackground=COLORS["line"])
            row.pack(fill="x", padx=18, pady=(0, 8))
            tk.Label(row, text=title, bg=COLORS["panel_2"], fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(side="left", padx=11, pady=9)
            lbl = tk.Label(row, text=value, bg=COLORS["panel_2"], fg=accent,
                           font=("Segoe UI Semibold", 9))
            lbl.pack(side="right", padx=11, pady=9)
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
            if self.telemetry.output_active is True or self.active_mode not in {"IDLE", "E-STOP"}:
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
            self.cal_mvc_value.configure(text="-- mV")
            self.cal_mvc_state.configure(text="BELUM")
            self.cal_emg_state.configure(text="REKALIBRASI")
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
            tk.Label(control, text="Set parameter awal", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=20, pady=(18, 3))
            tk.Label(control, text="Mode Auto mengendalikan stimulasi menuju target sudut berdasarkan logika kontrol pada MCU.",
                     bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=20)

            self.auto_current_var = tk.DoubleVar(value=PROJECT_FIXED_CURRENT_MA)
            self.auto_frequency_var = tk.DoubleVar(value=PROJECT_FIXED_FREQUENCY_HZ)
            self.auto_pwm_var = tk.DoubleVar(value=PROJECT_PWM_DEFAULT_US)
            self.auto_angle_var = tk.DoubleVar(value=PROJECT_DEFAULT_TARGET_ANGLE_DEG)

            form = tk.Frame(control, bg=COLORS["panel"])
            form.pack(fill="x", padx=20, pady=(18, 12))
            for col in range(4):
                form.grid_columnconfigure(col, weight=1, uniform="auto_params")
            widgets = (
                self._number_input_at(form, 0, 0, "Arus", "mA", self.auto_current_var, 0, PROJECT_CURRENT_MAX_MA, 0.5),
                self._number_input_at(form, 0, 1, "Frekuensi", "Hz", self.auto_frequency_var, PROJECT_FREQUENCY_MIN_HZ, PROJECT_FREQUENCY_MAX_HZ, 1),
                self._number_input_at(form, 0, 2, "Lebar Pulsa", "µs", self.auto_pwm_var, PROJECT_PWM_MIN_US, PROJECT_PWM_MAX_US, 10),
                self._number_input_at(form, 0, 3, "Target sudut", "°", self.auto_angle_var, 0, 90, 1),
            )
            self.control_widgets.extend(widgets)

            live = tk.Frame(control, bg=COLORS["panel"])
            live.pack(fill="x", padx=20, pady=(0, 12))
            for col in range(3): live.grid_columnconfigure(col, weight=1, uniform="autolive")
            self.target_angle_value = self._mini_metric(live, 0, "TARGET", "35.0°")
            self.error_angle_value = self._mini_metric(live, 1, "ERROR", "--°")
            self.auto_fsm_value = self._mini_metric(live, 2, "FSM", "IDLE")

            button_row = tk.Frame(control, bg=COLORS["panel"])
            button_row.pack(fill="x", padx=20, pady=(0, 18))
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
            tk.Label(status, text="FSM & FES", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=18, pady=(18, 8))
            self.auto_phase_label = tk.Label(status, text="IDLE", bg=COLORS["panel"], fg=COLORS["green"],
                                             font=("Segoe UI Semibold", 22))
            self.auto_phase_label.pack(anchor="w", padx=18, pady=(2, 5))
            self.auto_message_label = tk.Label(status, text="Hubungkan perangkat atau gunakan demo.", bg=COLORS["panel"],
                                               fg=COLORS["muted"], justify="left", wraplength=330, font=("Segoe UI", 9))
            self.auto_message_label.pack(anchor="w", padx=18, pady=(0, 12))
            self.auto_state_live = self._status_value(status, "FSM", "IDLE", COLORS["green"])
            self.mcp_detail_label = self._status_value(status, "MCP4725", "--", COLORS["cyan"])
            self.hbridge_detail_label = self._status_value(status, "H-Bridge", "--", COLORS["cyan"])
            self.dac_detail_label = self._status_value(status, "DAC command", "-- / 4095", COLORS["cyan"])
            self.dac_voltage_label = self._status_value(status, "DAC voltage", "-- V", COLORS["cyan"])
            self.fes_output_label = self._status_value(status, "FES output", "OFF", COLORS["green"])
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
            box.grid(row=row_index, column=column, sticky="ew", padx=6, pady=(0, 12))
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
            tk.Label(control, text="Set parameter awal", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=20, pady=(18, 3))
            tk.Label(control, text="Mode Manual menjalankan parameter FES sesuai nilai operator dengan siklus ACTIVE/REST.",
                     bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=20)

            self.manual_current_var = tk.DoubleVar(value=PROJECT_FIXED_CURRENT_MA)
            self.manual_frequency_var = tk.DoubleVar(value=PROJECT_FIXED_FREQUENCY_HZ)
            self.manual_pwm_var = tk.DoubleVar(value=PROJECT_PWM_DEFAULT_US)
            self.manual_active_var = tk.DoubleVar(value=5.0)
            self.manual_rest_var = tk.DoubleVar(value=5.0)

            form = tk.Frame(control, bg=COLORS["panel"])
            form.pack(fill="x", padx=20, pady=(18, 12))
            for col in range(3):
                form.grid_columnconfigure(col, weight=1, uniform="manual_params")
            widgets = (
                self._number_input_at(form, 0, 0, "Arus", "mA", self.manual_current_var, 0, PROJECT_CURRENT_MAX_MA, 0.5),
                self._number_input_at(form, 0, 1, "Frekuensi", "Hz", self.manual_frequency_var, PROJECT_FREQUENCY_MIN_HZ, PROJECT_FREQUENCY_MAX_HZ, 1),
                self._number_input_at(form, 0, 2, "Lebar Pulsa", "µs", self.manual_pwm_var, PROJECT_PWM_MIN_US, PROJECT_PWM_MAX_US, 10),
                self._number_input_at(form, 1, 0, "Durasi ACTIVE", "s", self.manual_active_var, 0.5, 120, 0.5),
                self._number_input_at(form, 1, 1, "Durasi REST", "s", self.manual_rest_var, 0.5, 120, 0.5),
            )
            self.control_widgets.extend(widgets)

            row = tk.Frame(control, bg=COLORS["panel"])
            row.pack(fill="x", padx=20, pady=(0, 18))
            self.manual_apply_button = tk.Button(row, text="Mulai Manual", command=self.apply_manual, bg=COLORS["blue"], fg="#061120",
                                                 activebackground="#7EC0FF", relief="flat", bd=0, font=("Segoe UI Semibold", 10), pady=12, cursor="hand2")
            self.manual_apply_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.control_widgets.append(self.manual_apply_button)
            tk.Button(row, text="Stop Sesi", command=self.stop_session, bg=COLORS["panel_2"], fg=COLORS["text"],
                      activebackground=COLORS["line"], activeforeground=COLORS["white"], relief="flat", bd=0,
                      font=("Segoe UI Semibold", 10), pady=12, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(6, 0))

            status = self._panel(page)
            status.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            tk.Label(status, text="Manual live", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=18, pady=(18, 10))
            self.manual_fsm_live = self._status_value(status, "FSM", "IDLE", COLORS["green"])
            self.manual_pwm_live = self._status_value(status, "Lebar Pulsa", "-- µs", COLORS["blue"])
            self.manual_frequency_live = self._status_value(status, "Frekuensi", "-- Hz", COLORS["cyan"])
            self.manual_current_live = self._status_value(status, "Arus", "-- mA", COLORS["green"])
            self.manual_mcp_live = self._status_value(status, "MCP4725", "--", COLORS["cyan"])
            self.manual_hbridge_live = self._status_value(status, "H-Bridge", "--", COLORS["cyan"])
            self.manual_output_live = self._status_value(status, "FES output", "OFF", COLORS["green"])
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
            heading.pack(fill="x", padx=18, pady=(16, 4))
            tk.Label(heading, text="Sinyal EMG", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(side="left")
            self.quality_label = tk.Label(panel, text="Signal quality: menunggu", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9))
            self.quality_label.pack(anchor="w", padx=18)
            self.movement_wait_label = tk.Label(panel, text="MENUNGGU GERAKAN", bg=COLORS["panel"], fg=COLORS["yellow"],
                                                font=("Segoe UI Semibold", 14))
            self.movement_wait_label.pack(anchor="w", padx=18, pady=(7, 0))
            self.emg_plot = EMGPlot(panel)
            self.emg_plot.pack(fill="both", expand=True, padx=12, pady=(8, 12))

            states = self._panel(page)
            states.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            tk.Label(states, text="Parameter monitoring", bg=COLORS["panel"], fg=COLORS["text"],
                     font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=18, pady=(18, 10))
            self.monitor_angle = self._status_value(states, "Sudut", "-- °", COLORS["cyan"])
            self.monitor_error = self._status_value(states, "Error sudut", "-- °", COLORS["yellow"])
            self.monitor_delta_error = self._status_value(states, "Delta Error", "-- °", COLORS["blue"])
            self.monitor_mvc = self._status_value(states, "Nilai MVC", "-- mV", COLORS["green"])
            self.monitor_active_duration = self._status_value(states, "Durasi ACTIVE", "-- s", COLORS["blue"])
            self.monitor_rest_duration = self._status_value(states, "Durasi REST", "-- s", COLORS["blue"])
            self.emg_quality_state_label = self._status_value(states, "Signal quality", "--", COLORS["green"])
            self.pages["EMG"] = page

        def show_page(self, page: str) -> None:
            if page not in self.pages:
                return
            self.active_page = page
            self.pages[page].tkraise()
            titles = {
                "CAL": ("Persiapan Sensor", "Kalibrasi sudut IMU atau pengambilan nilai MVC EMG"),
                "AUTO": ("Mode Auto", "Set arus, frekuensi, PWM, target sudut, dan pantau FSM"),
                "MANUAL": ("Mode Manual", "Parameter FES manual dengan durasi ACTIVE dan REST"),
                "EMG": ("Monitoring EMG", "Pantau sinyal EMG, sudut, error sudut, delta error, MVC, dan durasi ACTIVE/REST"),
            }
            title, subtitle = titles[page]
            self.page_title.configure(text=title)
            self.page_subtitle.configure(text=subtitle)
            for key, button in self.nav_buttons.items():
                selected = key == page
                button.configure(bg=COLORS["panel_2"] if selected else "#0E1728",
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
                messagebox.showerror("Nilai tidak valid", "Arus, frekuensi, PWM, ACTIVE, dan REST harus berupa angka.")
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
                    f"PWM / pulse width harus {PROJECT_PWM_MIN_US:.0f}–{PROJECT_PWM_MAX_US:.0f} µs.",
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
                messagebox.showerror("Nilai tidak valid", "Arus, frekuensi, PWM, dan target sudut harus berupa angka.")
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
                    f"PWM / pulse width harus {PROJECT_PWM_MIN_US:.0f}–{PROJECT_PWM_MAX_US:.0f} µs.",
                )
                return None
            if not 0.0 <= angle <= 90.0:
                messagebox.showerror("Nilai di luar rentang", "Target sudut harus 0–90°.")
                return None
            return angle, current, frequency, pwm

        def _current_fsm_state(self) -> str:
            raw = self.telemetry.fsm_state or self.telemetry.phase or "IDLE"
            return normalize_fsm_state(raw)

        def _update_state_indicator(self, state: str) -> None:
            normalized = normalize_fsm_state(state)
            for name, label in self.state_labels.items():
                active = name == normalized
                label.configure(
                    bg="#123B37" if active else COLORS["panel_2"],
                    fg=COLORS["green"] if active else COLORS["muted"],
                )

        def _start_snapshot_safe(self) -> bool:
            fault = (self.telemetry.fault or "NONE").strip().upper()
            quality = (self.telemetry.signal_quality or "UNKNOWN").strip().upper()
            fsm = self._current_fsm_state()
            return bool(
                self.telemetry.output_active is False
                and fsm == "IDLE"
                and self.telemetry.current_ma is not None
                and self.telemetry.current_ma <= 1.0
                and fault in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"}
                and quality in {"GOOD", "BAIK", "OK", "VALID"}
            )

        def _control_ready_for_start(self) -> bool:
            if not self.manager.can_control():
                self._set_status("Kontrol belum siap: hubungkan MCU atau gunakan Demo.", COLORS["red"])
                return False
            if self.data_stale:
                self._set_status("Kontrol dikunci karena telemetry belum aktif atau sudah stale.", COLORS["red"])
                return False
            if self.telemetry.output_active is not False:
                self._set_status("START ditolak: MCU belum mengonfirmasi keluaran OFF.", COLORS["red"])
                return False
            if self._current_fsm_state() != "IDLE":
                self._set_status(f"START ditolak: FSM belum IDLE ({self._current_fsm_state()}).", COLORS["red"])
                return False
            if self.telemetry.current_ma is None or self.telemetry.current_ma > 1.0:
                self._set_status("START ditolak: arus saat output OFF belum aman (harus <= 1.0 mA).", COLORS["red"])
                return False
            fault = (self.telemetry.fault or "NONE").strip().upper()
            if fault not in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"}:
                self._set_status(f"START ditolak: fault MCU aktif ({fault}).", COLORS["red"])
                return False
            quality = (self.telemetry.signal_quality or "UNKNOWN").strip().upper()
            if quality not in {"GOOD", "BAIK", "OK", "VALID"}:
                self._set_status(f"START ditolak: kualitas EMG tidak valid ({quality}).", COLORS["red"])
                return False
            return True

        def start_auto(self) -> None:
            if not self._control_ready_for_start():
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
            ok, message = self.manager.send_command(
                "START_AUTO",
                angle_target_deg=round(angle, 2),
                current_ma=round(current, 3),
                frequency_hz=round(frequency, 2),
                pulse_width_us=round(pwm, 1),
            )
            self._set_status(message, COLORS["green"] if ok else COLORS["red"])
            if ok:
                self.pending_mode = "AUTO"
                self.pending_start_deadline = time.monotonic() + 1.5
                self.active_mode = "PENDING AUTO"
                self.auto_running = False
                self.auto_phase_label.configure(text="MENUNGGU GERAKAN", fg=COLORS["yellow"])
                self.auto_message_label.configure(text="START Auto dikirim. FSM boleh tetap IDLE sampai niat gerak terdeteksi.")
                self._refresh_mode_label()
                self._refresh_control_state(force=True)

        def apply_manual(self) -> None:
            if not self._control_ready_for_start():
                return
            setpoints = self._validated_setpoints(
                self.manual_current_var, self.manual_frequency_var, self.manual_pwm_var,
                self.manual_active_var, self.manual_rest_var,
            )
            if setpoints is None:
                return
            current, frequency, pwm, active_s, rest_s = setpoints
            ok, message = self.manager.send_command(
                "SET_MANUAL",
                current_ma=round(current, 3),
                frequency_hz=round(frequency, 2),
                pulse_width_us=round(pwm, 1),
                active_duration_s=round(active_s, 2),
                rest_duration_s=round(rest_s, 2),
                output=True,
            )
            self._set_status(message, COLORS["green"] if ok else COLORS["red"])
            if ok:
                self.pending_mode = "MANUAL"
                self.pending_start_deadline = time.monotonic() + 1.5
                self.active_mode = "PENDING MANUAL"
                self.auto_running = False
                self._refresh_mode_label()
                self._set_status("START Manual dikirim; status terapi mengikuti telemetry STM32.", COLORS["yellow"])
                self._refresh_control_state(force=True)

        def stop_session(self) -> None:
            if self.manager.estop_latched:
                self._set_status("E-STOP sudah aktif; keluaran tetap terkunci.", COLORS["red"])
                return
            if self.active_mode == "IDLE" and self.pending_mode is None and self.telemetry.output_active is False:
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
            self.active_mode = "STOPPING"
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
            self.active_mode = "E-STOP"
            self.auto_running = False
            self.session_started_at = None
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
            fsm = self._current_fsm_state()
            return bool(
                state.get("connected") and not self.data_stale
                and fsm in {"EMERGENCY", "THERAPY_STOP"}
                and self.telemetry.output_active is False
            )

        def reset_estop(self) -> None:
            if not self._fresh_estop_off_confirmation():
                self._set_status(
                    "Reset tersedia hanya saat STM32 melaporkan EMERGENCY/THERAPY_STOP dan output OFF.",
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
            self.auto_phase_label.configure(text="RESET...", fg=COLORS["yellow"])
            self.auto_message_label.configure(text="Reset dikirim. Output tetap OFF sampai STM32 kembali IDLE.")
            self._set_status(message, COLORS["yellow"])
            self._refresh_control_state(force=True)

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
            if self.manager.state().get("port_open") or self.manager.connection_kind == "DEMO":
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
            self.active_mode = "IDLE"
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
            self.log_button.configure(text="Stop CSV", bg="#123B37", fg=COLORS["green"])
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
            self.connect_button.configure(text="Putus" if port_open else "Hubungkan")
            if estop and not connected:
                self.safety_badge.configure(text="OUTPUT UNKNOWN · E-STOP LOKAL", bg=COLORS["red_dark"], fg=COLORS["white"])
            elif estop:
                badge_text = "OUTPUT OFF · E-STOP" if self.estop_output_confirmed else "OUTPUT UNKNOWN · E-STOP"
                self.safety_badge.configure(text=badge_text, bg=COLORS["red_dark"], fg=COLORS["white"])
            elif self.active_mode == "E-STOP":
                self.safety_badge.configure(text="TUNGGU SAFE_IDLE", bg="#3B3220", fg=COLORS["yellow"])
            elif kind == "DEMO":
                self.safety_badge.configure(text="DEMO AMAN", bg="#123B37", fg=COLORS["green"])
            elif kind == "SERIAL" and connected:
                self.safety_badge.configure(text="KONTROL SERIAL", bg="#123B37", fg=COLORS["green"])
            else:
                badge = "MENUNGGU TELEMETRY" if port_open else "TERPUTUS"
                self.safety_badge.configure(text=badge, bg=COLORS["panel_2"], fg=COLORS["muted"])
                self.data_stale = True
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
                self.auto_message_label.configure(text="CONNECTED berdasarkan telemetry STM32 aktif.")
            self._refresh_system_health()

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
                # FSM hanya berasal dari field fsm_state STM32; phase bukan FSM.
                fresh.fsm_state = normalize_fsm_state(fresh.fsm_state)
                self.telemetry = fresh
            else:
                # Partial/legacy frames may update non-safety fields such as RMS/status.
                self.telemetry.merge(update)

            t = self.telemetry
            fsm = normalize_fsm_state(t.fsm_state or t.phase)
            self._update_state_indicator(fsm)

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
                fsm == "EMERGENCY" or t.emergency is True
                or (t.emergency is None and (phase_upper in {"E_STOP", "ESTOP"} or fault_upper == "EMERGENCY"))
            )
            emergency_clear = (
                t.emergency is False
                or (t.emergency is None and phase_upper in {"IDLE", "SAFE_IDLE"} and fault_upper in {"", "NONE", "0", "OK", "FALSE", "NO", "CLEAR"})
            )

            if control_frame and fsm == "THERAPY_STOP":
                # Controlled stop dari STM32; jangan diubah menjadi EMERGENCY.
                self.active_mode = t.mode if t.mode in {"AUTO", "MANUAL"} else "AUTO"
                self.auto_running = False
                self.pending_mode = None; self.pending_start_deadline = None; self.pending_stop_deadline = None
                self.auto_phase_label.configure(text="THERAPY_STOP", fg=COLORS["yellow"])
                self.auto_message_label.configure(text="Terapi dihentikan STM32. Output OFF; tekan RESET untuk sesi baru.")
                self.safety_badge.configure(text="THERAPY_STOP · OFF", bg="#3B3220", fg=COLORS["yellow"])
                self._refresh_mode_label(); self._refresh_control_state(force=True)

            elif control_frame and emergency_active:
                self.manager.estop_latched = True
                self.active_mode = "E-STOP"
                self.auto_running = False
                self.session_started_at = None
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
                and emergency_clear
                and t.output_active is False
                and fsm == "IDLE"
                and self.pending_reset_estop
            ):
                self.manager.confirm_estop_reset()
                self.pending_reset_estop = False
                self.pending_reset_deadline = None
                self.estop_output_confirmed = True
                self.active_mode = "IDLE"
                self.auto_running = False
                self.session_started_at = None
                self.auto_phase_label.configure(text="IDLE", fg=COLORS["green"])
                self.auto_message_label.configure(text="Emergency OFF. Sistem kembali IDLE dan output tetap OFF.")
                self.safety_badge.configure(text="SAFE · OUTPUT OFF", bg="#123B37", fg=COLORS["green"])
                self._set_status("RESET E-STOP dikonfirmasi STM32.", COLORS["green"])
                self._refresh_mode_label()
                self._refresh_control_state(force=True)

            # Session confirmation and stop handling.
            if control_frame and self.pending_stop_deadline is not None and t.output_active is False and fsm == "IDLE":
                self.pending_stop_deadline = None
                self.active_mode = "IDLE"
                self.auto_running = False
                self.session_started_at = None
                self.auto_phase_label.configure(text="IDLE", fg=COLORS["green"])
                self.auto_message_label.configure(text="Sesi berhenti; output OFF dikonfirmasi MCU.")
                self._set_status("STOP dikonfirmasi: FSM IDLE dan output OFF.", COLORS["green"])
                self._refresh_mode_label()
            elif control_frame and self.pending_mode is not None and (
                t.mode == self.pending_mode or phase_matches_mode(self.pending_mode, t.phase)
            ):
                confirmed_mode = self.pending_mode
                self.pending_mode = None
                self.pending_start_deadline = None
                self.active_mode = confirmed_mode
                self.auto_running = confirmed_mode == "AUTO"
                self.session_started_at = time.monotonic()
                if confirmed_mode == "AUTO" and fsm == "IDLE":
                    self._set_status("Mode Auto aktif; FSM menunggu niat gerak.", COLORS["green"])
                else:
                    self._set_status(f"Mode {confirmed_mode.title()} aktif; FSM {fsm}.", COLORS["green"])
                self._refresh_mode_label()
            elif (
                control_frame
                and self.active_mode in {"AUTO", "MANUAL"}
                and fsm == "IDLE"
                and t.output_active is False
                and phase_confirms_stopped(t.phase)
                and not phase_matches_mode(self.active_mode, t.phase)
            ):
                prior = self.active_mode
                self.active_mode = "IDLE"
                self.auto_running = False
                self.session_started_at = None
                self._set_status(f"Mode {prior.title()} selesai; MCU kembali IDLE.", COLORS["green"])
                self._refresh_mode_label()
            elif control_frame and self.active_mode == "IDLE" and self.pending_mode is None and t.output_active is True:
                self.emergency_stop("unexpected_output_active")
                self._set_status("Output aktif tanpa START GUI; E-STOP dikirim.", COLORS["red"])

            # Mode terapi juga berasal dari STM32, bukan transisi buatan GUI.
            if control_frame and t.mode in {"AUTO", "MANUAL"} and fsm not in {"EMERGENCY"}:
                self.active_mode = t.mode
            elif control_frame and t.mode in {"NONE", "IDLE"} and fsm == "IDLE" and not self.pending_reset_estop:
                self.active_mode = "IDLE"

            # Main metrics.
            if t.current_ma is not None:
                self.current_card.set(f"{t.current_ma:.2f}")
            if t.angle_deg is not None:
                self.angle_card.set(f"{t.angle_deg:.1f}")
            if t.emg_rms_mv is not None:
                self.emg_card.set(f"{t.emg_rms_mv:.3f}")
            if t.frequency_hz is not None:
                self.frequency_card.set(f"{t.frequency_hz:.1f}")
            pulse_width_value = t.pulse_width_us
            if pulse_width_value is None:
                pwm_compat = t.pwm_pct if t.pwm_pct is not None else t.pwm_command_pct
                if pwm_compat is not None:
                    pulse_width_value = pwm_pct_to_us(pwm_compat)
            if pulse_width_value is not None:
                self.pwm_card.set(f"{pulse_width_value:.1f}")
            target_angle = t.angle_target_deg
            if target_angle is None:
                try:
                    target_angle = float(self.auto_angle_var.get())
                except (ValueError, tk.TclError):
                    target_angle = None
            angle_error = t.angle_error_deg
            if angle_error is None and target_angle is not None and t.angle_deg is not None:
                angle_error = target_angle - t.angle_deg
            self.fsm_card.set(fsm, color=COLORS["green"] if fsm == "IDLE" else COLORS["blue"])

            # Auto page.
            self.target_angle_value.configure(text="--°" if target_angle is None else f"{target_angle:.1f}°")
            self.error_angle_value.configure(text="--°" if angle_error is None else f"{angle_error:.1f}°")
            self.auto_fsm_value.configure(text=fsm)
            self.auto_state_live.configure(text=fsm)
            if self.active_mode == "AUTO" and phase_matches_mode("AUTO", t.phase) and fsm == "IDLE":
                self.auto_phase_label.configure(text="MENUNGGU GERAKAN", fg=COLORS["yellow"])
                self.auto_message_label.configure(text="Auto aktif. FSM menunggu niat gerak dari EMG.")
            else:
                self.auto_phase_label.configure(text=fsm, fg=COLORS["green"] if fsm == "IDLE" else COLORS["blue"])
            self.mcp_detail_label.configure(text=t.mcp4725_status or "--")
            hbridge_text = t.hbridge_status
            if (hbridge_text or "").upper() in {"", "WAITING", "UNKNOWN", "--"}:
                hbridge_text = "READY" if (t.mcp4725_status or "").upper() in {"OK", "READY"} else "NOT_READY" if (t.mcp4725_status or "").upper() in {"ERROR", "NOT_READY", "OFF"} else "--"
            self.hbridge_detail_label.configure(text=hbridge_text)
            self.dac_detail_label.configure(text="-- / 4095" if t.dac_raw is None else f"{t.dac_raw} / 4095")
            self.dac_voltage_label.configure(text="-- V" if t.dac_voltage_v is None else f"{t.dac_voltage_v:.3f} V")
            self.fes_output_label.configure(text="ACTIVE" if t.output_active is True else "OFF" if t.output_active is False else "--")

            # Manual page.
            self.manual_fsm_live.configure(text=fsm)
            self.manual_pwm_live.configure(text="-- µs" if pulse_width_value is None else f"{pulse_width_value:.1f} µs")
            self.manual_frequency_live.configure(text="-- Hz" if t.frequency_hz is None else f"{t.frequency_hz:.1f} Hz")
            self.manual_current_live.configure(text="-- mA" if t.current_ma is None else f"{t.current_ma:.2f} mA")
            self.manual_mcp_live.configure(text=t.mcp4725_status or "--")
            self.manual_hbridge_live.configure(text=hbridge_text)
            self.manual_output_live.configure(text="ACTIVE" if t.output_active is True else "OFF" if t.output_active is False else "--")

            # Sensor preparation page.
            self.cal_imu_a.configure(text=(t.imu_a_status or "--") + ("" if t.imu_a_angle_deg is None else f" · {t.imu_a_angle_deg:.1f}°"))
            self.cal_imu_b.configure(text=(t.imu_b_status or "--") + ("" if t.imu_b_angle_deg is None else f" · {t.imu_b_angle_deg:.1f}°"))
            self.cal_joint.configure(text="-- °" if t.angle_deg is None else f"{t.angle_deg:.1f} °")
            self.cal_emg.configure(text="-- mV" if t.emg_rms_mv is None else f"{t.emg_rms_mv:.3f} mV")
            emg_state = (t.emg_status or "--").upper()
            self.cal_emg_state.configure(
                text=emg_state,
                fg=COLORS["green"] if emg_state == "READY" else COLORS["yellow"] if emg_state in {"SETTLING", "CALIBRATING", "RECALIBRATING"} else COLORS["red"] if "FAULT" in emg_state else COLORS["muted"],
            )
            self.cal_angle_state.configure(text="OK" if t.angle_calibrated is True else "BELUM" if t.angle_calibrated is False else "--")
            mvc_ready = t.mvc_ready if t.mvc_ready is not None else t.emg_calibrated
            self.cal_mvc_value.configure(text="-- mV" if t.mvc_value_mv is None else f"{t.mvc_value_mv:.3f} mV")
            self.cal_mvc_state.configure(text="OK" if mvc_ready is True else "BELUM" if mvc_ready is False else "--")

            # Monitoring EMG. PWM/frekuensi/arus/FSM sudah tersedia pada kartu atas,
            # sehingga panel kanan hanya memuat parameter tambahan yang tidak duplikatif.
            self.emg_quality_state_label.configure(text=t.signal_quality or "--")
            self.monitor_angle.configure(text="-- °" if t.angle_deg is None else f"{t.angle_deg:.1f} °")
            self.monitor_error.configure(text="-- °" if angle_error is None else f"{angle_error:.1f} °")
            delta_error = t.delta_error_deg
            if delta_error is None and angle_error is not None:
                if self._last_monitor_angle_error is not None:
                    delta_error = angle_error - self._last_monitor_angle_error
                self._last_monitor_angle_error = angle_error
            elif angle_error is not None:
                self._last_monitor_angle_error = angle_error
            self.monitor_delta_error.configure(text="-- °" if delta_error is None else f"{delta_error:.2f} °")
            self.monitor_mvc.configure(text="-- mV" if t.mvc_value_mv is None else f"{t.mvc_value_mv:.3f} mV")
            active_s = t.active_duration_s
            rest_s = t.rest_duration_s
            # Manual mempunyai input durasi; Auto menerima durasi dari FSM/telemetry MCU.
            if active_s is None and self.active_mode == "MANUAL":
                try:
                    active_s = float(self.manual_active_var.get())
                except (ValueError, tk.TclError):
                    active_s = None
            if rest_s is None and self.active_mode == "MANUAL":
                try:
                    rest_s = float(self.manual_rest_var.get())
                except (ValueError, tk.TclError):
                    rest_s = None
            self.monitor_active_duration.configure(text="-- s" if active_s is None else f"{active_s:.1f} s")
            self.monitor_rest_duration.configure(text="-- s" if rest_s is None else f"{rest_s:.1f} s")
            if fsm == "IDLE":
                movement_text = "MENUNGGU GERAKAN"
                movement_color = COLORS["yellow"]
            elif fsm in {"ACTIVE / NORMAL", "ACTIVE / FATIGUE"}:
                movement_text = fsm
                movement_color = COLORS["blue"]
            else:
                movement_text = "RELAKSASI · REST"
                movement_color = COLORS["green"]
            self.movement_wait_label.configure(text=movement_text, fg=movement_color)
            self.quality_label.configure(text=f"Signal quality: {t.signal_quality.title() if t.signal_quality else 'menunggu'}")
            self.emg_plot.add(t.emg_rms_mv)

            # Fault/quality hanya ditampilkan. Keputusan FSM/emergency tetap milik STM32.
            self._refresh_system_health()
            self.logger.log(
                self.telemetry,
                source="demo" if self.manager.connection_kind == "DEMO" else "serial",
                connection=self.manager.port_name,
                mode=self.active_mode,
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
                if u in {"OK", "READY", "GOOD", "BAIK", "VALID", "ACTIVE", "ONLINE", "LIVE"}: return "ok"
                if u in {"WAITING", "WAIT", "CALIBRATING", "INIT", "UNKNOWN", "--", "", "PORT OPEN"}: return "warn"
                return "bad"

            self._set_health("IMU_A", t.imu_a_status or "--", sensor_level(t.imu_a_status))
            self._set_health("IMU_B", t.imu_b_status or "--", sensor_level(t.imu_b_status))
            if t.emg_status:
                emg_text = t.emg_status
            elif (t.signal_quality or "").upper() in {"GOOD", "BAIK", "OK", "VALID"}:
                emg_text = "OK"
            elif t.emg_rms_mv is not None and link_live:
                emg_text = "LIVE"
            else:
                emg_text = t.signal_quality or "--"
            self._set_health("EMG", emg_text, sensor_level(emg_text))
            self._set_health("MCP", t.mcp4725_status or "--", sensor_level(t.mcp4725_status))
            hbridge_text = t.hbridge_status
            if (hbridge_text or "").upper() in {"", "WAITING", "UNKNOWN", "--"}:
                hbridge_text = "READY" if (t.mcp4725_status or "").upper() in {"OK", "READY"} else "NOT_READY" if (t.mcp4725_status or "").upper() in {"ERROR", "NOT_READY", "OFF"} else "--"
            self._set_health("HBRIDGE", hbridge_text, sensor_level(hbridge_text))
            fes_text = t.fes_status or ("ACTIVE" if t.output_active is True else "READY" if t.output_active is False and not self.data_stale else "--")
            self._set_health("FES", fes_text, sensor_level(fes_text))

            fault = (t.fault or "").upper()
            if self.manager.estop_latched or self.active_mode == "E-STOP":
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
                and self.active_mode == "IDLE"
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
            if self.active_mode == "E-STOP":
                self.estop_output_confirmed = False
                self.safety_badge.configure(text="OUTPUT UNKNOWN · E-STOP", bg=COLORS["red_dark"], fg=COLORS["white"])
            self.current_card.set("--")
            self.angle_card.set("--")
            self.emg_card.set("--")
            self.pwm_card.set("--")
            self.frequency_card.set("--")
            self.fsm_card.set("DATA STALE", color=COLORS["muted"])
            self.quality_label.configure(text="Signal quality: data stale")
            self.movement_wait_label.configure(text="MENUNGGU DATA", fg=COLORS["muted"])
            self._refresh_system_health()

        def _check_data_health(self) -> None:
            state = self.manager.state()
            output_may_be_active = bool(
                self.active_mode in {"AUTO", "MANUAL", "STOPPING"}
                or self.pending_mode is not None
            )
            if not state.get("connected"):
                self.data_stale = True
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
                self._mark_control_values_stale()
                return
            age = time.monotonic() - self.last_telemetry_monotonic
            was_stale = self.data_stale
            self.data_stale = age > DATA_STALE_SECONDS
            if self.data_stale and not was_stale:
                self._set_status(f"DATA STALE {age:.1f} s · kontrol dikunci.", COLORS["red"])
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
            self._set_status("RESET tidak dikonfirmasi STM32.", COLORS["red"])
            self.auto_phase_label.configure(text="E-STOP", fg=COLORS["red"])
            self.auto_message_label.configure(
                text="STM32 belum kembali IDLE/OFF. Periksa penyebab fault lalu coba RESET lagi.",
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
                self.active_mode = "IDLE"
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
            elif self.active_mode in {"AUTO", "MANUAL", "STOPPING"}:
                self.emergency_stop("heartbeat_write_failed")
                self._set_status(f"Heartbeat gagal ({message}); E-STOP aktif.", COLORS["red"])

        def _update_timer(self) -> None:
            timer_ms = self.telemetry.therapy_timer_ms
            if timer_ms is None or self.data_stale:
                self.timer_label.configure(text="00:00" if timer_ms is None else "--:--")
                return
            total_seconds = max(0, int(timer_ms) // 1000)
            self.timer_label.configure(text=f"{total_seconds // 60:02d}:{total_seconds % 60:02d}")

        def _refresh_mode_label(self) -> None:
            self.mode_label.configure(text=f"MODE: {self.active_mode}",
                                      fg=COLORS["red"] if self.active_mode == "E-STOP" else COLORS["muted"])

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
        '{"type":"TEL","current_ma":12.5,"angle_deg":42,"pwm_pct":33,"pulse_width_us":199,'
        '"frequency_hz":35,"fsm_state":"KONTRAKSI","emg_rms_mv":0.48,'
        '"emg_status":"READY","signal_quality":"GOOD","phase":"KONTRAKSI","output_active":true,"fault":"NONE","emergency":0,"emergency_source":0,'
        '"mcp4725_status":"OK","hbridge_status":"READY",'
        '"active_duration_s":5,"rest_duration_s":4,"mvc_value_mv":1.2,"mvc_ready":true}'
    )
    assert parsed["current_ma"] == 12.5
    assert parsed["angle_deg"] == 42.0
    assert parsed["pwm_pct"] == 33.0
    assert parsed["pulse_width_us"] == 199.0
    assert parsed["emergency"] is False
    assert parsed["fsm_state"] == "ACTIVE / NORMAL"
    assert parsed["active_duration_s"] == 5.0
    assert parsed["mvc_ready"] is True
    assert parsed["hbridge_status"] == "READY"
    assert is_complete_control_telemetry(parsed)
    checks += 1

    assert normalize_fsm_state("contraction") == "ACTIVE / NORMAL"
    assert normalize_fsm_state("rest") == "REST"
    assert normalize_fsm_state("safe_idle") == "IDLE"
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
    checks += 1

    demo_manager = SerialManager()
    demo_manager.start_demo()
    try:
        sent, _ = demo_manager.send_command(
            "SET_MANUAL", current_ma=8.0, frequency_hz=35, pulse_width_us=250,
            active_duration_s=0.5, rest_duration_s=0.5,
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
        telemetry = Telemetry(received_at=utc_timestamp(), current_ma=3.2, fsm_state="IDLE", mvc_value_mv=1.2)
        logger.log(telemetry, source="self-test", connection="none", mode="IDLE")
        logger.stop()
        with open(temp_path, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 1 and rows[0]["fsm_state"] == "IDLE"
    finally:
        logger.stop()
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
    checks += 1

    print(f"SELF-TEST PASS ({checks} kelompok pemeriksaan)")
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GUI rehabilitasi FES: persiapan sensor, MVC EMG, Auto, Manual, FSM, monitoring, dan system health")
    parser.add_argument("--port", help="Port serial MCU, misalnya COM6. Tanpa port, aplikasi mulai dalam demo.")
    parser.add_argument("--baud", type=int, default=BAUD_RATE, help=f"Baud rate serial (default: {BAUD_RATE})")
    parser.add_argument("--enable-hardware-control", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="Uji parser/safety/logger lalu keluar tanpa GUI")
    parser.add_argument("--ui-smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ui-flow-test", action="store_true", help=argparse.SUPPRESS)
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
    flow_failures: list[str] = []
    if args.ui_smoke_test:
        root.withdraw()
        root.after(400, app.close)
    elif args.ui_flow_test:
        root.withdraw()

        def flow_start() -> None:
            if app.data_stale or not app.manager.can_control():
                flow_failures.append("Demo control did not become ready")
            app.start_auto()

        def flow_check_running_and_stop() -> None:
            if app.active_mode != "AUTO":
                flow_failures.append(f"Expected AUTO, got {app.active_mode}")
            app.stop_session()

        def flow_check_stopped_and_estop() -> None:
            if app.active_mode != "IDLE" or app.telemetry.output_active is not False:
                flow_failures.append(
                    f"Expected confirmed IDLE/OFF, got {app.active_mode}/{app.telemetry.output_active}",
                )
            app.emergency_stop("ui_flow_test")

        def flow_check_estop_and_close() -> None:
            if not (
                app.active_mode == "E-STOP"
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
