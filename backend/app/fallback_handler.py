"""
Model Fallback Manager — automatic fallback when primary model fails.

Workflow:
1. Try primary model
2. If primary fails (network error, rate limit, API error), try fallback model
3. If fallback also fails, return error with both failure details
4. Update task record with actual model used
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FallbackConfig:
    """Fallback configuration for a model."""
    primary: str
    fallback: str
    max_attempts: int = 2  # primary + 1 fallback


# Fallback mapping: primary → fallback
# If the primary model fails, try these fallbacks in order
FALLBACK_MAP = {
    # Video models
    "seedance-2.0": FallbackConfig(
        primary="seedance-2.0",
        fallback="seedance-2.0-fast",
    ),
    "seedance-2.0-fast": FallbackConfig(
        primary="seedance-2.0-fast",
        fallback="seedance-2.0",
    ),

    # Image models
    "gpt-image-2": FallbackConfig(
        primary="gpt-image-2",
        fallback="nano-banana",
    ),
    "nano-banana": FallbackConfig(
        primary="nano-banana",
        fallback="gpt-image-2",
    ),
}

# Error types that warrant fallback (vs hard failures)
RETRYABLE_ERRORS = [
    "timeout",
    "timed out",
    "超时",
    "排队",
    "queue",
    "rate limit",
    "Too Many Requests",
    "429",
    "503",
    "502",
    "connection refused",
    "connection reset",
    "GPU 资源",
    "try again",
    "请稍后重试",
    "no results",
    "missing media url",
    "invalid result",
    "API key",  # will NOT retry — this is a config issue (overridden by FATAL_ERRORS)
]

# Error types that should NOT fallback
FATAL_ERRORS = [
    "API key",
    "API_KEY",
    "not configured",
    "no adapter",
    "not implemented",
    # Content policy / safety violations
    "guardrails",
    "nudity",
    "sexuality",
    "erotic",
    "violates",
    "content policy",
    "safety system",
    "inappropriate",
    # Billing / credits
    "Credits insufficient",
    "balance isn't enough",
    "余额不足",
]


def is_retryable_error(error_msg: str) -> bool:
    """Check if an error is potentially transient."""
    err_lower = error_msg.lower()
    # If it's a fatal/config error, don't retry
    for fatal in FATAL_ERRORS:
        if fatal.lower() in err_lower:
            return False
    # Check if it matches any retryable pattern
    for pattern in RETRYABLE_ERRORS:
        if pattern.lower() in err_lower:
            return True
    return False


def get_fallback(model_id: str) -> Optional[str]:
    """Get the fallback model for a given primary model."""
    config = FALLBACK_MAP.get(model_id)
    return config.fallback if config else None


async def try_with_fallback(
    primary_func,
    primary_model: str,
    fallback_model: Optional[str] = None,
    **kwargs,
) -> dict:
    """
    Try primary model, fallback if retriable error occurs.

    Args:
        primary_func: The async function to call (adapter method)
        primary_model: Primary model ID
        fallback_model: Explicit fallback model (overrides config map)
        **kwargs: Arguments to pass to primary_func

    Returns:
        dict with 'result', 'model_used', 'used_fallback', 'errors'
    """
    errors = {}

    # Try primary
    try:
        result = await primary_func(**kwargs, _model=primary_model)
        return {
            "result": result,
            "model_used": primary_model,
            "used_fallback": False,
            "errors": {},
        }
    except Exception as e:
        error_msg = str(e)
        errors[primary_model] = error_msg
        logger.warning(f"Primary model {primary_model} failed: {error_msg}")

        # If fallback was specified in config but not explicitly used
        if not fallback_model:
            config = FALLBACK_MAP.get(primary_model)
            if config:
                fallback_model = config.fallback

        if not fallback_model:
            return {
                "result": None,
                "model_used": primary_model,
                "used_fallback": False,
                "errors": errors,
            }

        # Only fallback on retryable errors
        if not is_retryable_error(error_msg):
            return {
                "result": None,
                "model_used": primary_model,
                "used_fallback": False,
                "errors": errors,
            }

        # Try fallback
        logger.info(f"Trying fallback: {fallback_model}")
        try:
            from app.adapters.registry import get_adapter, _load_all_adapters
            _load_all_adapters()

            fallback_adapter = get_adapter(fallback_model)
            if not fallback_adapter:
                errors[fallback_model] = f"No adapter for fallback: {fallback_model}"
                return {
                    "result": None,
                    "model_used": primary_model,
                    "used_fallback": False,
                    "errors": errors,
                }

            result = await fallback_adapter.generate_image(**kwargs) if kwargs.get("_is_image")                 else await fallback_adapter.generate_video(**kwargs)

            return {
                "result": result,
                "model_used": fallback_model,
                "used_fallback": True,
                "errors": errors,
            }
        except Exception as fe:
            errors[fallback_model] = str(fe)
            logger.error(f"Fallback model {fallback_model} also failed: {fe}")
            return {
                "result": None,
                "model_used": primary_model,
                "used_fallback": True,
                "errors": errors,
            }
