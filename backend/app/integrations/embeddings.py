"""Gemini semantic embeddings for explicitly enabled retrieval."""

import http.client
import json
import math

MODEL = "gemini-embedding-001"
DIMENSIONS = 768
MAX_BATCH = 8


class Unavailable(Exception):
    pass


def embed(settings, texts, *, query=False):
    if settings.gemini_api_key is None or not 1 <= len(texts) <= MAX_BATCH:
        raise Unavailable
    model = f"models/{MODEL}"
    payload = {
        "requests": [
            {
                "model": model,
                "content": {"parts": [{"text": item}]},
                "taskType": "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT",
                "outputDimensionality": DIMENSIONS,
            }
            for item in texts
        ]
    }
    connection = http.client.HTTPSConnection("generativelanguage.googleapis.com", timeout=7)
    try:
        connection.request(
            "POST",
            f"/v1beta/{model}:batchEmbedContents",
            body=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": settings.gemini_api_key.get_secret_value(),
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise Unavailable
        raw = response.read(262145)
        if len(raw) > 262144:
            raise Unavailable
        vectors = [item["values"] for item in json.loads(raw)["embeddings"]]
        if len(vectors) != len(texts) or any(
            len(vector) != DIMENSIONS
            or not all(type(value) in (float, int) and math.isfinite(value) for value in vector)
            or not any(vector)
            for vector in vectors
        ):
            raise Unavailable
        return vectors
    except OSError, ValueError, TypeError, LookupError, http.client.HTTPException:
        raise Unavailable from None
    finally:
        connection.close()
