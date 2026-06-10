import os
from typing import Any, Dict, Optional

from mellea_skills_compiler.enums import InferenceEngineType, InferenceModel


OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")

INFERENCE_ENGINE_CACHE = {}


class InferenceService:

    def __init__(self, inference_engine_type: Optional[InferenceEngineType] = None):
        self.inference_engine_type = (
            inference_engine_type
            if inference_engine_type
            else InferenceEngineType.OLLAMA
        )

    @property
    def inference_engine_class(self):
        from ai_atlas_nexus.blocks.inference import OllamaInferenceEngine

        if self.inference_engine_type == InferenceEngineType.OLLAMA:
            return OllamaInferenceEngine
        else:
            raise ValueError(f"Invalid inference engine: {self.inference_engine_type}")

    @property
    def credentials(self) -> Dict[str, Any]:
        if self.inference_engine_type == InferenceEngineType.OLLAMA:
            return {"api_url": OLLAMA_API_URL}
        else:
            raise ValueError(f"Invalid inference engine: {self.inference_engine_type}")

    @property
    def risk_model(self) -> str:
        return InferenceModel[f"{self.inference_engine_type.name}_RISK_MODEL"]

    @property
    def guardian_model(self) -> str:
        return InferenceModel[f"{self.inference_engine_type.name}_GUARDIAN_MODEL"]

    def risk(
        self,
        model: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        return self._cache_and_get_inference_engine(
            model or self.risk_model, parameters, **kwargs
        )

    def guardian(
        self,
        model: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        return self._cache_and_get_inference_engine(
            model or self.guardian_model, parameters, **kwargs
        )

    def _cache_and_get_inference_engine(
        self,
        model_name_or_path: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        cache_key = (self.inference_engine_type, model_name_or_path)
        if cache_key not in INFERENCE_ENGINE_CACHE:
            INFERENCE_ENGINE_CACHE[cache_key] = self.inference_engine_class(
                model_name_or_path=model_name_or_path,
                credentials=self.credentials,
                parameters=parameters or {},
                **kwargs,
            )
        return INFERENCE_ENGINE_CACHE[cache_key]
