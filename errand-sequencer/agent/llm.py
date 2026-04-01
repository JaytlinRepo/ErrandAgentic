"""AWS Bedrock text generation via InvokeModel (Llama and similar)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

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
        try:
            response = self.client.invoke_model(modelId=self.model_id, body=body)
            result = json.loads(response["body"].read())
            return result.get("generation") or ""
        except Exception as e:
            print(f"Bedrock error: {e}")
            return "I encountered an error processing your request."
