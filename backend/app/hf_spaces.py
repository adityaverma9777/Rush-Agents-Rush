import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

HF_API_TOKEN = (os.environ.get("HF_API_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN") or "").strip()
ROUTER_MODELS_URL = "https://router.huggingface.co/v1/models"

PREFERRED_MODELS = [
    {"id": "meta-llama/Llama-3.1-8B-Instruct", "name": "Llama 3.1 8B Instruct", "size": "medium", "description": "Fast general-purpose instruct model"},
    {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 7B Instruct", "size": "medium", "description": "Reliable JSON-following instruction model"},
    {"id": "meta-llama/Meta-Llama-3-8B-Instruct", "name": "Meta Llama 3 8B Instruct", "size": "medium", "description": "Strong general chat behavior"},
    {"id": "google/gemma-3n-E4B-it", "name": "Gemma 3n E4B", "size": "small", "description": "Lightweight instruction-tuned Gemma model"},
    {"id": "Sao10K/L3-8B-Stheno-v3.2", "name": "L3 8B Stheno v3.2", "size": "medium", "description": "Creative 8B chat model"},
    {"id": "XiaomiMiMo/MiMo-V2-Flash", "name": "MiMo V2 Flash", "size": "medium", "description": "Fast flash-tier chat model"},
    {"id": "google/gemma-4-26B-A4B-it", "name": "Gemma 4 26B A4B", "size": "large", "description": "Higher-capacity Gemma instruct model"},
    {"id": "google/gemma-4-31B-it", "name": "Gemma 4 31B", "size": "large", "description": "Large Gemma chat model"},
    {"id": "Qwen/Qwen3.5-35B-A3B", "name": "Qwen 3.5 35B A3B", "size": "large", "description": "Large Qwen instruction model"},
    {"id": "google/gemma-3-27b-it", "name": "Gemma 3 27B", "size": "large", "description": "Large Gemma 3 instruct model"},
    {"id": "moonshotai/Kimi-K2.5", "name": "Kimi K2.5", "size": "large", "description": "Large reasoning-oriented chat model"},
    {"id": "Qwen/Qwen3-Coder-30B-A3B-Instruct", "name": "Qwen 3 Coder 30B", "size": "large", "description": "Coder-tuned instruction model"},
    {"id": "meta-llama/Llama-3.3-70B-Instruct", "name": "Llama 3.3 70B Instruct", "size": "xl", "description": "Large instruction-following flagship model"},
]

_CACHE = {"expires_at": 0.0, "ids": None}


def _headers() -> dict[str, str]:
    if not HF_API_TOKEN:
        return {}
    return {"Authorization": f"Bearer {HF_API_TOKEN}"}


def _extract_router_models(payload) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    return []


async def _fetch_router_model_ids() -> set[str] | None:
    now = time.monotonic()
    cached_ids = _CACHE["ids"]
    if isinstance(cached_ids, set) and _CACHE["expires_at"] > now:
        return cached_ids

    if not HF_API_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(ROUTER_MODELS_URL, headers=_headers())
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None

    models = _extract_router_models(payload)
    ids = {item["id"] for item in models if isinstance(item.get("id"), str)}
    _CACHE["ids"] = ids
    _CACHE["expires_at"] = now + 300
    return ids


def get_supported_model_ids() -> set[str]:
    return {model["id"] for model in PREFERRED_MODELS}


def is_supported_model(model_id: str) -> bool:
    return model_id in get_supported_model_ids()


def get_default_model_id() -> str:
    return PREFERRED_MODELS[0]["id"]


async def get_available_models() -> dict:
    live_ids = await _fetch_router_model_ids()
    if live_ids:
        models = [model for model in PREFERRED_MODELS if model["id"] in live_ids]
    else:
        models = list(PREFERRED_MODELS)
    return {"models": models, "total": len(models)}


def get_model_display_name(model_id: str) -> str:
    for model in PREFERRED_MODELS:
        if model["id"] == model_id:
            return model["name"]
    return model_id.split("/")[-1].split("-")[0].capitalize()
