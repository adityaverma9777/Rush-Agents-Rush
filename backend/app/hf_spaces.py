"""
Model registry for unified inference API (Groq + HF Spaces).
All models are returned without backend categorization.
"""
import os
from . import groq_client

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

# All available models from both backends (unified list)
ALL_MODELS = [
    # Premium Groq models (unlimited calls, high-quality)
    {
        "id": "mixtral-8x7b-32768",
        "name": "Mixtral 8x7B",
        "description": "High-performance 8x7B mixture of experts model",
    },
    {
        "id": "llama2-70b-4096",
        "name": "Llama 2 70B",
        "description": "Meta's large 70B instruction-tuned model",
    },
    # Open-source HF models (unlimited calls, free)
    {
        "id": "mistralai/Mistral-7B-Instruct-v0.2",
        "name": "Mistral 7B Instruct",
        "description": "Fast, reliable 7B instruction-tuned model",
    },
    {
        "id": "NousResearch/Nous-Hermes-2-Mistral-7B-DPO",
        "name": "Nous Hermes 2",
        "description": "High-quality 7B with DPO training",
    },
    {
        "id": "meta-llama/Llama-2-7b-chat-hf",
        "name": "Llama 2 7B Chat",
        "description": "Meta's Llama 2 7B chat variant",
    },
    {
        "id": "google/flan-t5-large",
        "name": "FLAN-T5 Large",
        "description": "Google's instruction-tuned T5 model",
    },
]


async def get_available_models() -> dict:
    """
    Get unified list of all available models (Groq + HF).
    Frontend receives models without backend categorization.
    """
    return {
        "models": ALL_MODELS,
        "total": len(ALL_MODELS),
    }


def get_model_display_name(model_id: str) -> str:
    """Get clean display name from model ID."""
    for model in ALL_MODELS:
        if model["id"] == model_id:
            return model["name"]
    # Fallback
    return model_id.split("/")[-1].split("-")[0].capitalize()

