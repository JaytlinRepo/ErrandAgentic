# tests/test_bedrock.py
import boto3
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Project .env lives in errand-sequencer/ (this file is in tests/).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def test_bedrock():
    client = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1"
    )

    # Test with Llama 3
    prompt = """You are an errand sequencing assistant. 
    I need to go to the post office, Costco, and CVS pharmacy. 
    What order should I do these errands and why?"""

    body = json.dumps({
        "prompt": prompt,
        "max_gen_len": 512,
        "temperature": 0.7
    })

    response = client.invoke_model(
        modelId="meta.llama3-8b-instruct-v1:0",
        body=body
    )

    result = json.loads(response["body"].read())
    print("Bedrock Response:")
    print(result["generation"])

if __name__ == "__main__":
    test_bedrock()