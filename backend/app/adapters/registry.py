"""
Model adapter registry — lazy-loaded to avoid importing all adapters at startup.
"""
from typing import Optional
from app.adapters.base import BaseModelAdapter

# Lazy registration map: model_id → adapter_class
_ADAPTER_CLASSES: dict[str, type] = {}


def register_adapter(adapter_cls: type[BaseModelAdapter]) -> type[BaseModelAdapter]:
    """Decorator to register an adapter class"""
    adapter = adapter_cls()
    for model_id in adapter_cls.supported_models.__get__(adapter):
        _ADAPTER_CLASSES[model_id] = adapter
    return adapter_cls


def get_adapter(model_id: str) -> Optional[BaseModelAdapter]:
    """Get adapter instance by model ID"""
    return _ADAPTER_CLASSES.get(model_id)


def list_adapters() -> dict[str, BaseModelAdapter]:
    """List all registered adapters"""
    return dict(_ADAPTER_CLASSES)


# Import all adapters to trigger registration
# Order matters: register_adapter must be called when modules are loaded
def _load_all_adapters():
    try:
        from app.adapters import openai_adapter      # noqa: F401
        from app.adapters import seedance_adapter     # noqa: F401
        from app.adapters import kling_adapter        # noqa: F401
        from app.adapters import kie_adapter          # noqa: F401 — KIE.ai unified API
        from app.adapters import replicate_adapter    # noqa: F401 — Replicate API
    except ImportError:
        # Adapter modules may not be created yet — that's OK
        pass

_load_all_adapters()

# Expose as a convenient dict
MODEL_REGISTRY: dict[str, BaseModelAdapter] = _ADAPTER_CLASSES
