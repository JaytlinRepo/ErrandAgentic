"""AWS Bedrock text generation via InvokeModel (Llama and similar)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv

from configs.ml_tracker import get_mlflow_tracker

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)


class BedrockLLM:
    """Thin wrapper around bedrock-runtime invoke_model for single-string prompts."""

    def __init__(
        self,
        *,
        region_name: str | None = None,
        model_id: str | None = None,
    ) -> None:
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0"
        )
        self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    def query(self, prompt: str, max_tokens: int = 512) -> str:
        body = json.dumps(
            {
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": 0.7,
            }
        )
        tracker = get_mlflow_tracker()
        start = time.perf_counter()
        try:
            response = self.client.invoke_model(modelId=self.model_id, body=body)
            result = json.loads(response["body"].read())
            text = result.get("generation") or ""
            latency_ms = (time.perf_counter() - start) * 1000.0
            tracker.log_model_call(
                model_type="invoke_model",
                model_id=self.model_id,
                prompt=prompt,
                response=text,
                input_tokens=int(result.get("prompt_token_count") or 0),
                output_tokens=int(result.get("generation_token_count") or 0),
                latency_ms=latency_ms,
            )
            return text
        except Exception as e:
            print(f"Bedrock error: {e}")
            return "I encountered an error processing your request."
