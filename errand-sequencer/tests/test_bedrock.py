"""Manual Bedrock smoke tests. Run from errand-sequencer: `python tests/test_bedrock.py`"""

from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)

_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
_LLAMA_MODEL = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
_HAIKU_MODEL = os.getenv(
    "BEDROCK_AGENT_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)


def test_bedrock() -> None:
    """Test 1 — Llama 3 simple chat (InvokeModel)."""
    client = boto3.client("bedrock-runtime", region_name=_REGION)

    prompt = """You are an errand sequencing assistant.
I need to go to the post office, Costco, and CVS pharmacy.
What order should I do these errands and why?"""

    body = json.dumps(
        {
            "prompt": prompt,
            "max_gen_len": 512,
            "temperature": 0.7,
        }
    )

    response = client.invoke_model(modelId=_LLAMA_MODEL, body=body)
    result = json.loads(response["body"].read())
    print("Bedrock (Llama) Response:")
    print(result.get("generation", ""))


def test_haiku() -> None:
    """Test 2 — Claude Haiku (Converse API, no tools)."""
    client = boto3.client("bedrock-runtime", region_name=_REGION)

    response = client.converse(
        modelId=_HAIKU_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": "I need to go to Costco and the post office. Which should I do first?"
                    }
                ],
            }
        ],
    )

    print("Haiku Response:")
    print(response["output"]["message"]["content"][0]["text"])


if __name__ == "__main__":
    import sys

    arg = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if arg in ("all", "llama", "1"):
        test_bedrock()
    if arg in ("all", "haiku", "2"):
        if arg == "all":
            print()
        test_haiku()
    if arg not in ("all", "llama", "1", "haiku", "2"):
        print("Usage: python tests/test_bedrock.py [all|llama|haiku]", file=sys.stderr)
        sys.exit(2)
