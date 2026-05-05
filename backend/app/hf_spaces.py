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
    # Open-source HF models - Fast & Reliable
    {
        "id": "mistralai/Mistral-7B-Instruct-v0.2",
        "name": "Mistral 7B Instruct v0.2",
        "description": "Fast, reliable 7B instruction-tuned model",
    },
    {
        "id": "mistralai/Mistral-7B-Instruct-v0.1",
        "name": "Mistral 7B Instruct v0.1",
        "description": "Original Mistral 7B instruct version",
    },
    {
        "id": "HuggingFaceH4/zephyr-7b-beta",
        "name": "Zephyr 7B Beta",
        "description": "HF's high-quality 7B chat model",
    },
    {
        "id": "HuggingFaceH4/zephyr-7b",
        "name": "Zephyr 7B",
        "description": "Fast, well-aligned 7B model",
    },
    # Open-source HF models - Quality-Focused
    {
        "id": "NousResearch/Nous-Hermes-2-Mistral-7B-DPO",
        "name": "Nous Hermes 2 Mistral",
        "description": "High-quality 7B with DPO training",
    },
    {
        "id": "NousResearch/Nous-Hermes-2-7b",
        "name": "Nous Hermes 2 7B",
        "description": "Quality-focused 7B model",
    },
    # Open-source HF models - Meta's Llama
    {
        "id": "meta-llama/Llama-2-7b-chat-hf",
        "name": "Llama 2 7B Chat",
        "description": "Meta's Llama 2 7B chat variant",
    },
    {
        "id": "meta-llama/Llama-2-13b-chat-hf",
        "name": "Llama 2 13B Chat",
        "description": "Meta's Llama 2 13B chat variant",
    },
    {
        "id": "meta-llama/Llama-3-8b-Instruct",
        "name": "Llama 3 8B Instruct",
        "description": "Meta's latest Llama 3 8B model",
    },
    # Open-source HF models - Google & Others
    {
        "id": "google/flan-t5-large",
        "name": "FLAN-T5 Large",
        "description": "Google's instruction-tuned T5 model",
    },
    {
        "id": "google/flan-t5-base",
        "name": "FLAN-T5 Base",
        "description": "Google's FLAN-T5 base variant",
    },
    {
        "id": "tiiuae/falcon-7b-instruct",
        "name": "Falcon 7B Instruct",
        "description": "TII's Falcon 7B instruction-tuned",
    },
    {
        "id": "EleutherAI/gpt-j-6B",
        "name": "GPT-J 6B",
        "description": "EleutherAI's 6B GPT model",
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

