from __future__ import annotations

import base64

import cv2
import numpy as np


class OpenCVMediaProcessor:
    def decode_image(self, payload: bytes) -> np.ndarray:
        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("The image could not be decoded. Use JPEG, PNG, or WebP.")
        return image

    def encode_data_url(self, image: np.ndarray, quality: int = 88) -> str:
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise RuntimeError("Could not encode result image")
        return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")

    def decode_data_url(self, data_url: str) -> np.ndarray:
        return self.decode_image(base64.b64decode(data_url.split(",", 1)[1]))

