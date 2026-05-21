from typing import Optional, Tuple, List, Dict, Any
import time
import os
import io
import logging
import numpy as np
from PIL import Image
from fastapi import HTTPException
import tensorflow as tf

logger = logging.getLogger(__name__)

# ── Class labels ──
# UPDATE this list confirms exact label order for model_2.tflite.
# Order MUST match the training label order (index 0 = first class, etc).
CLASS_NAMES: List[str] = [
    "class_0",
    "class_1",
    "class_2",
    "class_3",
    "class_4",
    "class_5",
    "class_6",
]

# Minimum confidence to accept a prediction. Below this → "tidak_dikenali"
CONFIDENCE_THRESHOLD: float = 0.40

# Input size expected by MobileNetV2
INPUT_SIZE: int = 224


def _preprocess(image_bytes: bytes) -> np.ndarray:
    """
    Convert raw image bytes to the float32 tensor expected by MobileNetV2.
    MobileNetV2 standard: resize to INPUT_SIZE, normalize pixels to [-1, 1].
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((INPUT_SIZE, INPUT_SIZE))
    arr = np.array(image, dtype=np.float32)
    arr = (arr / 127.5) - 1.0          # [-1, 1] normalization
    arr = np.expand_dims(arr, axis=0)  # [1, 224, 224, 3]
    return arr


class InferenceService:
    def __init__(self):
        self.interpreter: Optional[tf.lite.Interpreter] = None

    async def load_model(self):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        model_path = os.path.join(base_dir, "model_2.tflite")

        if not os.path.exists(model_path):
            logger.error(f"Model tidak ditemukan di: {model_path}")
            raise HTTPException(
                status_code=500,
                detail="model_2.tflite tidak ditemukan. Pastikan file ada di root folder backend.",
            )

        try:
            self.interpreter = tf.lite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self._input_details = self.interpreter.get_input_details()
            self._output_details = self.interpreter.get_output_details()
            logger.info(f"Model TFLite berhasil dimuat: {model_path}")
            logger.info(f"Input shape: {self._input_details[0]['shape']}")
            logger.info(f"Output shape: {self._output_details[0]['shape']}")
        except Exception as e:
            logger.error(f"Gagal memuat model TFLite: {e}")
            raise HTTPException(status_code=500, detail=f"Gagal memuat model: {e}")

    async def predict(
        self, image_bytes: bytes
    ) -> Tuple[str, float, int, List[Dict[str, Any]]]:
        if self.interpreter is None:
            raise HTTPException(status_code=500, detail="Model belum dimuat")

        try:
            start_time = time.time()

            try:
                tensor = _preprocess(image_bytes)
            except Exception:
                raise HTTPException(
                    status_code=400, detail="File bukan gambar yang valid"
                )

            self.interpreter.set_tensor(self._input_details[0]["index"], tensor)
            self.interpreter.invoke()
            output = self.interpreter.get_tensor(self._output_details[0]["index"])

            # output shape: [1, 7] — softmax scores per class
            scores: np.ndarray = output[0]
            class_id: int = int(np.argmax(scores))
            confidence: float = float(scores[class_id])

            if confidence < CONFIDENCE_THRESHOLD:
                label = "tidak_dikenali"
            else:
                label = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else f"class_{class_id}"

            processing_time = int((time.time() - start_time) * 1000)

            return label, confidence, processing_time, []

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise HTTPException(
                status_code=500, detail=f"Gagal melakukan inferensi: {e}"
            )

    def get_model_info(self) -> dict:
        return {
            "status": "loaded" if self.interpreter else "not_loaded",
            "model": "model_2.tflite (MobileNetV2)",
            "classes": len(CLASS_NAMES),
            "input_size": INPUT_SIZE,
        }


inference_service = InferenceService()