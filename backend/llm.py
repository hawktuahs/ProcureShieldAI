"""
LLM abstraction layer.

Current provider: Google Gemini (default).
To swap in other providers (Ollama, OpenAI, Anthropic), set LLM_PROVIDER in environment.

Provider selection is driven by the LLM_PROVIDER environment variable:
  - "gemini"    → Google Gemini API (default)
  - "ollama"    → local Ollama
  - "openai"    → OpenAI-compatible endpoint
  - "anthropic" → Anthropic Claude API
"""

import json
import re
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base provider interface
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    @abstractmethod
    def chat(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        """Send a prompt; return the raw text response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...


# ---------------------------------------------------------------------------
# Ollama provider (default — local, free)
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.1:8b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def chat(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        try:
            import ollama
            client = ollama.Client(host=self.host)
            response = client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_ctx": 8192, "num_predict": max_tokens},
            )
            return response["message"]["content"].strip()
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise RuntimeError(
                    "Cannot connect to Ollama. Start it with: ollama serve"
                ) from e
            raise


# ---------------------------------------------------------------------------
# OpenAI-compatible provider stub (plug in your key + model name)
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    @property
    def name(self) -> str:
        return f"openai/{self.model}"

    def chat(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")


# ---------------------------------------------------------------------------
# Anthropic provider stub
# ---------------------------------------------------------------------------

class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def name(self) -> str:
        return f"anthropic/{self.model}"

    def chat(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")


# ---------------------------------------------------------------------------
# Google Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-3.1-flash-lite-preview", api_key: Optional[str] = None):
        self.model = model
        # Prioritize the specific free API key provided by the user
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    @property
    def name(self) -> str:
        return f"gemini/{self.model}"

    def chat(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        import time
        import random
        import re
        max_retries = 5
        base_delay = 5  # Increased base delay

        for attempt in range(max_retries):
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    if attempt < max_retries - 1:
                        # Try to parse "retry in X.Xs" from the error message
                        wait_match = re.search(r"retry in (\d+\.?\d*)s", error_msg)
                        if wait_match:
                            delay = float(wait_match.group(1)) + 1.0 # Add a buffer
                        else:
                            delay = (base_delay * (2 ** attempt)) + (random.random() * 5)
                        
                        logger.warning(f"Gemini Rate Limit (429). Retrying in {delay:.1f}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                
                logger.error(f"Gemini API error: {e}")
                raise e
        
        raise RuntimeError(f"Gemini API failed after {max_retries} retries due to rate limiting.")


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def _build_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider_name == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
        # If the environment is set to the broken gemini-1.5-flash, force it to gemini-3.1-flash-lite-preview
        if model == "gemini-1.5-flash":
            model = "gemini-3.1-flash-lite-preview"
        return GeminiProvider(model=model)
    elif provider_name == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        return OllamaProvider(model=model, host=host)
    elif provider_name == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        return OpenAIProvider(model=model)
    elif provider_name == "anthropic":
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        return AnthropicProvider(model=model)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider_name}. Choose: gemini, ollama, openai, anthropic")


# Singleton — imported once, reused everywhere
_provider: Optional[LLMProvider] = None

def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json_array(text: str) -> list:
    """
    Robustly extract the first complete JSON array from LLM output.
    Uses bracket counting to handle nested objects — avoids greedy regex failures.
    """
    start = text.find('[')
    if start == -1:
        return []
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
        if in_string:
            continue
        if ch == '[' or ch == '{':
            depth += 1
        elif ch == ']' or ch == '}':
            depth -= 1
        if ch == ']' and depth == 0:
            candidate = text[start:i + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # Try cleaning common Llama artifacts: trailing commas, control chars
                cleaned = re.sub(r',\s*([\]\}])', r'\1', candidate)
                cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass
            break
    return []


def _extract_json_object(text: str) -> dict:
    """
    Robustly extract the first complete JSON object from LLM output.
    Uses bracket counting to handle nested objects.
    """
    start = text.find('{')
    if start == -1:
        return {}
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
        if in_string:
            continue
        if ch == '{' or ch == '[':
            depth += 1
        elif ch == '}' or ch == ']':
            depth -= 1
        if ch == '}' and depth == 0:
            candidate = text[start:i + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                cleaned = re.sub(r',\s*([\]\}])', r'\1', candidate)
                cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass
            break
    return {}


def _truncate(text: str, head: int, tail: int) -> str:
    if len(text) <= head + tail:
        return text
    return text[:head] + "\n...[truncated]...\n" + text[-tail:]


def _split_pages(text: str) -> list[tuple[int, str]]:
    """
    Split page-marker-delimited text into [(page_num, page_text), ...].
    Expects markers like '--- PAGE 5 ---' as inserted by pdf_parser.
    """
    import re
    parts = re.split(r"\n---\s*PAGE\s+(\d+)\s*---\n", text)
    pages: list[tuple[int, str]] = []
    # parts[0] is text before any marker (usually empty)
    if parts[0].strip():
        pages.append((1, parts[0].strip()))
    # Remaining parts alternate: page_number, page_text
    for i in range(1, len(parts) - 1, 2):
        page_num = int(parts[i])
        page_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if page_text:
            pages.append((page_num, page_text))
    return pages


def _smart_sample(text: str, budget: int = 40000) -> str:
    """
    Extract a representative sample from long documents, preserving page markers.

    Government tenders typically have:
      - Cover / NIT at the start (general info, dates, EMD)
      - T&Cs / eligibility in the first third
      - Specifications / QR in the middle
      - Checklists, appendices, BoQ near the end

    Strategy: 30% front + 25% first-mid + 25% second-mid + 20% end.
    Cuts happen at page boundaries so page markers stay intact.
    """
    n = len(text)
    if n <= budget:
        return text

    pages = _split_pages(text)
    if not pages:
        # Fallback: old character-based approach
        head_sz = int(budget * 0.30)
        mid1_sz = int(budget * 0.25)
        mid2_sz = int(budget * 0.25)
        tail_sz = budget - head_sz - mid1_sz - mid2_sz
        mid1_start = max(head_sz, int(n * 0.25))
        mid2_start = max(mid1_start + mid1_sz, int(n * 0.55))
        return (
            text[:head_sz]
            + "\n\n--- [document section ~25%] ---\n\n"
            + text[mid1_start:mid1_start + mid1_sz]
            + "\n\n--- [document section ~55%] ---\n\n"
            + text[mid2_start:mid2_start + mid2_sz]
            + "\n\n--- [document end section] ---\n\n"
            + text[-tail_sz:]
        )

    # Page-aware sampling: select pages from 4 regions
    total_pages = len(pages)
    head_pages  = max(1, int(total_pages * 0.30))
    mid1_start  = max(head_pages, int(total_pages * 0.25))
    mid1_pages  = max(1, int(total_pages * 0.20))
    mid2_start  = max(mid1_start + mid1_pages, int(total_pages * 0.55))
    mid2_pages  = max(1, int(total_pages * 0.20))
    tail_pages  = max(1, int(total_pages * 0.20))

    selected: list[tuple[int, str]] = []
    selected.extend(pages[:head_pages])
    selected.extend(pages[mid1_start:mid1_start + mid1_pages])
    selected.extend(pages[mid2_start:mid2_start + mid2_pages])
    selected.extend(pages[-tail_pages:])

    # Deduplicate by page number (regions may overlap)
    seen = set()
    unique = []
    for pg_num, pg_text in selected:
        if pg_num not in seen:
            seen.add(pg_num)
            unique.append((pg_num, pg_text))

    # Reconstruct with page markers, truncating if over budget
    result_parts = []
    char_count = 0
    for pg_num, pg_text in unique:
        marker = f"\n--- PAGE {pg_num} ---\n"
        if char_count + len(marker) + len(pg_text) > budget:
            remaining = budget - char_count - len(marker)
            if remaining > 200:
                result_parts.append(marker + pg_text[:remaining])
            break
        result_parts.append(marker + pg_text)
        char_count += len(marker) + len(pg_text)

    return "\n".join(result_parts)


def _chunk_text(text: str, chunk_size: int = 6000, overlap: int = 500) -> list[str]:
    """Split text into overlapping chunks for multi-pass extraction on very long docs."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _chunk_text_by_pages(text: str, chars_per_chunk: int = 8000) -> list[str]:
    """
    Split text into chunks on page boundaries.
    Groups consecutive pages until the chunk exceeds chars_per_chunk.
    Each chunk retains its page markers so the LLM knows page numbers.
    """
    pages = _split_pages(text)
    if not pages:
        return _chunk_text(text, chunk_size=chars_per_chunk)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for pg_num, pg_text in pages:
        entry = f"\n--- PAGE {pg_num} ---\n{pg_text}"
        if current_len + len(entry) > chars_per_chunk and current_parts:
            chunks.append("\n".join(current_parts))
            current_parts = []
            current_len = 0
        current_parts.append(entry)
        current_len += len(entry)

    if current_parts:
        chunks.append("\n".join(current_parts))

    return chunks


# ---------------------------------------------------------------------------
# Core LLM tasks
# ---------------------------------------------------------------------------

CONFIDENCE_REVIEW_THRESHOLD = float(os.getenv("CONFIDENCE_REVIEW_THRESHOLD", "0.75"))
CONFIDENCE_LOW_THRESHOLD = float(os.getenv("CONFIDENCE_LOW_THRESHOLD", "0.40"))
# For technical docs, use multi-pass for everything over 15k chars
MULTIPASS_THRESHOLD = int(os.getenv("MULTIPASS_THRESHOLD", "15000"))


def _extract_criteria_from_chunk(text_chunk: str, provider: "LLMProvider", chunk_label: str = "") -> list[dict]:
    """Run criteria extraction on a single text chunk."""
    prompt = f"""You are a world-class senior procurement specialist specializing in Indian Government Tenders (MHA, BSF, CRPF, DGQA). 
Extract EVERY SINGLE technical parameter, quality requirement, financial gate, and eligibility criterion from this document section{' (' + chunk_label + ')' if chunk_label else ''}.

CRITICAL INSTRUCTIONS:
- Be EXTREMELY exhaustive. Extract 100% of the requirements.
- ZERO SUMMARIZATION: Every single row in every table (Technical Specs, QRs, BOQs, Financial Tables) MUST be a separate JSON object.
- Extract precise values: Dimensions, weight, tolerances, temperature ranges, material types, certificates required.
- Label the 'criterion_type' accurately: ["technical", "financial", "experience", "compliance", "documentation"].

IMPORTANT: Use the "--- PAGE N ---" markers for page numbers.

TENDER DOCUMENT:
{text_chunk}

Extract every requirement and return ONLY a JSON array. Each requirement must have:
- "criterion_type": one of the types above
- "description": clear description including specific values/units (e.g., "Operating Temperature: -20C to +50C")
- "is_mandatory": true or false
- "threshold_value": the specific value or limit
- "extraction_confidence": 1.0
- "raw_source_text": the EXACT verbatim table row or sentence
- "source_page": the page number (integer)

Return ONLY the JSON array. If none, return []."""

    try:
        raw = provider.chat(prompt, temperature=0.1, max_tokens=6000)
        if not raw or not raw.strip():
            logger.warning(f"Chunk extraction: LLM returned empty response for {chunk_label}")
            return []
        result = _extract_json_array(raw)
        logger.debug(f"Chunk extracted {len(result)} criteria")
        return result
    except Exception as e:
        logger.warning(f"Chunk extraction failed: {e}")
        return []


def _deduplicate_criteria(criteria_list: list[dict]) -> list[dict]:
    """Remove near-duplicate criteria by description similarity."""
    seen = []
    unique = []
    for c in criteria_list:
        desc = c.get("description", "").lower().strip()
        # Simple dedup: skip if first 60 chars match an existing entry
        key = desc[:60]
        if key not in seen:
            seen.append(key)
            unique.append(c)
    return unique


def extract_criteria_from_tender(tender_text: str) -> list[dict]:
    """
    Extract structured eligibility criteria from a tender document.

    Uses page-aware chunking so the LLM can report page numbers.
    For documents under MULTIPASS_THRESHOLD chars: single smart-sampled pass.
    For longer documents: multi-pass page-boundary chunked extraction with deduplication.
    Returns list of criterion dicts (each includes source_page).
    """
    provider = get_provider()
    logger.info(f"Extracting criteria from {len(tender_text):,} char document via {provider.name}")

    # For weaponry and technical docs, we use the FULL text if it's within the threshold.
    # We also use a more aggressive persona to ensure exhaustive extraction.
    if len(tender_text) <= MULTIPASS_THRESHOLD:
        return _extract_criteria_from_chunk(tender_text, provider, "Single-Pass Wholistic")

    # Multi-pass: split on page boundaries, extract from each, deduplicate
    logger.info(f"Document exceeds {MULTIPASS_THRESHOLD} chars — using multi-pass page-aware extraction")
    chunks = _chunk_text_by_pages(tender_text, chars_per_chunk=35000)
    all_criteria: list[dict] = []

    import time
    for i, chunk in enumerate(chunks):
        label = f"section {i+1}/{len(chunks)}"
        logger.info(f"Extracting criteria from {label}")
        criteria = _extract_criteria_from_chunk(chunk, provider, label)
        logger.info(f"Chunk {label}: Extracted {len(criteria)} raw items")
        all_criteria.extend(criteria)
        # Add a delay between chunks to avoid hitting RPM limits
        if i < len(chunks) - 1:
            time.sleep(3)

    deduped = _deduplicate_criteria(all_criteria)
    logger.info(f"Multi-pass criteria: {len(all_criteria)} raw → {len(deduped)} after dedup")
    return deduped


def evaluate_criterion(criterion: dict, bidder_text: str, bidder_name: str) -> dict:
    """
    Evaluate a single criterion against a bidder's submission.
    Returns verdict dict with confidence-based review escalation applied.
    """
    # For weaponry, we need a larger context to find specific technical evidence
    text_sample = _smart_sample(bidder_text, budget=40000)
    provider = get_provider()

    prompt = f"""You are an expert procurement evaluator. Evaluate whether this bidder meets a specific eligibility criterion.

CRITERION:
- Type: {criterion['criterion_type']}
- Requirement: {criterion['description']}
- Threshold: {criterion.get('threshold_value', 'Not specified')}
- Mandatory: {criterion['is_mandatory']}

BIDDER NAME: {bidder_name}

BIDDER DOCUMENTS:
{text_sample}

Evaluate carefully and return ONLY a JSON object. No explanation, no markdown, no code blocks.

Fields required:
- "verdict": "pass", "fail", or "needs_review" (use needs_review when information is ambiguous, partially present, or unreadable)
- "confidence": number 0.0 to 1.0 — CALIBRATE this carefully:
  * 0.95-1.0: Exact explicit evidence found (e.g., certificate number, exact turnover figure, specific clause match)
  * 0.75-0.94: Strong evidence but not exact match (e.g., turnover above threshold but not exact format)
  * 0.50-0.74: Partial or indirect evidence (e.g., related document found but not the exact one required)
  * 0.25-0.49: Very weak evidence, mostly inferred
  * 0.0-0.24: No evidence found at all
  Do NOT default to 0.9 for everything. Use the full range based on actual evidence quality.
- "extracted_value": the specific value/evidence found in bidder docs (e.g. "Annual turnover: Rs. 7.2 crore"), or null if not found
- "evidence_snippet": exact quote from bidder document supporting the verdict (max 300 chars), or null
- "reasoning": Concise, jargon-free 1-sentence summary explaining this verdict so an auditor can quickly screen it. Reference specific evidence.

Return ONLY the JSON object."""

    logger.info(f"Evaluating criterion '{criterion['description'][:40]}' for {bidder_name} via {provider.name}")

    try:
        raw = provider.chat(prompt, temperature=0.1)
        result = _extract_json_object(raw)
        if not result:
            raise ValueError("Empty JSON result")
    except Exception as e:
        logger.warning(f"Evaluation parse failed: {e}")
        return {
            "verdict": "needs_review",
            "confidence": 0.0,
            "extracted_value": None,
            "evidence_snippet": None,
            "reasoning": "Automated evaluation failed — manual review required.",
        }

    # Apply confidence thresholds: escalate low-confidence verdicts to needs_review
    confidence = float(result.get("confidence", 0.0))
    verdict = result.get("verdict", "needs_review")

    if confidence < CONFIDENCE_LOW_THRESHOLD:
        result["verdict"] = "needs_review"
        result["reasoning"] = (
            f"[Low confidence: {confidence:.0%}] " + result.get("reasoning", "")
        )
    elif confidence < CONFIDENCE_REVIEW_THRESHOLD and verdict != "needs_review":
        result["verdict"] = "needs_review"
        result["reasoning"] = (
            f"[Borderline confidence: {confidence:.0%}] " + result.get("reasoning", "")
        )

    return result


def compute_overall_verdict(
    evaluations: list[dict], criteria: list[dict]
) -> tuple[str, str]:
    """
    Derive overall bidder verdict from per-criterion results.
    Returns (verdict, reasoning).
    """
    mandatory_fails = []
    review_items = []

    for eval_item, criterion in zip(evaluations, criteria):
        effective_verdict = eval_item.get("human_verdict") or eval_item.get("verdict")
        if criterion["is_mandatory"]:
            if effective_verdict == "fail":
                mandatory_fails.append(criterion["description"])
            elif effective_verdict == "needs_review":
                review_items.append(criterion["description"])

    if mandatory_fails:
        return (
            "not_eligible",
            f"Failed mandatory criteria: {'; '.join(mandatory_fails[:3])}",
        )
    elif review_items:
        return (
            "needs_review",
            f"Review required for: {'; '.join(review_items[:3])}",
        )
    else:
        return "eligible", "All mandatory criteria satisfied with sufficient evidence."


# ---------------------------------------------------------------------------
# Tender analysis — structured sections (Documents, Scope, Eligibility, Contacts)
# ---------------------------------------------------------------------------

def _section_extract(prompt: str, provider: "LLMProvider") -> list[dict]:
    try:
        raw = provider.chat(prompt, temperature=0.1, max_tokens=6000)
        if not raw or not raw.strip():
            logger.warning("Section extraction: LLM returned empty response")
            return []
        result = _extract_json_array(raw)
        logger.debug(f"Section extracted {len(result)} items")
        return result
    except Exception as e:
        logger.warning(f"Section extraction failed: {e}")
        return []


def _multipass_section_extract(
    tender_text: str,
    prompt_builder,
    provider: "LLMProvider",
    section_name: str,
    dedup_key: str = "title",
    chunk_size: int = 35000,
    overlap: int = 5000,  # Increased overlap for better continuity
) -> list[dict]:
    """
    Multi-pass extraction for long documents.
    Splits text into page-aware chunks, runs prompt_builder(chunk) on each,
    deduplicates by dedup_key, and returns combined results.
    """
    # Force multi-pass for everything over a very small threshold
    # to ensure NO technical specifications are skipped.
    FORCE_MULTIPASS_MIN = 12000
    
    if len(tender_text) <= FORCE_MULTIPASS_MIN:
        prompt = prompt_builder(tender_text)
        return _section_extract(prompt, provider)

    logger.info(f"Multi-pass {section_name}: {len(tender_text):,} chars")
    chunks = _chunk_text_by_pages(tender_text, chars_per_chunk=chunk_size)
    all_items: list[dict] = []

    import time
    for i, chunk in enumerate(chunks):
        label = f"{section_name} chunk {i+1}/{len(chunks)}"
        logger.info(f"Extracting {label}")
        prompt = prompt_builder(chunk)
        items = _section_extract(prompt, provider)
        logger.info(f"{label}: Extracted {len(items)} raw items")
        all_items.extend(items)
        # Add a delay between chunks to avoid hitting RPM limits
        if i < len(chunks) - 1:
            time.sleep(3)

    # Deduplicate by key prefix
    seen = []
    unique = []
    for item in all_items:
        key = str(item.get(dedup_key, "")).lower().strip()[:60]
        if key and key not in seen:
            seen.append(key)
            unique.append(item)
        elif not key:
            unique.append(item)

    logger.info(f"Multi-pass {section_name} summary: {len(all_items)} raw → {len(unique)} after dedup")
    return unique


def extract_documents_section(tender_text: str) -> list[dict]:
    """
    Extract the submission checklist — all documents a bidder must submit.
    Uses multi-pass for long documents to ensure nothing is missed.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are a world-class defense procurement analyst. 
Extract EVERY SINGLE document, certificate, form, and letter that a bidder must submit for this weaponry tender.

CRITICAL: 
- Be EXTREMELY exhaustive. Zero summarization.
- Look for documents in checklists, Annexures, Appendices, and NIT sections.
- Capture specific weaponry-related certificates (e.g., OEM Authorization, DGQA approval, NABL lab reports).
- Use "--- PAGE N ---" markers for page numbers.

TENDER DOCUMENT:
{text_chunk}

Extract every document and return ONLY a JSON array. Each document must have:
- "title": name of the document (e.g., "OEM Authorization Certificate", "GST Registration")
- "categories": array of: ["financial", "technical", "compliance", "documentation", "experience"]
- "is_mandatory": true or false
- "format_available": true if a template/appendix is provided in the tender
- "summary": one sentence on what this document proves
- "how_to_submit": e.g., "notarized", "self-attested", "scanned PDF"
- "details": specific requirements (e.g., "valid for 180 days")
- "format_notes": e.g., "See Appendix-3"
- "source_text": verbatim quote from the document
- "source_page": page number (integer)

Return ONLY the JSON array."""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "documents", dedup_key="title"
    )


def extract_scope_section(tender_text: str) -> list[dict]:
    """
    Extract scope of work items — what the bidder must supply/do/deliver.
    Uses multi-pass for long documents.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are a world-class senior procurement specialist. 
Extract EVERY SINGLE technical parameter, quality specification, and deliverable from this tender section.

CRITICAL INSTRUCTIONS:
- Be EXTREMELY exhaustive. Zero summarization.
- Every technical parameter (e.g., dimensions, weight, performance, testing, material, calibre, velocity, range) must be a separate JSON entry.
- Reconstruct every row in Technical Specification or QR (Qualitative Requirements) tables as a separate item.
- Extract precise values and tolerances (e.g., "920 +/- 20mm", "Max 4500 gms", "Minimum 30 rounds").
- If a table has multiple columns for different variants, extract them as separate criteria or include the variant in the title.
- Use "--- PAGE N ---" markers for page numbers.

TENDER DOCUMENT:
{text_chunk}

Extract every distinct requirement and return ONLY a JSON array. Each item must have:
- "title": descriptive name (e.g., "Melt Flow Index", "Water resistance", "Calibre", "Barrel Length")
- "summary": detailed description with SPECIFIC values and tolerances. DO NOT omit numbers.
- "citations": array of 1-3 verbatim short quotes
- "source_text": the exact verbatim quote from the document
- "source_page": page number (integer)

Return ONLY the JSON array. If none, return []."""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "scope", dedup_key="title"
    )


def extract_eligibility_rich(tender_text: str) -> list[dict]:
    """
    Extract eligibility requirements with detailed parameters.
    Uses multi-pass for long documents.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are a world-class senior procurement specialist. 
Extract EVERY SINGLE eligibility requirement, qualification gate, and mandatory criterion from this tender section.

CRITICAL INSTRUCTIONS:
- Be EXTREMELY exhaustive. Zero summarization.
- Extract all gates: Financial turnover, OEM status, past experience, certificates required, non-blacklisting, bank guarantees, EMD details.
- Reconstruct tables into individual JSON entries.
- Identify if the requirement is MANDATORY (usually indicated by "shall", "must", "mandatory", or asterisk).
- Label 'criterion_type' as one of: ["financial", "technical", "experience", "compliance", "documentation"].
- For experience, capture specific values (e.g., "3 years experience", "supplied 500 units previously").
- For financial, capture specific limits (e.g., "Rs. 50 Lakhs turnover").
- Use "--- PAGE N ---" markers for page numbers.

TENDER DOCUMENT:
{text_chunk}

Extract every requirement and return ONLY a JSON array. Each requirement must have:
- "title": descriptive name (e.g., "Average Annual Turnover", "ISO 9001:2015 Certification")
- "summary": detailed description with SPECIFIC values and conditions. DO NOT omit numbers or years.
- "is_mandatory": true or false
- "criterion_type": one of the types listed above
- "threshold_value": the specific numeric or text requirement (e.g., "50,00,000", "3 years")
- "source_text": the exact verbatim quote from the document
- "source_page": page number (integer)

Return ONLY the JSON array. If none, return []."""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "eligibility", dedup_key="title"
    )


def extract_contacts_section(tender_text: str) -> list[dict]:
    """
    Extract contact persons, authorities, and offices mentioned.
    Uses smart sampling as deep depth is not required for contacts.
    """
    provider = get_provider()
    # Contacts are typically at the beginning or end
    text = _smart_sample(tender_text, budget=12000)

    def build_prompt(text_chunk: str) -> str:
        return f"""You are an expert procurement analyst. 
Extract all authorities, contact persons, and office addresses mentioned in this tender.

TENDER DOCUMENT:
{text_chunk}

Extract every contact and return ONLY a JSON array. Each contact must have:
- "role": e.g., "Consignee", "Tendering Authority", "Helpdesk"
- "name": full name
- "organisation": department or office name
- "address": full postal address
- "phone": telephone/fax numbers
- "email": email addresses
- "source_text": verbatim quote
- "source_page": page number (integer)

Return ONLY the JSON array. If none, return []."""

    # We use the build_prompt logic but with the sampled text in a single pass
    try:
        raw = provider.chat(build_prompt(text), temperature=0.1)
        return _extract_json_object(raw) or []
    except Exception as e:
        logger.warning(f"Contacts extraction failed: {e}")
        return []


def _section_extract_obj(prompt: str, provider: "LLMProvider") -> dict:
    """Like _section_extract but expects a JSON object, not an array."""
    try:
        raw = provider.chat(prompt, temperature=0.1, max_tokens=2000)
        result = _extract_json_object(raw)
        return result
    except Exception as e:
        logger.warning(f"Object section extraction failed: {e}")
        return {}


def extract_overview_section(tender_text: str) -> dict:
    """
    Extract high-level tender metadata.
    Always uses a smart sample of the document to save tokens while capturing key info.
    """
    provider = get_provider()
    # Overview info is almost always on the first few pages
    text = _smart_sample(tender_text, budget=30000)

    prompt = f"""You are a world-class government procurement analyst. Extract high-level metadata for this tender.

TENDER DOCUMENT:
{text}

Extract the following fields into a JSON object:
- "work_description": brief summary of the work (e.g., "Supply of 400 Nos Polymer Based Pistol")
- "total_quantity": the primary total quantity of the main item being procured (e.g., "400", "12000")
- "quantity_unit": the unit for total_quantity (e.g., "Nos", "Sets")
- "tender_type": e.g., "Open Tender", "Limited Tender"
- "evaluation_method": e.g., "L1", "QCBS"
- "location": work location
- "bid_type": e.g., "Two-Bid System"
- "beneficiary": department/organisation
- "published_date": tender publication date
- "bid_opening_date": technical bid opening date
- "last_activity_date": date of last amendment/activity
- "tender_fee_amount": numeric fee amount
- "emd_fee_amount": numeric EMD amount

Return ONLY the JSON object. If no data, return {{}}."""

    raw = provider.chat(prompt, temperature=0.1)
    return _extract_json_object(raw) or {}


def extract_items_section(tender_text: str) -> list[dict]:
    """
    Extract itemised list of goods/services with specifications.
    Uses multi-pass for long documents to capture specs from all pages.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are a world-class government procurement analyst specializing in Indian tenders. 
Extract EVERY SINGLE line item, good, or service from this tender section, including EXACT quantities and full technical specifications.

CRITICAL INSTRUCTIONS:
- Be EXTREMELY exhaustive. Extract every row from BOQ (Bill of Quantities) tables.
- Capture the quantity, unit, and delivery details for EACH item.
- RECONSTRUCT TABLES: Many tables are OCR'd and might look like "1 | 2 | Item Name | 500 | Nos" or have rows split across multiple lines. Mentally combine them to extract the full item name and its corresponding quantity.
- QUANTITY IS CRITICAL: Look for columns like "Qty", "Quantity", "Nos", "Amount", "Approx Qty".
- ZERO SUMMARIZATION: If a table has 50 items, return 50 JSON objects.
- Use "--- PAGE N ---" markers for page numbers.

TENDER DOCUMENT:
{text_chunk}

Extract each item and return ONLY a JSON array. Each item must have:
- "item_name": full name of the item (e.g., "9mm Polymer Based Pistol")
- "quantity": numeric value ONLY as a string (e.g., "400", "12000"). If a range is given, use the higher value.
- "quantity_unit": unit of measurement (e.g., "Nos", "Kg", "Pairs", "Sets", "Units")
- "delivery_location": destination department or city
- "consignee": receiving officer or office
- "delivery_period": timeline (e.g., "12 months", "180 days")
- "specifications": array of specific technical details (calibre, weight, dimensions, materials, etc.)
- "source_text": verbatim quote from the document including the item name and quantity
- "source_page": page number (integer) where this item was found

Return ONLY the JSON array. If no items, return []."""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "items", dedup_key="item_name"
    )


def analyze_tender_full(tender_text: str) -> dict:
    """
    Run all section extractions and return combined analysis dict.
    Optimized for Gemini: uses a single consolidated request for documents under threshold.
    """
    provider = get_provider()
    
    # We disabled consolidated analysis for anything over a very small size 
    # to ensure the AI doesn't summarize weaponry specs.
    CONSOLIDATED_MAX = 15000 
    
    if len(tender_text) <= CONSOLIDATED_MAX:
        logger.info(f"Starting consolidated wholistic analysis for {len(tender_text):,} chars")
        
        prompt = f"""You are a world-class senior procurement specialist. Analyze this tender and extract EVERY SINGLE data point.

CRITICAL INSTRUCTIONS:
- Be EXTREMELY exhaustive. Zero summarization.
- Reconstruct all tables (Technical Specs, QRs, BOQs): every single row MUST be a separate JSON object.
- Extract precise values: Dimensions, weights, tolerances, financial limits, experience years.
- Capture all critical dates and required certificates.

TENDER DOCUMENT:
{tender_text}

Return a single JSON object with EXACTLY these 6 keys. Every item in the arrays MUST be a detailed object.

1. "overview": Object with fields: work_description, total_quantity, quantity_unit, tender_type, evaluation_method, location, beneficiary, published_date, bid_opening_date, tender_fee_amount, emd_fee_amount.
2. "documents": Array of objects. Each MUST have: "title", "is_mandatory" (bool), "summary", "source_page" (int).
3. "scope_of_work": Array of objects. Each MUST have: "title", "summary" (detailed with values), "source_page" (int).
4. "eligibility": Array of objects. Each MUST have: "title", "summary" (detailed), "is_mandatory" (bool), "criterion_type", "threshold_value", "source_page" (int).
5. "contacts": Array of objects. Each MUST have: "role", "name", "organisation", "address", "phone", "email".
6. "items": Array of objects. Each MUST have: "item_name", "quantity", "quantity_unit", "specifications" (array of strings), "source_page" (int).

Return ONLY the raw JSON object. No explanation."""

        try:
            raw = provider.chat(prompt, temperature=0.1, max_tokens=8000)
            results = _extract_json_object(raw)
            if results:
                # Basic validation
                for key in ["documents", "scope_of_work", "eligibility", "contacts", "items"]:
                    if key not in results or not isinstance(results[key], list):
                        results[key] = []
                if "overview" not in results or not isinstance(results["overview"], dict):
                    results["overview"] = {}
                
                logger.info("Consolidated analysis successful")
                return results
        except Exception as e:
            logger.error(f"Consolidated analysis failed: {e}")

    # For everything else, run exhaustive individual sections
    logger.info(f"Running exhaustive individual section analysis for {len(tender_text):,} chars")
    results = {}

    # 1. Overview (Can use sample)
    results["overview"] = extract_overview_section(tender_text)
    
    # 2. Array sections (Exhaustive)
    array_sections = [
        ("documents", extract_documents_section),
        ("scope_of_work", extract_scope_section),
        ("eligibility", extract_eligibility_rich),
        ("contacts", extract_contacts_section),
        ("items", extract_items_section),
    ]
    
    import time
    for i, (key, fn) in enumerate(array_sections):
        try:
            results[key] = fn(tender_text)
            logger.info(f"Exhaustive section '{key}': {len(results[key])} items")
            if i < len(array_sections) - 1:
                time.sleep(3) # Delay to respect RPM
        except Exception as e:
            logger.error(f"Exhaustive section '{key}' failed: {e}")
            results[key] = []

    return results


def answer_question(tender_text: str, question: str) -> str:
    """
    Answer a free-form question grounded in the tender document.
    Returns a plain-text answer.
    """
    provider = get_provider()
    text_sample = _smart_sample(tender_text, budget=18000)

    prompt = f"""You are an expert government procurement analyst. Answer the following question based ONLY on the provided tender document. Be specific, cite relevant clauses or values where possible. If the answer is not found in the document, say so clearly.

TENDER DOCUMENT:
{text_sample}

QUESTION: {question}

Provide a clear, concise answer grounded in the tender document. Use bullet points if listing multiple items. Do not make up information not present in the document.
When asked about dates or deadlines, provide a concise, definitive answer. Act as an analyst and explicitly interpret tender terminology (e.g., if asked "when is the last day to file", explicitly state that "receipt of online tenders" or "closing date" is the submission deadline)."""

    try:
        return provider.chat(prompt, temperature=0.2, max_tokens=1024)
    except Exception as e:
        logger.error(f"answer_question failed: {e}")
        raise
