"""Crop condition profiles returned by DeepSeek or a safe local knowledge base."""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .deepseek_client import DeepSeekError, deepseek_client
from .prompt_loader import prompt_loader

logger = logging.getLogger(__name__)

# Conservative greenhouse defaults.  They intentionally use the same flat keys
# consumed by the existing specialist agents.
DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "tomato": {
        "stage": "vegetative",
        "temperature_min": 18,
        "temperature_max": 30,
        "humidity_min": 55,
        "humidity_max": 80,
        "light_min": 300,
        "light_max": 1000,
        "co2_min": 400,
        "co2_max": 1200,
        "ph": 6.2,
        "ec": 2.5,
        "soil_moisture_min": 35,
        "soil_moisture_max": 70,
        "water_need": "medium_high",
        "disease_risks": ["gray_mold", "late_blight"],
    },
    "lettuce": {
        "stage": "vegetative",
        "temperature_min": 12,
        "temperature_max": 24,
        "humidity_min": 50,
        "humidity_max": 75,
        "light_min": 150,
        "light_max": 700,
        "co2_min": 350,
        "co2_max": 1000,
        "ph": 6.2,
        "ec": 1.8,
        "soil_moisture_min": 40,
        "soil_moisture_max": 75,
        "water_need": "medium",
        "disease_risks": ["downy_mildew"],
    },
    "strawberry": {
        "stage": "flowering",
        "temperature_min": 14,
        "temperature_max": 26,
        "humidity_min": 55,
        "humidity_max": 75,
        "light_min": 250,
        "light_max": 900,
        "co2_min": 400,
        "co2_max": 1000,
        "ph": 6.0,
        "ec": 1.8,
        "soil_moisture_min": 35,
        "soil_moisture_max": 70,
        "water_need": "medium",
        "disease_risks": ["gray_mold", "powdery_mildew"],
    },
    "cucumber": {
        "stage": "vegetative",
        "temperature_min": 20,
        "temperature_max": 32,
        "humidity_min": 60,
        "humidity_max": 85,
        "light_min": 300,
        "light_max": 1100,
        "co2_min": 450,
        "co2_max": 1200,
        "ph": 6.2,
        "ec": 2.2,
        "soil_moisture_min": 40,
        "soil_moisture_max": 75,
        "water_need": "high",
        "disease_risks": ["powdery_mildew", "downy_mildew"],
    },
    "pepper": {
        "stage": "flowering",
        "temperature_min": 18,
        "temperature_max": 30,
        "humidity_min": 55,
        "humidity_max": 80,
        "light_min": 300,
        "light_max": 1000,
        "co2_min": 400,
        "co2_max": 1100,
        "ph": 6.2,
        "ec": 2.3,
        "soil_moisture_min": 35,
        "soil_moisture_max": 70,
        "water_need": "medium_high",
        "disease_risks": ["anthracnose", "gray_mold"],
    },
}
GENERIC_PROFILE = {
    "stage": "unknown",
    "temperature_min": 18,
    "temperature_max": 30,
    "humidity_min": 50,
    "humidity_max": 80,
    "light_min": 200,
    "light_max": 1200,
    "co2_min": 350,
    "co2_max": 1200,
    "ph": 6.2,
    "ec": 2.0,
    "soil_moisture_min": 30,
    "soil_moisture_max": 70,
    "water_need": "medium",
    "disease_risks": [],
}

PROFILE_KEYS = (
    "temperature_min", "temperature_max", "humidity_min", "humidity_max",
    "light_min", "light_max", "co2_min", "co2_max", "soil_moisture_min",
    "soil_moisture_max", "ph", "ec",
)


def _profile_path() -> Path:
    path = Path(os.getenv("CROP_PROFILE_PATH", Path(__file__).parents[2] / "config" / "crop_profiles.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_saved() -> Dict[str, Dict[str, Any]]:
    try:
        data = json.loads(_profile_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_profile(profile: Dict[str, Any]) -> None:
    profiles = _load_saved()
    crop = profile.get("crop")
    if crop:
        profiles[crop] = profile
    try:
        _profile_path().write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist crop profile: %s", exc)


def normalize_profile(crop: str, profile: Optional[Dict[str, Any]] = None, stage: str = "unknown") -> Dict[str, Any]:
    crop_key = str(crop or "unknown").lower().strip()
    base = dict(DEFAULT_PROFILES.get(crop_key, GENERIC_PROFILE))
    base.update(_load_saved().get(crop_key, {}))
    incoming = dict(profile or {})
    stages = incoming.get('stages') if isinstance(incoming.get('stages'), dict) else {}
    selected_stage = incoming.get('stage')
    if not selected_stage or selected_stage == 'unknown':
        default_stage = DEFAULT_PROFILES.get(crop_key, GENERIC_PROFILE).get('stage', 'unknown')
        selected_stage = stage if stage and stage != 'unknown' else (base.get('stage') if base.get('stage') not in (None, 'unknown') else default_stage)
    stage_values = stages.get(selected_stage) if isinstance(stages.get(selected_stage), dict) else None
    base.update(incoming)
    if stage_values:
        base.update(stage_values)
    # Some models return a per-stage map in a flat field; flatten the selected
    # stage so existing agents can continue using profile.get('<key>').
    for key in PROFILE_KEYS:
        if isinstance(base.get(key), dict):
            values = base[key]
            base[key] = values.get(selected_stage, next(iter(values.values()), 0.0))
    base["crop"] = crop_key
    base["stage"] = selected_stage or "unknown"
    base["updated_at"] = incoming.get("updated_at") or datetime.utcnow().isoformat()
    for key in PROFILE_KEYS:
        if key not in base:
            base[key] = 0.0
        try:
            base[key] = float(base[key])
        except (TypeError, ValueError):
            base[key] = 0.0
    base.setdefault("stages", {})
    base.setdefault("disease_risks", [])
    base.setdefault("profile_source", "local_fallback")
    return base


def analyze_crop_conditions(crop: str, stage: str = "unknown", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ask DeepSeek for a profile, then merge it with safe local defaults."""
    crop_key = str(crop or "unknown").lower().strip()
    fallback = normalize_profile(crop_key, stage=stage)
    if crop_key not in DEFAULT_PROFILES:
        fallback["profile_source"] = "unknown_crop_fallback"
        return fallback
    variables = {
        "crop": crop_key,
        "stage": stage or fallback.get("stage", "unknown"),
        "crop_profile_json": fallback,
        "sensor_data_json": (context or {}).get("sensor_data", (context or {}).get("sensor_data_json", {})),
        "history_json": (context or {}).get("history", (context or {}).get("history_json", {})),
        "weather_json": (context or {}).get("weather", (context or {}).get("weather_json", {})),
    }
    try:
        response = deepseek_client.complete_json(prompt_loader.load("crop_profile", variables))
        profile = normalize_profile(crop_key, response, stage=stage)
        profile["profile_source"] = "deepseek"
    except DeepSeekError:
        profile = fallback
        profile["profile_source"] = "local_fallback"
    _save_profile(profile)
    return profile


async def analyze_crop_conditions_async(crop: str, stage: str = "unknown", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return await asyncio.to_thread(analyze_crop_conditions, crop, stage, context)
