#!/usr/bin/env python3
"""
Extract paper metadata from a PDF or HTML file using:
1. Text extraction:
   - PDF mode: crawl4ai NaivePDFProcessorStrategy to extract text from first pages
   - HTML mode: stdlib html.parser to extract text from pdf2htmlEX-generated HTML
2. Local multimodal LLM (localhost:8000/v1, glm-4.5-air) to extract structured metadata
"""
import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import requests
from crawl4ai.processors.pdf.processor import NaivePDFProcessorStrategy

LLM_BASE = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4.5-air")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")

EXTRACTION_PROMPT = """You are a research paper metadata extractor.
Given the text extracted from the first pages of a research paper PDF, extract the following fields and return them as a single JSON object.

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


def extract_pdf_text(pdf_path: str) -> str:
    """Use crawl4ai NaivePDFProcessorStrategy to extract text from PDF first pages."""
    strategy = NaivePDFProcessorStrategy(extract_images=False, save_images_locally=False)
    result = strategy.process_batch(Path(pdf_path))

    texts = []
    for page in result.pages[:3]:
        raw = page.raw_text.strip()
        if raw:
            # Remove unicode replacement characters and clean up
            cleaned = raw.replace('�', '').replace('\x00', '')
            # Normalize whitespace: collapse multiple spaces/newlines
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:
                texts.append(cleaned)

    return "\n\n".join(texts)


class _HTMLTextExtractor(HTMLParser):
    """Strip HTML tags, keeping text content. Skip script/style/head blocks."""
    _SKIP_TAGS = {'script', 'style', 'head'}
    _BLOCK_TAGS = {'p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'blockquote'}

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag in self._BLOCK_TAGS:
            self._parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in self._BLOCK_TAGS:
            self._parts.append('\n')

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self):
        return ''.join(self._parts)


def extract_html_text(html_path: str) -> str:
    """Extract clean text from an HTML file (e.g. pdf2htmlEX output)."""
    with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
        html_content = f.read()

    extractor = _HTMLTextExtractor()
    extractor.feed(html_content)
    raw = extractor.get_text()

    # Normalize whitespace: collapse runs of spaces/tabs, keep paragraph breaks
    lines = []
    for line in raw.split('\n'):
        cleaned = re.sub(r'[ \t]+', ' ', line).strip()
        if cleaned:
            lines.append(cleaned)

    # Collapse 3+ consecutive blank lines into 2
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_metadata(text: str) -> dict:
    """Use local LLM to extract structured paper metadata from PDF text."""
    resp = requests.post(
        f"{LLM_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n---\n\nExtracted PDF text:\n{text[:100000]}"},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        timeout=300,
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
        # Try to find and parse the first JSON object
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass

        # Last resort: line-by-line extraction with safe defaults
        print(f"[WARN] JSON parse failed, falling back to line-by-line extraction", file=sys.stderr)
        fallback = {
            "title": None,
            "authors": [],
            "year": None,
            "venue": None,
            "doi": None,
            "abstract": None,
        }
        doi_match = re.search(r'10\.\d{4,}[^\s"]+', content)
        if doi_match:
            fallback["doi"] = doi_match.group(0).rstrip("\"').,>")
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', content)
        if year_match:
            fallback["year"] = int(year_match.group(1))
        # Title: first substantial line that isn't a DOI, year-only, or author list
        for line in content.split('\n'):
            line = line.strip()
            if len(line) > 10 and not re.match(r'^(10\.\d|20\d{2}|19\d{2})', line):
                fallback["title"] = line[:200]
                break
        return fallback


def main():
    parser = argparse.ArgumentParser(description="Extract paper metadata from a PDF or HTML file")
    parser.add_argument("input_path", help="Path to PDF or HTML file")
    parser.add_argument("--html", action="store_true", help="Treat input as HTML (pdf2htmlEX output) instead of PDF")
    args = parser.parse_args()

    if not os.path.exists(args.input_path):
        print(json.dumps({"error": f"File not found: {args.input_path}"}), file=sys.stderr)
        sys.exit(1)

    mode = "HTML" if args.html else "PDF"
    print(f"[1/3] Extracting text from {mode}: {args.input_path}", file=sys.stderr)
    if args.html:
        text = extract_html_text(args.input_path)
    else:
        text = extract_pdf_text(args.input_path)
    print(f"      Extracted {len(text)} chars", file=sys.stderr)

    print(f"[2/3] Extracting metadata via LLM ({LLM_MODEL})...", file=sys.stderr)
    metadata = extract_metadata(text)

    print(f"[3/3] Done.", file=sys.stderr)
    print(json.dumps({"metadata": metadata}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
