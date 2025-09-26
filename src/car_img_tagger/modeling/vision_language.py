"""Utility classes for loading and scoring vision-language models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import torch
from PIL import Image

try:
    import clip  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    clip = None

try:
    from transformers import AutoModel, AutoProcessor
except ImportError:  # pragma: no cover - optional dependency
    AutoModel = None
    AutoProcessor = None


@dataclass
class VisionLanguageConfig:
    provider: str = "clip"
    model_name: str = "ViT-B/32"
    revision: str | None = None
    dtype: str = "fp16"
    normalize: bool = True


class VisionLanguageModel:
    """Wrapper that abstracts CLIP/SigLIP style backbones."""

    def __init__(self, config: VisionLanguageConfig, device: str = "cpu") -> None:
        self.config = config
        self.device = torch.device(device)
        self.provider = config.provider.lower()

        if self.provider == "siglip":
            if AutoModel is None or AutoProcessor is None:
                raise ImportError("transformers is required for SigLIP support")
            torch_dtype = _resolve_dtype(config.dtype)
            self.processor = AutoProcessor.from_pretrained(
                config.model_name,
                revision=config.revision,
            )
            self.model = AutoModel.from_pretrained(
                config.model_name,
                revision=config.revision,
                torch_dtype=torch_dtype,
            )
            self.model.to(self.device)
            self.model.eval()
            self.preprocess = None
        else:
            if clip is None:
                raise ImportError("clip-by-openai is required for CLIP support")
            self.model, self.preprocess = clip.load(config.model_name, device=self.device)
            self.model.eval()
            self.processor = None

    @torch.inference_mode()
    def image_features(self, image: Image.Image) -> torch.Tensor:
        if self.provider == "siglip":
            assert self.processor is not None
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            outputs = self.model.get_image_features(**inputs)
        else:
            assert self.preprocess is not None
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            outputs = self.model.encode_image(image_tensor)
        return torch.nn.functional.normalize(outputs, dim=-1) if self.config.normalize else outputs

    @torch.inference_mode()
    def text_features(self, prompts: Iterable[str]) -> torch.Tensor:
        prompt_list = list(prompts)
        if self.provider == "siglip":
            assert self.processor is not None
            inputs = self.processor(text=prompt_list, padding=True, return_tensors="pt").to(self.device)
            outputs = self.model.get_text_features(**inputs)
        else:
            assert clip is not None
            text_tokens = clip.tokenize(prompt_list).to(self.device)
            outputs = self.model.encode_text(text_tokens)
        normalized = torch.nn.functional.normalize(outputs, dim=-1) if self.config.normalize else outputs
        return normalized, prompt_list

    @torch.inference_mode()
    def predict_probabilities(self, image: Image.Image, prompts: List[str]) -> torch.Tensor:
        image_embeds = self.image_features(image)
        text_embeds, _ = self.text_features(prompts)
        logits = (image_embeds @ text_embeds.T) * 100.0
        return torch.nn.functional.softmax(logits, dim=-1).squeeze(0)


def _resolve_dtype(name: str) -> torch.dtype:
    name = (name or "").lower()
    if name == "fp32":
        return torch.float32
    if name == "bf16":
        return torch.bfloat16
    return torch.float16
