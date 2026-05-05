import httpx
from . import groq_client

async def _fetch_model_card(model_name: str) -> str:
    # We'll use a few specific models from Groq, so model card fetching
    # might not always find a "README.md" on HF for these specific names
    # if they are just the Groq IDs. But we'll try.
    url = f"https://huggingface.co/{model_name}/raw/main/README.md"
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            response = await http.get(url)
            if response.status_code == 200:
                return response.text[:2000]
    except Exception:
        pass
    return f"A powerful AI model known as {model_name}."

async def generate_personality(model_name: str) -> dict:
    model_card = await _fetch_model_card(model_name)
    return await groq_client.generate_personality(model_name, model_card)
