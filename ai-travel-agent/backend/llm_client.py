"""
backend/llm_client.py — Centralized LLM Client with Fallback
===========================================================

Provides a uniform interface for calling LLMs from multiple providers
(OpenRouter, Groq) with an automatic fallback mechanism. If the primary
provider fails (e.g., rate limits, timeout), it automatically retries with
the configured secondary provider.
"""

import logging
import requests
import time
from typing import Optional, Dict, Any

from backend.config import (
    OPENROUTER_API_KEY,
    GROQ_API_KEY,
    MODEL_PROVIDER,
    MODEL_NAME
)

logger = logging.getLogger(__name__)

# Constants for defaults
PROVIDER_DEFAULTS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.1-8b-instant",
        "api_key": GROQ_API_KEY,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "arcee-ai/trinity-large-preview:free",
        "api_key": OPENROUTER_API_KEY,
    },
}

class LLMClient:
    """
    Handles LLM requests with automatic provider fallback.
    """

    @staticmethod
    def call_llm(
        prompt: str,
        system_prompt: str,
        temperature: float = 0.5,
        model_override: Optional[str] = None,
        max_retries: int = 1
    ) -> str:
        """
        Calls the LLM provider. If it fails, falls back to the other provider.
        
        Args:
            prompt: The user prompt.
            system_prompt: The system instruction.
            temperature: LLM temperature setting.
            model_override: Specific model to use (for the primary provider).
            max_retries: Not used for provider fallback (which is always 1 try per provider).
            
        Returns:
            The raw text response from the LLM.
            
        Raises:
            RuntimeError: If all configured providers fail.
        """
        primary = MODEL_PROVIDER
        secondary = "groq" if primary == "openrouter" else "openrouter"
        
        providers_to_try = [primary, secondary]
        errors = []

        for provider in providers_to_try:
            try:
                logger.info(f"LLMClient: Attempting call with {provider}...")
                return LLMClient._execute_call(
                    provider=provider,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    model_override=model_override
                )
            except Exception as e:
                logger.warning(f"LLMClient: Provider {provider} failed: {str(e)}")
                errors.append(f"{provider}: {str(e)}")
                # If we have more providers to try, wait briefly before switching
                if provider != providers_to_try[-1]:
                    time.sleep(1)
                continue

        # If we reach here, all providers failed
        error_msg = " | ".join(errors)
        raise RuntimeError(f"All LLM providers failed. Errors: {error_msg}")

    @staticmethod
    def _execute_call(
        provider: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        model_override: Optional[str]
    ) -> str:
        """Internal helper to perform the actual HTTP request."""
        config = PROVIDER_DEFAULTS.get(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")

        api_key = config["api_key"]
        if not api_key:
            raise RuntimeError(f"API key missing for provider: {provider}")

        # Use model_override only if it's the primary provider or if it looks compatible
        # For OpenRouter, we stick to free models. For Groq, we stick to llama-3.1-8b-instant.
        model = config["model"]
        if model_override and provider == MODEL_PROVIDER:
             model = model_override

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://ai-travel-agent"
            headers["X-Title"] = "AI Travel Agent"

        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        response = requests.post(config["base_url"], headers=headers, json=payload, timeout=60)
        
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected response format from {provider}")
