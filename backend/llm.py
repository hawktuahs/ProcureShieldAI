"""
LLM abstraction layer.

Current provider: Ollama (local, zero-cost).
To swap in a paid API (OpenAI, Anthropic, Gemini, etc.), implement a new
class inheriting LLMProvider and set ACTIVE_PROVIDER in config.

Provider selection is driven by the LLM_PROVIDER environment variable:
  - "ollama"    → local Ollama (default)
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
# Provider factory
# ---------------------------------------------------------------------------

def _build_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider_name == "ollama":
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
        raise ValueError(f"Unknown LLM_PROVIDER: {provider_name}. Choose: ollama, openai, anthropic")


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
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


def _extract_json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _truncate(text: str, head: int, tail: int) -> str:
    if len(text) <= head + tail:
        return text
    return text[:head] + "\n...[truncated]...\n" + text[-tail:]


def _smart_sample(text: str, budget: int = 20000) -> str:
    """
    Extract a representative sample from long documents.

    Government tenders typically have:
      - Cover / NIT at the start (general info, dates, EMD)
      - T&Cs / eligibility in the first third
      - Specifications / QR in the middle
      - Checklists, appendices, BoQ near the end

    Strategy: 30% front + 25% first-mid + 25% second-mid + 20% end.
    This ensures all major sections of 50-100+ page tenders are covered.
    """
    n = len(text)
    if n <= budget:
        return text

    head_sz  = int(budget * 0.30)
    mid1_sz  = int(budget * 0.25)
    mid2_sz  = int(budget * 0.25)
    tail_sz  = budget - head_sz - mid1_sz - mid2_sz

    # First-mid: around 30% through the document
    mid1_start = max(head_sz, int(n * 0.25))
    mid1_end   = mid1_start + mid1_sz

    # Second-mid: around 60% through the document
    mid2_start = max(mid1_end, int(n * 0.55))
    mid2_end   = mid2_start + mid2_sz

    return (
        text[:head_sz]
        + "\n\n--- [document section ~25%] ---\n\n"
        + text[mid1_start:mid1_end]
        + "\n\n--- [document section ~55%] ---\n\n"
        + text[mid2_start:mid2_end]
        + "\n\n--- [document end section] ---\n\n"
        + text[-tail_sz:]
    )


def _chunk_text(text: str, chunk_size: int = 6000, overlap: int = 500) -> list[str]:
    """Split text into overlapping chunks for multi-pass extraction on very long docs."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Core LLM tasks
# ---------------------------------------------------------------------------

CONFIDENCE_REVIEW_THRESHOLD = float(os.getenv("CONFIDENCE_REVIEW_THRESHOLD", "0.75"))
CONFIDENCE_LOW_THRESHOLD = float(os.getenv("CONFIDENCE_LOW_THRESHOLD", "0.40"))
# For very long docs (>30k chars), use multi-pass extraction
MULTIPASS_THRESHOLD = int(os.getenv("MULTIPASS_THRESHOLD", "30000"))


def _extract_criteria_from_chunk(text_chunk: str, provider: "LLMProvider", chunk_label: str = "") -> list[dict]:
    """Run criteria extraction on a single text chunk."""
    prompt = f"""You are an expert government procurement analyst. Extract ALL eligibility criteria from this tender document{' (' + chunk_label + ')' if chunk_label else ''}.

TENDER DOCUMENT:
{text_chunk}

Extract every eligibility criterion and return ONLY a JSON array. No explanation, no markdown, no code blocks. Just the raw JSON array.

Each criterion must have exactly these fields:
- "criterion_type": one of "financial", "technical", "compliance", "documentation"
- "description": clear one-sentence description of the requirement
- "is_mandatory": true or false
- "threshold_value": the specific number, certification name, or requirement (e.g. "5 crore", "ISO 9001", "3 years", "9mm x 19mm", null if no specific threshold)
- "extraction_confidence": number 0.0 to 1.0 (your confidence in this extraction)
- "raw_source_text": the exact sentence or phrase from the document that contains this criterion (max 200 chars)

Include ALL types of eligibility criteria:
- Financial: turnover, EMD, net worth, bid security
- Technical: product specifications, dimensions, performance requirements, certifications
- Compliance: GST, registrations, Make-in-India, debarment declarations
- Documentation: certificates, test reports, appendices required

If no eligibility criteria are found in this section, return an empty array: []

Return ONLY the JSON array."""

    try:
        raw = provider.chat(prompt, temperature=0.1)
        return _extract_json_array(raw)
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

    For documents under MULTIPASS_THRESHOLD chars: single smart-sampled pass.
    For longer documents: multi-pass chunked extraction with deduplication.
    Returns list of criterion dicts.
    """
    provider = get_provider()
    logger.info(f"Extracting criteria from {len(tender_text):,} char document via {provider.name}")

    if len(tender_text) <= MULTIPASS_THRESHOLD:
        # Single pass with smart sampling
        text_sample = _smart_sample(tender_text, budget=20000)
        return _extract_criteria_from_chunk(text_sample, provider)

    # Multi-pass: split into chunks, extract from each, deduplicate
    logger.info(f"Document exceeds {MULTIPASS_THRESHOLD} chars — using multi-pass extraction")
    chunks = _chunk_text(tender_text, chunk_size=6000, overlap=500)
    all_criteria: list[dict] = []

    for i, chunk in enumerate(chunks):
        label = f"section {i+1}/{len(chunks)}"
        logger.info(f"Extracting criteria from {label}")
        criteria = _extract_criteria_from_chunk(chunk, provider, label)
        all_criteria.extend(criteria)

    deduped = _deduplicate_criteria(all_criteria)
    logger.info(f"Multi-pass: {len(all_criteria)} raw → {len(deduped)} after dedup")
    return deduped


def evaluate_criterion(criterion: dict, bidder_text: str, bidder_name: str) -> dict:
    """
    Evaluate a single criterion against a bidder's submission.
    Returns verdict dict with confidence-based review escalation applied.
    """
    text_sample = _smart_sample(bidder_text, budget=12000)
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
- "confidence": number 0.0 to 1.0 (your confidence in this verdict)
- "extracted_value": the specific value/evidence found in bidder docs (e.g. "Annual turnover: Rs. 7.2 crore"), or null if not found
- "evidence_snippet": exact quote from bidder document supporting the verdict (max 300 chars), or null
- "reasoning": 2-3 sentence explanation of why this verdict was reached, referencing specific evidence

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
        raw = provider.chat(prompt, temperature=0.1, max_tokens=3000)
        result = _extract_json_array(raw)
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
    chunk_size: int = 8000,
    overlap: int = 800,
) -> list[dict]:
    """
    Multi-pass extraction for long documents.
    Splits text into chunks, runs prompt_builder(chunk) on each,
    deduplicates by dedup_key, and returns combined results.
    """
    if len(tender_text) <= MULTIPASS_THRESHOLD:
        text = _smart_sample(tender_text, budget=20000)
        prompt = prompt_builder(text)
        return _section_extract(prompt, provider)

    logger.info(f"Multi-pass {section_name}: {len(tender_text):,} chars")
    chunks = _chunk_text(tender_text, chunk_size=chunk_size, overlap=overlap)
    all_items: list[dict] = []

    for i, chunk in enumerate(chunks):
        label = f"{section_name} chunk {i+1}/{len(chunks)}"
        logger.info(f"Extracting {label}")
        prompt = prompt_builder(chunk)
        items = _section_extract(prompt, provider)
        all_items.extend(items)

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

    logger.info(f"Multi-pass {section_name}: {len(all_items)} raw → {len(unique)} after dedup")
    return unique


def extract_documents_section(tender_text: str) -> list[dict]:
    """
    Extract the submission checklist — all documents a bidder must submit.
    Uses multi-pass for long documents to ensure nothing is missed.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are an expert government procurement analyst. Extract ALL documents, certificates, letters, declarations, and forms that a bidder must submit for this tender.

TENDER DOCUMENT:
{text_chunk}

Look for:
- Required certificates (GST, PAN, registration, ISO, BIS, quality certifications)
- Mandatory letters (authorization letters, undertakings, power of attorney, covering letters)
- Declarations (non-blacklisting, no-litigation, debarment, integrity pact)
- Financial documents (EMD/bid security, annual reports, turnover certificates, bank guarantees)
- Technical documents (test reports, product brochures, conformity certificates, specifications compliance)
- Experience documents (past supply orders, completion certificates, client references)
- Bid forms (price schedule, BoQ, technical bid format, commercial bid format)
- Appendices and annexures referenced in the tender (Appendix-1 through Appendix-N)
- Any document mentioned in a "checklist" or "list of documents" section

Return ONLY a JSON array. Each element represents one document required. No explanation, no markdown, no code blocks.

Each item must have these exact fields:
- "title": name of the document (e.g. "Bid Securing Declaration", "Authorization Letter from OEM", "Annual Turnover Certificate")
- "categories": array of strings from: ["financial", "technical", "compliance", "documentation", "bid security", "identity", "experience"]
- "is_mandatory": true or false
- "format_available": true if tender provides a template/appendix/format for this, false otherwise
- "summary": one sentence describing what this document proves or why it is needed
- "how_to_submit": how to submit (e.g. "self-attested copy", "on company letterhead", "notarised", "uploaded on GeM/CPP portal") — null if not specified
- "details": specific details from the tender about this document — null if not specified
- "format_notes": notes about format or appendix reference (e.g. "As per Appendix-3", "Format at Page 26") — null if not specified
- "source_text": the exact phrase or sentence from the document (max 200 chars)

Return ONLY the JSON array. If no submission documents found in this section, return [].
Example: [{{"title": "Bid Securing Declaration", "categories": ["bid security"], "is_mandatory": true, "format_available": true, "summary": "Declaration in lieu of EMD as per tender requirement.", "how_to_submit": "on company letterhead with authorised signatory", "details": "Must be valid for 225 days from bid opening", "format_notes": "As per Appendix-2", "source_text": "Bid securing declaration as per format..."}}]"""

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
        return f"""You are an expert government procurement analyst. Extract all scope of work items and requirements from this tender section.

TENDER DOCUMENT:
{text_chunk}

Extract every distinct requirement including:
- What goods/services must be supplied (product names, models, types)
- Technical specifications and quality requirements (dimensions, materials, performance parameters)
- Delivery terms (timeline, location, packaging, transport)
- Warranty and after-sales support requirements
- Testing and inspection requirements (factory testing, proof testing, acceptance criteria)
- Quantity and lot details
- Installation, training, or commissioning requirements
- Maintenance and spare parts requirements
- Any performance guarantees or liquidated damages clauses

Return ONLY a JSON array. Each element is one distinct scope/requirement item. No explanation, no markdown, no code blocks.

Each item must have these exact fields:
- "title": short descriptive name (5-10 words max)
- "summary": 1-2 clear sentences describing this scope item with SPECIFIC values, numbers, and details from the tender
- "citations": array of 1-3 direct short quotes from the tender text (each max 200 chars)
- "source_text": the single most important quote (max 200 chars)

Return ONLY the JSON array. If no scope items found in this section, return [].
Example: [{{"title": "Supply of 9mm Polymer Based Pistols", "summary": "Supply 400 units of 9mm x 19mm polymer-frame semi-automatic pistols conforming to QR/TD at Appendix-6. Must include 2 magazines per pistol.", "citations": ["Supply of Polymer Based Pistol (9mm), 400 No.", "Each pistol shall be supplied with 02 magazines"], "source_text": "Supply of Polymer Based Pistol (9mm), 400 No."}}]"""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "scope", dedup_key="title"
    )


def extract_eligibility_rich(tender_text: str) -> list[dict]:
    """
    Extract eligibility requirements with citation blockquotes.
    Uses multi-pass for long documents.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are an expert government procurement analyst. Extract ALL eligibility requirements and qualifying criteria from this tender section.

TENDER DOCUMENT:
{text_chunk}

Extract every eligibility/qualification requirement including:
- Financial: minimum turnover, net worth, bid security/EMD amounts, bank guarantee
- Technical: product certifications (BIS, ISO, MIL-STD), testing requirements, design approvals
- Experience: past supply orders, years in business, similar contract completion
- Compliance: GST/PAN registration, Make in India, MSME, non-blacklisting declarations
- Documentation: specific certificates, letters, declarations required for eligibility
- Product specifications that serve as eligibility gates (calibre, dimensions, materials, performance thresholds)

Return ONLY a JSON array. Each element is one eligibility requirement. No explanation, no markdown, no code blocks.

Each item must have these exact fields:
- "title": short descriptive name (e.g. "Minimum Annual Turnover", "BIS Certification", "EMD / Bid Security")
- "summary": one sentence stating the requirement clearly with SPECIFIC values/thresholds from the tender
- "citations": array of 1-3 direct short quotes from the tender text (each max 200 chars)
- "is_mandatory": true or false
- "threshold_value": specific value (e.g. "Rs. 5 crore", "ISO 9001:2015", "3 similar orders", "9mm x 19mm") — null if none
- "source_text": most relevant quote (max 200 chars)

Return ONLY the JSON array. If none found in this section, return [].
Example: [{{"title": "Earnest Money Deposit", "summary": "EMD of Rs. 12,00,000 must be submitted via bank guarantee or demand draft, valid for 225 days.", "citations": ["EMD should be valid up to 225 days from the date of opening of tender", "Rs. 12,00,000/- (Rupees Twelve Lakh) only"], "is_mandatory": true, "threshold_value": "Rs. 12,00,000", "source_text": "Rs. 12,00,000/- (Rupees Twelve Lakh) only"}}]"""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "eligibility", dedup_key="title"
    )


def extract_contacts_section(tender_text: str) -> list[dict]:
    """
    Extract all contact information and authorities from the tender.
    Contacts are usually in the first and last sections, so smart-sample is sufficient.
    """
    text = _smart_sample(tender_text, budget=20000)
    provider = get_provider()
    prompt = f"""You are an expert government procurement analyst. Extract all contact details and authority information from this tender.

TENDER DOCUMENT:
{text}

Return ONLY a JSON array. Each element is one contact or authority. No explanation, no markdown, no code blocks.

Each item must have these exact fields:
- "role": the person's or office's role (e.g. "Tender Inviting Authority", "For Queries", "Consignee", "Inspection Authority")
- "name": person's name if stated — null if not given
- "organisation": organisation or department name — null if not given
- "address": full address — null if not given
- "phone": phone/fax number — null if not given
- "email": email address — null if not given
- "citations": array of 1-2 direct short quotes from the tender that mention this contact (each max 200 chars)
- "source_text": most relevant quote (max 200 chars)

Return ONLY the JSON array. If no contacts found, return [].
Example: [{{"role": "Tender Inviting Authority", "name": "Commandant (Proc)Dte", "organisation": "CRPF", "address": "Block No.1, CGO Complex, Lodhi Road, New Delhi - 110023", "phone": "011-24369586", "email": "proccell@crpf.gov.in", "citations": ["Directorate General, CRPF, Block No.1, CGO Complex"], "source_text": "e-mail: proccell@crpf.gov.in"}}]"""
    return _section_extract(prompt, provider)


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
    Extract high-level tender metadata: work description, type, dates, fees,
    location, beneficiary, and purchase preferences.
    Returns a single JSON object (not an array).
    """
    text = _smart_sample(tender_text, budget=20000)
    provider = get_provider()
    prompt = f"""You are an expert government procurement analyst. Extract the key tender metadata from this document.

TENDER DOCUMENT:
{text}

Return ONLY a single JSON object. No explanation, no markdown, no code blocks.

The object must have exactly these fields (use null for any field not found):
- "work_description": the full name or title of what is being procured (e.g. "Supply of 9mm Polymer Based Pistols")
- "tender_type": e.g. "Two Packet Bid", "Single Packet Bid", "Limited Tender", "Open Tender" — null if not stated
- "evaluation_method": how bids will be evaluated (e.g. "L1 basis", "Total value wise evaluation") — null if not stated
- "location": delivery or buyer location (e.g. "New Delhi", "Karnataka; Bengaluru Urban") — null if not stated
- "bid_type": "SERVICE" or "PRODUCT" or "WORKS" — null if not stated
- "beneficiary": the receiving organisation or authority (full name) — null if not stated
- "published_date": tender publication date as string (e.g. "25 Mar 2026") — null if not found
- "bid_opening_date": bid opening / submission deadline date (e.g. "15 Apr 2026") — null if not found
- "last_activity_date": last date for queries/corrigendum (e.g. "15 Apr 2026") — null if not found
- "tender_fee_amount": tender document fee (e.g. "₹500", "₹0", "Nil") — null if not stated
- "tender_fee_exemption_allowed": "Yes" or "No" — null if not stated
- "emd_fee_amount": EMD / bid security amount (e.g. "₹12,00,000", "Exempted") — null if not stated
- "emd_fee_exemption_allowed": "Yes" or "No" — null if not stated
- "purchase_preferences": array of applicable purchase preferences (e.g. ["MSE EMD Exemption", "Startup Exemption", "Make in India"]) — empty array [] if none

Return ONLY the JSON object.
Example: {{"work_description": "Supply of Cotton Terry Towel (MHA) (V2)", "tender_type": "Two Packet Bid", "evaluation_method": "Total value wise evaluation", "location": "Karnataka; Bengaluru Urban", "bid_type": "PRODUCT", "beneficiary": "Inspector General, Frontier HQ, BSF", "published_date": "25 Mar 2026", "bid_opening_date": "15 Apr 2026", "last_activity_date": "15 Apr 2026", "tender_fee_amount": "₹0", "tender_fee_exemption_allowed": "No", "emd_fee_amount": "Exempted", "emd_fee_exemption_allowed": "Yes", "purchase_preferences": ["MSE EMD Exemption", "Startup Exemption"]}}"""
    return _section_extract_obj(prompt, provider)


def extract_items_section(tender_text: str) -> list[dict]:
    """
    Extract itemised list of goods/services with specifications.
    Uses multi-pass for long documents to capture specs from all pages.
    """
    provider = get_provider()

    def build_prompt(text_chunk: str) -> str:
        return f"""You are an expert government procurement analyst. Extract all items, goods, and services to be procured from this tender section, along with their DETAILED specifications.

TENDER DOCUMENT:
{text_chunk}

Extract each item with its full technical specifications. Look for:
- Product names, model numbers, types
- Technical specifications: dimensions, calibre, weight, materials, capacity, power ratings
- Quality requirements: BIS standards, MIL-STD, IS codes, testing standards
- Performance parameters: accuracy, range, reliability, durability
- Packaging and marking requirements
- Accessories and components included (magazines, holsters, cleaning kits, etc.)

Return ONLY a JSON array. Each element is one line item. No explanation, no markdown, no code blocks.

Each item must have these exact fields:
- "item_name": full name of the item or service with key spec (e.g. "9mm x 19mm Polymer Based Semi-Automatic Pistol")
- "quantity": numeric quantity as a string (e.g. "400", "12,000")
- "quantity_unit": unit of measurement (e.g. "Nos", "Sets", "Pairs", "MT") — null if not specified
- "delivery_location": delivery address or consignee location — null if not specified
- "consignee": name of the person/office receiving goods — null if not specified
- "delivery_period": delivery timeline (e.g. "105 days", "12 months") — null if not specified
- "specifications_ref": reference to specification appendix (e.g. "Appendix-6", "QR/TD") — null if not specified
- "specifications": array of key specification strings (e.g. ["Calibre: 9mm x 19mm", "Weight: ≤850g with empty magazine", "Magazine capacity: 15 rounds minimum", "Barrel length: 95-115mm"]) — empty array [] if no specs found
- "source_text": exact quote from the document (max 200 chars)

Return ONLY the JSON array. If no items found in this section, return [].
Example: [{{"item_name": "9mm x 19mm Polymer Based Semi-Automatic Pistol", "quantity": "400", "quantity_unit": "Nos", "delivery_location": "CRPF, New Delhi", "consignee": "Commandant (Proc)Dte", "delivery_period": "12 months", "specifications_ref": "Appendix-6 QR/TD", "specifications": ["Calibre: 9mm x 19mm", "Action: Semi-automatic, recoil operated", "Weight: max 850g with empty magazine", "Magazine capacity: min 15 rounds", "Barrel length: 95-115mm"], "source_text": "Supply of Polymer Based Pistol (9mm), 400 No."}}]"""

    return _multipass_section_extract(
        tender_text, build_prompt, provider, "items", dedup_key="item_name"
    )


def analyze_tender_full(tender_text: str) -> dict:
    """
    Run all section extractions and return combined analysis dict.
    Called from background task after tender upload.
    """
    logger.info("Starting full tender analysis (6 sections)")
    results = {}

    # Array sections
    array_sections = [
        ("documents", extract_documents_section),
        ("scope_of_work", extract_scope_section),
        ("eligibility", extract_eligibility_rich),
        ("contacts", extract_contacts_section),
        ("items", extract_items_section),
    ]
    for key, fn in array_sections:
        try:
            results[key] = fn(tender_text)
            logger.info(f"Analysis section '{key}': {len(results[key])} items")
        except Exception as e:
            logger.error(f"Analysis section '{key}' failed: {e}")
            results[key] = []

    # Object section
    try:
        results["overview"] = extract_overview_section(tender_text)
        logger.info(f"Analysis section 'overview': extracted")
    except Exception as e:
        logger.error(f"Analysis section 'overview' failed: {e}")
        results["overview"] = {}

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

Provide a clear, concise answer grounded in the tender document. Use bullet points if listing multiple items. Do not make up information not present in the document."""

    try:
        return provider.chat(prompt, temperature=0.2, max_tokens=1024)
    except Exception as e:
        logger.error(f"answer_question failed: {e}")
        raise
