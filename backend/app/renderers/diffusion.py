from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image

from app.domain.contracts import Keypoint
from app.renderers.fast import SkeletonRenderer


class DiffusionAvatarRenderer:
    """Optional notebook-derived ControlNet renderer; never imported on the CPU path."""

    id = "diffusion"

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._pipe = None

    def available(self) -> tuple[bool, str | None]:
        if not self.enabled:
            return False, "Enable POSEAPP_ENABLE_DIFFUSION=1 on a CUDA machine."
        try:
            import torch
            if not torch.cuda.is_available():
                return False, "CUDA is not available on this computer."
        except ImportError:
            return False, "The optional diffusion dependencies are not installed."
        return True, None

    def _load(self) -> None:
        if self._pipe is not None:
            return
        import torch
        from diffusers import ControlNetModel, DPMSolverMultistepScheduler, StableDiffusionControlNetPipeline

        controlnet = ControlNetModel.from_pretrained("lllyasviel/control_v11p_sd15_openpose", torch_dtype=torch.float16)
        pipe = StableDiffusionControlNetPipeline.from_pretrained(
            "Lykon/dreamshaper-8", controlnet=controlnet, torch_dtype=torch.float16,
            safety_checker=None, requires_safety_checker=False,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, algorithm_type="dpmsolver++")
        self._pipe = pipe.to("cuda")

    def render(self, image: np.ndarray, keypoints: list[Keypoint], edges: list[tuple[str, str]]) -> np.ndarray:
        available, reason = self.available()
        if not available:
            raise RuntimeError(reason)
        self._load()
        pose = SkeletonRenderer().render(np.zeros_like(image), keypoints, edges)
        prompt = os.getenv("POSEAPP_DIFFUSION_PROMPT", "full body futuristic hero, cinematic lighting, detailed costume, masterpiece")
        result = self._pipe(
            prompt=prompt,
            negative_prompt="blurry, deformed, extra limbs, bad anatomy, watermark, text",
            image=Image.fromarray(cv2.cvtColor(pose, cv2.COLOR_BGR2RGB)).resize((512, 512)),
            num_inference_steps=28, guidance_scale=7.0, controlnet_conditioning_scale=1.2,
        ).images[0]
        rendered = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
        return cv2.resize(rendered, (image.shape[1], image.shape[0]))

