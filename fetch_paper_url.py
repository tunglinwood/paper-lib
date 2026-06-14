#!/usr/bin/env python3
"""
Fetch paper metadata from a URL using:
1. Crawl4AI endpoint (174.1.21.1:11235) to get markdown
2. Local multimodal LLM (localhost:8000/v1) to extract structured metadata
"""
import argparse
import json
import os
import sys

import requests

CRAWL4AI_BASE = os.getenv("CRAWL4AI_BASE_URL", "http://174.1.21.1:11235")
LLM_BASE = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4.5-air")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")

EXTRACTION_PROMPT = """You are a research paper metadata extractor.
Given the markdown content of a paper webpage, extract the following fields and return them as a single JSON object.

Required JSON schema:
{
  "title": "string or null",
  "authors": ["list of strings"],
  "year": "integer or null",
  "venue": "string or null",
  "doi": "string or null",
  "abstract": "string or null"
}

Rules:
- Return ONLY the JSON object. No markdown code blocks, no extra text.
- If a field is not found, use null (not empty string).
- For authors, extract full names as a list of strings.
- For year, extract the 4-digit publication year.
- For venue, extract the journal or conference name.
- For DOI, extract just the DOI string (e.g., "10.1234/example").
- For abstract, extract the paper abstract/summary if present.

Output ONLY valid JSON. Do not wrap in markdown fences. No explanations before or after.
"""


def fetch_markdown(url: str) -> str:
    """Use Crawl4AI /md endpoint to fetch cleaned markdown from a URL."""
    resp = requests.post(
        f"{CRAWL4AI_BASE}/md",
        json={"url": url},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    markdown = data.get("markdown", "").strip()
    if not markdown:
        raise ValueError("Crawl4AI returned empty markdown")
    return markdown


def extract_metadata(markdown: str) -> dict:
    """Use local LLM to extract structured paper metadata from markdown."""
    resp = requests.post(
        f"{LLM_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n---\n\nWebpage markdown:\n{markdown[:12000]}"},
            ],
            "temperature": 0.1,
            "max_tokens": 8192,
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content")

    # Some reasoning models return content=null with reasoning_content
    if content is None and msg.get("reasoning_content"):
        # Try to find JSON inside reasoning content
        content = msg["reasoning_content"]

    if not content:
        raise ValueError("LLM returned empty content")

    # Clean up accidental markdown code fences
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    # Try to extract the first JSON object if there's surrounding text
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start:end + 1])
        raise


def main():
    parser = argparse.ArgumentParser(description="Fetch paper metadata from a URL")
    parser.add_argument("url", help="Paper webpage URL (e.g., arXiv, PubMed, journal page)")
    parser.add_argument("--raw", action="store_true", help="Also output the raw markdown")
    args = parser.parse_args()

    print(f"[1/3] Crawling: {args.url}", file=sys.stderr)
    markdown = fetch_markdown(args.url)
    print(f"      Markdown length: {len(markdown)} chars", file=sys.stderr)

    print(f"[2/3] Extracting metadata via LLM ({LLM_MODEL})...", file=sys.stderr)
    metadata = extract_metadata(markdown)

    print(f"[3/3] Done.", file=sys.stderr)
    result = {
        "url": args.url,
        "metadata": metadata,
    }
    if args.raw:
        result["markdown"] = markdown

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
