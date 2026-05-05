"""
HuggingFace Spaces integration for discovering and querying open-source models.
"""
import os
import httpx
from typing import Optional

HF_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_API_TOKEN")

# Unified HF-only list with models verified to work on HF Inference API
ALL_MODELS = [
    {"id": "mistralai/Mistral-7B-Instruct-v0.2", "name": "Mistral 7B v0.2", "size": "medium"},
    {"id": "mistralai/Mistral-7B-Instruct-v0.1", "name": "Mistral 7B v0.1", "size": "medium"},
    {"id": "NousResearch/Nous-Hermes-2-7b", "name": "Nous Hermes 7B", "size": "medium"},
    {"id": "HuggingFaceH4/zephyr-7b-beta", "name": "Zephyr 7B Beta", "size": "medium"},
    {"id": "tiiuae/falcon-7b-instruct", "name": "Falcon 7B Instruct", "size": "medium"},
    {"id": "meta-llama/Llama-2-7b-chat-hf", "name": "Llama 2 7B Chat", "size": "large"},
    {"id": "meta-llama/Llama-2-13b-chat-hf", "name": "Llama 2 13B Chat", "size": "large"},
    {"id": "stabilityai/stablelm-tuned-alpha-3b", "name": "StableLM 3B", "size": "medium"},
    {"id": "WizardLM/WizardLM-7B-V1.0", "name": "WizardLM 7B", "size": "medium"},
]


async def get_available_models() -> dict:
    return {"models": ALL_MODELS, "total": len(ALL_MODELS)}


def get_model_display_name(model_id: str) -> str:
    for m in ALL_MODELS:
        if m["id"] == model_id:
            return m["name"]
    return model_id.split("/")[-1].split("-")[0].capitalize()
