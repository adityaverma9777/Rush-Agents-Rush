"""
HuggingFace Spaces integration for discovering and querying open-source models.
"""
import os
import httpx
from typing import Optional

HF_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_API_TOKEN")

# Unified HF-only list for the frontend (curated small→large)
ALL_MODELS = [
    {"id": "google/flan-t5-small", "name": "FLAN-T5 Small", "size": "small"},
    {"id": "google/flan-t5-base", "name": "FLAN-T5 Base", "size": "small"},
    {"id": "google/flan-t5-large", "name": "FLAN-T5 Large", "size": "medium"},
    {"id": "bigscience/bloom-3b", "name": "BLOOM 3B", "size": "medium"},
    {"id": "EleutherAI/gpt-neo-2.7B", "name": "GPT-Neo 2.7B", "size": "medium"},
    {"id": "mistralai/Mistral-7B-Instruct-v0.2", "name": "Mistral 7B Instruct v0.2", "size": "medium"},
    {"id": "mistralai/Mistral-7B-Instruct-v0.1", "name": "Mistral 7B Instruct v0.1", "size": "medium"},
    {"id": "NousResearch/Nous-Hermes-2-7b", "name": "Nous Hermes 7B", "size": "medium"},
    {"id": "HuggingFaceH4/zephyr-7b", "name": "Zephyr 7B", "size": "medium"},
    {"id": "tiiuae/falcon-7b-instruct", "name": "Falcon 7B Instruct", "size": "medium"},
    {"id": "EleutherAI/gpt-j-6B", "name": "GPT-J 6B", "size": "medium"},
    {"id": "meta-llama/Llama-2-7b-chat-hf", "name": "Llama 2 7B Chat", "size": "large"},
    {"id": "meta-llama/Llama-2-13b-chat-hf", "name": "Llama 2 13B Chat", "size": "large"},
    {"id": "meta-llama/Llama-2-70b-chat-hf", "name": "Llama 2 70B Chat", "size": "xlarge"},
    {"id": "bigscience/bloom-176b", "name": "BLOOM 176B", "size": "xlarge"},
    {"id": "stabilityai/stablelm-tuned-alpha-3b", "name": "StableLM 3B", "size": "medium"},
    {"id": "meta-llama/Llama-3-8b-Instruct", "name": "Llama 3 8B Instruct", "size": "large"},
]


async def get_available_models() -> dict:
    return {"models": ALL_MODELS, "total": len(ALL_MODELS)}


def get_model_display_name(model_id: str) -> str:
    for m in ALL_MODELS:
        if m["id"] == model_id:
            return m["name"]
    return model_id.split("/")[-1].split("-")[0].capitalize()
