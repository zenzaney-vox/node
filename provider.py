import logging

import httpx

from .config import Settings


logger = logging.getLogger(__name__)


class ModelProviderError(Exception):
    pass


async def generate_reply(
    settings: Settings,
    system_prompt: str,
    history: list[dict[str, str]],
    new_message: str,
) -> str:
    headers = {"Content-Type": "application/json"}
    if settings.model_api_key:
        headers["Authorization"] = f"Bearer {settings.model_api_key}"

    messages = [{"role": "system", "content": system_prompt}, *history]
    messages.append({"role": "user", "content": new_message})
    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.model_timeout_seconds) as client:
            response = await client.post(
                f"{settings.model_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError("The model endpoint returned an empty reply.")
        return content.strip()
    except ModelProviderError:
        raise
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        logger.exception("Model request failed")
        raise ModelProviderError("The model endpoint could not complete the request.") from error
