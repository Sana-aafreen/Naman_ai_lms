"""
AIChat.py    RAG edition (offline, rule-based)

Pipeline
--------
1. Ingest    scan ORIGINAL_SOPS_DIR for *.pdf files
              extract raw text page-by-page with PyPDF2
              split each page into overlapping fixed-size chunks
2. Index     build a TF-IDF matrix over all chunks with scikit-learn
3. Retrieve  cosine-similarity search at query time -> top-K chunks
4. Answer    format retrieved chunks as a grounded, cited response

No LLM, no API keys, no internet required.
Falls back to the built-in DEFAULT_SOPS when no PDFs are found.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from zipfile import ZipFile


# -- optional heavy deps (graceful degradation) ------------------------------
try:
    import pdfplumber  # type: ignore
    _PDF_OK = True
except Exception:
    pdfplumber = None
    _PDF_OK = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    import numpy as np  # type: ignore
    _SKLEARN_OK = True
except Exception:
    _SKLEARN_OK = False

# -- paths --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_KNOWLEDGE_PATH = BASE_DIR / "sop_knowledge.json"
ORIGINAL_SOPS_DIR = BASE_DIR.parent.parent / "Frontend" / "public" / "sops"

# -- chunking config ----------------------------------------------------------
CHUNK_SIZE   = 400   # characters per chunk
CHUNK_OVERLAP = 80   # overlap between consecutive chunks
TOP_K        = 4     # chunks returned per query

# -- stopwords ----------------------------------------------------------------
STOPWORDS = {
    "a","an","and","are","as","at","be","by","do","for","from","how",
    "i","if","in","is","it","me","my","of","on","or","our","the","to",
    "we","what","when","where","with","you","your",
}

# ===========================================================================
#  Data models
# ===========================================================================

@dataclass
class Chunk:
    """A single retrievable passage from a source document."""
    text:     str
    source:   str   # filename stem
    page:     int   # 1-based page number
    chunk_id: int   # sequential index within the document

    @property
    def citation(self) -> str:
        return f"[{self.source}  p.{self.page}  chunk {self.chunk_id}]"


@dataclass
class SOPEntry:
    """Legacy dataclass kept for DEFAULT_SOPS fallback compatibility."""
    department: str
    title:      str
    steps:      List[str]
    keywords:   List[str] = field(default_factory=list)
    escalation: str = ""

    @property
    def searchable_text(self) -> str:
        return " ".join([self.department, self.title,
                         *self.steps, *self.keywords, self.escalation]).lower()


# -- built-in fallback SOPs (used when no PDFs are found) --------------------
DEFAULT_SOPS: List[SOPEntry] = [
    SOPEntry(
        department="Sales",
        title="Inbound Lead Handling",
        steps=[
            "Log the lead in CRM within 5 minutes.",
            "Tag lead priority based on urgency.",
            "Send the first WhatsApp greeting within 15 minutes.",
            "Schedule or complete the qualification call based on priority.",
            "Send the quote and payment link, then follow the standard follow-up cadence.",
        ],
        keywords=["lead", "crm", "quote", "payment", "sales", "whatsapp"],
        escalation="Escalate to the Sales lead if the devotee is high priority or payment is blocked.",
    ),
    SOPEntry(
        department="Operations",
        title="VIP Darshan Day-of Execution",
        steps=[
            "Confirm arrival details, pickup point, and dress code with the devotee.",
            "Reconfirm the darshan slot with the on-ground partner one hour before.",
            "Meet the devotee, verify the booking, and escort them to the sanctum.",
            "Log delays, access issues, or special mobility needs immediately.",
            "Complete the post-darshan handoff and feedback step.",
        ],
        keywords=["vip", "darshan", "escort", "ops", "slot", "temple"],
        escalation="Escalate immediately to Operations if there is a slot conflict, temple access issue, or VIP complaint.",
    ),
    SOPEntry(
        department="Sewa",
        title="Puja Sankalp Confirmation",
        steps=[
            "Schedule the sankalp call in the preferred calling window.",
            "Confirm devotee name, gotra, puja details, and timing.",
            "Ask for phonetic spelling for uncommon names.",
            "Repeat all details back before finalizing the form.",
            "Send the reminder and link 24 hours before the puja.",
        ],
        keywords=["sankalp", "puja", "gotra", "reminder", "sewa"],
        escalation="Escalate to the puja coordination team if timing, priest assignment, or devotee details are unclear.",
    ),
    SOPEntry(
        department="HR",
        title="Leave Request Review",
        steps=[
            "Check the employee's requested dates, reason, and manager details.",
            "Verify there is no conflict with coverage or planned business-critical work.",
            "Confirm the leave balance or policy eligibility if needed.",
            "Approve or reject the leave with clear manager remarks.",
            "Record the final manager decision in the Leaves sheet.",
        ],
        keywords=["leave", "absence", "vacation", "manager approval", "hr"],
        escalation="Escalate to HR leadership if there is a policy exception, sensitive case, or repeated conflict.",
    ),
    SOPEntry(
        department="Marketing",
        title="Campaign Launch Readiness",
        steps=[
            "Confirm campaign objective, audience, and launch owner.",
            "Review creative assets, landing page, and CTA links.",
            "Get compliance or brand approval before publishing.",
            "Schedule launch windows and assign monitoring owners.",
            "Review campaign metrics within the first reporting window.",
        ],
        keywords=["marketing", "campaign", "creative", "landing page", "seo", "launch"],
        escalation="Escalate to the marketing lead if assets are incomplete, links are broken, or approvals are pending.",
    ),
]


# ===========================================================================
#  Text utilities
# ===========================================================================

def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def clean_text(raw: str) -> str:
    """Collapse whitespace and strip non-printable characters."""
    text = re.sub(r"[^\x20-\x7E\n]", " ", raw)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def make_chunks(text: str, source: str, page: int) -> List[Chunk]:
    """Split a page's text into overlapping fixed-size chunks."""
    chunks: List[Chunk] = []
    start = 0
    idx = 1
    while start < len(text):
        end = start + CHUNK_SIZE
        snippet = text[start:end].strip()
        if len(snippet) > 40:                           # skip near-empty slices
            chunks.append(Chunk(text=snippet, source=source, page=page, chunk_id=idx))
            idx += 1
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


# ===========================================================================
#  PDF ingestion
# ===========================================================================

def extract_pdf_chunks(path: Path) -> List[Chunk]:
    """Return all Chunk objects extracted from a single PDF file using pdfplumber."""
    if not _PDF_OK:
        return []

    chunks: List[Chunk] = []

    try:
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                raw = page.extract_text() or ""
                text = clean_text(raw)

                if text:
                    page_chunks = make_chunks(text, source=path.stem, page=page_num)
                    chunks.extend(page_chunks)
                else:
                    print(f"[AIChat] Empty text on page {page_num} of {path.name}", file=sys.stderr)

    except Exception as exc:
        print(f"[AIChat] Warning: could not read {path.name}  {exc}", file=sys.stderr)

    return chunks

# ===========================================================================
#  TF-IDF index
# ===========================================================================

class TFIDFIndex:
    """Thin wrapper around sklearn TfidfVectorizer for chunk retrieval."""

    def __init__(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        self._ready = False

        if not chunks or not _SKLEARN_OK:
            return

        n_docs = len(chunks)
        self._vectorizer = TfidfVectorizer(
            strip_accents="unicode",
            analyzer="word",
            token_pattern=r"[a-zA-Z0-9]{2,}",
            stop_words=list(STOPWORDS),
            ngram_range=(1, 2),         # unigrams + bigrams
            sublinear_tf=True,
            # Avoid min_df > max_df on tiny corpora
            max_df=1.0 if n_docs < 5 else 0.95,
            min_df=1,
        )
        corpus = [c.text for c in chunks]
        self._matrix = self._vectorizer.fit_transform(corpus)
        self._ready = True

    def search(self, query: str, top_k: int = TOP_K) -> List[Tuple[Chunk, float]]:
        if not self._ready:
            return []

        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: List[Tuple[Chunk, float]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.0:
                results.append((self.chunks[idx], score))
        return results


# ===========================================================================
#  Legacy keyword search (fallback when sklearn or PDFs are unavailable)
# ===========================================================================

def load_sops(knowledge_path: Optional[Path] = None) -> List[SOPEntry]:
    path = knowledge_path or DEFAULT_KNOWLEDGE_PATH
    if not path.exists():
        return DEFAULT_SOPS
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = [
            SOPEntry(
                department=item.get("department", "General"),
                title=item.get("title", "Untitled SOP"),
                steps=item.get("steps", []),
                keywords=item.get("keywords", []),
                escalation=item.get("escalation", ""),
            )
            for item in payload
        ]
        return entries or DEFAULT_SOPS
    except Exception:
        return DEFAULT_SOPS


def keyword_search(
    query: str,
    sops: List[SOPEntry],
    department: Optional[str],
    limit: int = 3,
) -> List[Tuple[SOPEntry, float]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    results: List[Tuple[SOPEntry, float]] = []
    req_dept = (department or "").strip().lower()

    for sop in sops:
        sop_tokens = tokenize(sop.searchable_text)
        overlap = len(set(query_tokens) & set(sop_tokens))
        if overlap == 0:
            continue
        density = overlap / max(len(set(query_tokens)), 1)
        dept_bonus = 0.25 if req_dept and sop.department.lower() == req_dept else 0.0
        results.append((sop, overlap + density + dept_bonus))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


# ===========================================================================
#  Agent
# ===========================================================================
def load_all_pdf_chunks(sops_dir: Path) -> List[Chunk]:
    """Scan the sops directory and ingest every PDF found."""
    # Check both the requested dir and the current agents dir for sops
    search_dirs = [sops_dir, Path(__file__).parent]
    
    all_chunks: List[Chunk] = []
    pdf_files: List[Path] = []
    
    for d in search_dirs:
        if d.exists():
            pdf_files.extend(list(d.glob("*.pdf")))
    
    pdf_files = sorted(list(set(pdf_files)))  # uniq and sort

    if not pdf_files:
        return []

    print(f"[AIChat] Indexing {len(pdf_files)} PDF(s) from {[str(d) for d in search_dirs]} ...", file=sys.stderr)

    for pdf_path in pdf_files:
        file_chunks = extract_pdf_chunks(pdf_path)
        all_chunks.extend(file_chunks)
        print(f"  OK  {pdf_path.name}  ->  {len(file_chunks)} chunk(s)", file=sys.stderr)

    print(f"[AIChat] Total chunks indexed: {len(all_chunks)}", file=sys.stderr)
    return all_chunks

class AIChatAgent:
    """
    RAG agent that retrieves grounded answers from indexed PDF SOPs.

    Retrieval priority
    ------------------
    1. TF-IDF over PDF chunks  (when PDFs exist and sklearn is available)
    2. Keyword search over DEFAULT_SOPS / sop_knowledge.json  (fallback)
    """

    def __init__(self, sops_dir: Optional[Path] = None) -> None:
        self._dir = sops_dir or ORIGINAL_SOPS_DIR

        # Try PDF-based RAG first
        self._chunks = load_all_pdf_chunks(self._dir)
        self._index  = TFIDFIndex(self._chunks) if self._chunks else None
        self._mode   = "rag" if (self._index and self._index._ready) else "keyword"

        if self._mode == "keyword":
            self._sops = load_sops()
            print("[AIChat] Running in keyword-search fallback mode.", file=sys.stderr)
        else:
            print(f"[AIChat] Running in RAG mode ({len(self._chunks)} chunks).", file=sys.stderr)

    # -- public interface ----------------------------------------------------

    def search(
        self,
        query: str,
        department: Optional[str] = None,
        limit: int = TOP_K,
    ) -> List[Dict]:
        """Return a list of ranked result dicts (works in both modes)."""
        if self._mode == "rag":
            return self._rag_search(query, limit)
        return self._keyword_search_dicts(query, department, limit)

    def answer(
        self,
        query: str,
        employee_name: str = "",
        department: Optional[str] = None,
    ) -> Dict[str, object]:
        if self._mode == "rag":
            return self._rag_answer(query, employee_name)
        return self._keyword_answer(query, employee_name, department)

    # -- RAG path -----------------------------------------------------------

    def _rag_search(self, query: str, limit: int) -> List[Dict]:
        assert self._index is not None
        hits = self._index.search(query, top_k=limit)
        return [
            {
                "source":     chunk.source,
                "page":       chunk.page,
                "chunk_id":   chunk.chunk_id,
                "score":      round(score, 4),
                "excerpt":    chunk.text[:300],
            }
            for chunk, score in hits
        ]

    def _rag_answer(self, query: str, employee_name: str) -> Dict[str, object]:
        assert self._index is not None
        hits = self._index.search(query, top_k=TOP_K)

        if not hits:
            return self._no_match_response()

        greeting = f"{employee_name}, " if employee_name else ""
        top_chunk, top_score = hits[0]
        confidence = round(min(top_score * 5, 1.0), 2)   # scale 01

        # -- build readable answer ------------------------------------------
        lines: List[str] = [
            f"{greeting}here is what the SOPs say about your question.\n",
        ]

        for rank, (chunk, score) in enumerate(hits, start=1):
            pct = f"{score * 100:.1f}%"
            lines.append(
                f"-- Result {rank} {chunk.citation}  (relevance {pct}) --\n"
                f"{chunk.text}\n"
            )

        # Escalation hint based on top source
        escalation = (
            f"If the above does not fully resolve your issue, "
            f"refer to the full '{top_chunk.source}' document "
            f"or escalate to your department lead."
        )
        lines.append(f"\nEscalation: {escalation}")

        return {
            "answer":     "\n".join(lines),
            "matches":    [
                {
                    "source":  ch.source,
                    "page":    ch.page,
                    "score":   round(sc, 4),
                    "excerpt": ch.text[:150],
                }
                for ch, sc in hits
            ],
            "escalation": escalation,
            "confidence": confidence,
            "mode":       "rag",
        }

    # -- keyword fallback path ----------------------------------------------

    def _keyword_search_dicts(
        self,
        query: str,
        department: Optional[str],
        limit: int,
    ) -> List[Dict]:
        results = keyword_search(query, self._sops, department, limit)
        return [
            {
                "department": sop.department,
                "title":      sop.title,
                "score":      round(score, 2),
            }
            for sop, score in results
        ]

    def _keyword_answer(
        self,
        query: str,
        employee_name: str,
        department: Optional[str],
    ) -> Dict[str, object]:
        matches = keyword_search(query, self._sops, department, limit=3)

        if not matches:
            return self._no_match_response()

        top_sop, top_score = matches[0]
        greeting = f"{employee_name}, " if employee_name else ""
        opening = (
            f"{greeting}the best SOP match is '{top_sop.title}' "
            f"from {top_sop.department}. "
            "Here is the most practical path to follow right now:"
        )
        numbered = [
            f"{i + 1}. {step}"
            for i, step in enumerate(top_sop.steps[:5])
        ]
        escalation = top_sop.escalation or "Escalate to your manager if this does not resolve the issue."

        return {
            "answer":     "\n".join([opening, *numbered, f"Escalation: {escalation}"]),
            "matches":    [
                {"department": s.department, "title": s.title, "score": round(sc, 2)}
                for s, sc in matches
            ],
            "escalation": escalation,
            "confidence": round(min(top_score / 5, 1.0), 2),
            "mode":       "keyword",
        }

    # -- shared helpers -----------------------------------------------------

    @staticmethod
    def _no_match_response() -> Dict[str, object]:
        return {
            "answer": (
                "I could not find a strong match for that question in the SOPs. "
                "Please rephrase with the department, task, and specific blocker, "
                "or escalate to your manager for a manual review."
            ),
            "matches":    [],
            "escalation": "Escalate to your department lead if the task is time-sensitive.",
            "confidence": 0.0,
            "mode":       "none",
        }


# ===========================================================================
#  Entry points  (unchanged public API)
# ===========================================================================

def run_json_mode() -> int:
    agent = AIChatAgent()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"Invalid JSON input: {exc}"}))
        return 1

    query         = str(payload.get("query", "")).strip()
    department    = payload.get("department")
    employee_name = str(payload.get("employee_name", "")).strip()

    if not query:
        print(json.dumps({"error": "Missing required field: query"}))
        return 1

    result = agent.answer(query=query, employee_name=employee_name, department=department)
    print(json.dumps(result, indent=2))
    return 0


def run_cli() -> int:
    agent = AIChatAgent()
    mode_label = "RAG (PDF)" if agent._mode == "rag" else "keyword fallback"
    print(f"Naman AIChat is ready  [{mode_label}].  Type 'exit' to quit.")
    print("Optional format: department | your question\n")

    while True:
        try:
            raw = input("You: ").strip()
        except EOFError:
            print()
            return 0

        if not raw:
            continue
        if raw.lower() in {"exit", "quit"}:
            return 0

        department, query = None, raw
        if "|" in raw:
            left, right = raw.split("|", 1)
            department = left.strip() or None
            query = right.strip()

        result = agent.answer(query=query, department=department)
        print(f"\nAIChat  [confidence {result.get('confidence', 0):.0%}]:\n")
        print(result["answer"])
        print()


if __name__ == "__main__":
    if "--json" in sys.argv:
        raise SystemExit(run_json_mode())
    raise SystemExit(run_cli())