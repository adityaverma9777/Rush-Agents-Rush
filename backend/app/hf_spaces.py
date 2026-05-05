"""
HuggingFace Spaces integration for discovering and querying open-source models.
"""
import os
import httpx
from typing import Optional

HF_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")

# Curated list of verified open-source models on HF Spaces that work reliably
KNOWN_SPACES_MODELS = [
    {
        "id": "tiiuae/Falcon-7B",
        "name": "Falcon-7B",
        "space_url": "https://huggingface.co/spaces/tiiuae/falcon-chat",
        "description": "7B parameter open model",
    },
    {
        "id": "meta-llama/Llama-2-7b",
        "name": "Llama-2-7B",
        "space_url": "https://huggingface.co/spaces/meta-llama/Llama-2-7b-chat",
        "description": "Meta's 7B model",
    },
    {
        "id": "mistralai/Mistral-7B",
        "name": "Mistral-7B",
        "space_url": "https://huggingface.co/spaces/mistralai/Mistral-7B-Instruct-v0.1",
        "description": "Mistral's 7B model",
    },
    {
        "id": "HuggingFaceH4/zephyr-7b",
        "name": "Zephyr-7B",
        "space_url": "https://huggingface.co/spaces/HuggingFaceH4/zephyr-7b-beta",
        "description": "Zephyr 7B fine-tuned model",
    },
    {
        "id": "teknium/OpenHermes-2.5-Mistral-7B",
        "name": "OpenHermes-7B",
        "space_url": "https://huggingface.co/spaces/teknium/OpenHermes-2.5-Mistral-7B",
        "description": "OpenHermes instruction-tuned 7B",
    },
]

# Groq models (built-in)
GROQ_MODELS = [
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "backend": "groq"},
    {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B", "backend": "groq"},
    {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "backend": "groq"},
    {"id": "gemma-7b-it", "name": "Gemma 7B", "backend": "groq"},
]


async def get_available_models() -> dict:
    """
    Get list of available models from Groq and HF Spaces.
    Returns both for frontend model selector.
    """
    return {
        "groq_models": GROQ_MODELS,
        "hf_spaces_models": KNOWN_SPACES_MODELS,
        "total": len(GROQ_MODELS) + len(KNOWN_SPACES_MODELS),
    }


async def query_hf_space_model(model_id: str, prompt: str) -> Optional[str]:
    """
    Query a model on HuggingFace Spaces.
    This is a fallback if we want to use HF spaces directly.
    Note: HF spaces may have rate limits and require authentication.
    """
    if not HF_API_TOKEN:
        return None

    # Try to find the space URL for this model
    space = next((m for m in KNOWN_SPACES_MODELS if m["id"] == model_id), None)
    if not space:
        return None

    try:
        # This would hit the HF inference API
        # For now, we focus on Groq which is more reliable
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
            response = await client.post(
                "https://api-inference.huggingface.co/models/" + model_id,
                json={"inputs": prompt},
                headers=headers,
            )
            if response.status_code == 200:
                result = response.json()
                # Extract generated text from response
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "")
    except Exception as e:
        print(f"Error querying HF space {model_id}: {e}")

    return None


def get_model_display_name(model_id: str) -> str:
    """Get a clean display name from model ID."""
    # Try to find in known models
    for model in GROQ_MODELS + KNOWN_SPACES_MODELS:
        if model["id"] == model_id:
            return model["name"]

    # Fallback: clean up the ID
    return model_id.split("/")[-1].split("-")[0].capitalize()
