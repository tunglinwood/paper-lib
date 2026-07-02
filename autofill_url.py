#!/usr/bin/env python3
"""
Fetch paper metadata from a URL using local crawl4ai:
- For direct PDF URLs: download and extract text via NaivePDFProcessorStrategy
- For regular URLs: crawl with crawl4ai and extract page text
- Use local LLM (localhost:8000/v1, glm-4.5-air) to extract structured metadata
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import requests
from crawl4ai.processors.pdf.processor import NaivePDFProcessorStrategy

LLM_BASE = os.getenv("LLM_BASE_URL", "http://223.108.218.44:54001/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "hua-llm")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-v-FMlAezr7Y9GjHKwdjdWA")

EXTRACTION_PROMPT = """You are a research paper metadata extractor.
Given the text extracted from a research paper, extract the following fields and return them as a single JSON object.

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


def is_pdf_url(url: str) -> bool:
    """Check if URL points to a PDF (by extension or content-type)."""
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".pdf"):
        return True
    # Try HEAD request to check content-type
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "").lower()
        if "application/pdf" in ct:
            return True
    except Exception:
        pass
    return False


def download_pdf(url: str) -> str:
    """Download PDF to a temp file and return the path."""
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    for chunk in resp.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name


def extract_pdf_text(pdf_path: str) -> str:
    """Use crawl4ai NaivePDFProcessorStrategy to extract text from PDF."""
    strategy = NaivePDFProcessorStrategy(extract_images=False, save_images_locally=False)
    result = strategy.process_batch(Path(pdf_path))
    texts = []
    for page in result.pages[:3]:
        raw = page.raw_text.strip()
        if raw:
            texts.append(raw)
    return "\n\n---PAGE BREAK---\n\n".join(texts)


def crawl_url(url: str) -> str:
    """Fetch page content via remote Crawl4AI service (local AsyncWebCrawler requires Playwright)."""
    crawl4ai_base = os.getenv("CRAWL4AI_BASE_URL", "http://174.1.21.1:11235")
    resp = requests.post(
        f"{crawl4ai_base}/md",
        json={"url": url},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("markdown", "").strip()


def extract_metadata(text: str) -> dict:
    """Use local LLM to extract structured metadata from text."""
    resp = requests.post(
        f"{LLM_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n---\n\nExtracted text:\n{text[:12000]}"},
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
    if content is None and msg.get("reasoning_content"):
        content = msg["reasoning_content"]
    if not content:
        raise ValueError("LLM returned empty content")
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start:end + 1])
        raise


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "URL required"}), file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    pdf_tmp = None

    try:
        if is_pdf_url(url):
            print(f"[1/3] URL is a PDF, downloading...", file=sys.stderr)
            pdf_tmp = download_pdf(url)
            print(f"[2/3] Extracting text from PDF...", file=sys.stderr)
            text = extract_pdf_text(pdf_tmp)
        else:
            print(f"[1/3] Crawling URL: {url}", file=sys.stderr)
            text = crawl_url(url)

        print(f"[2/3] Extracting metadata via LLM ({LLM_MODEL})...", file=sys.stderr)

        metadata = extract_metadata(text)
        print(f"[3/3] Done.", file=sys.stderr)
        print(json.dumps({"metadata": metadata}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        if pdf_tmp:
            try:
                os.unlink(pdf_tmp)
            except Exception:
                pass


if __name__ == "__main__":
    main()
