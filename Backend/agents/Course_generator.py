# -*- coding: utf-8 -*-
"""
course_generator.py  NamanDarshan Course Generator v5.1
=========================================================
NEW in v5
---------
* Multi-file HTML output per course:
    - {dept}-index.html          -> course dashboard, module cards, overall progress
    - {dept}-module-01.html ...    -> individual module pages (linked from index)
    - {dept}-final-exam.html     -> dedicated final exam page
* All pages are standalone  can be opened directly from filesystem or served as static files
* localStorage progress sync across all pages (no backend required for progress display)
* Growth tracker auto-POST on quiz pass -> /api/update-progress AND /api/generated-courses/progress
* Richer AI prompt: 5+ lessons per module, case studies, pro tips, 8-10 scenario Qs
* PDF is download-only (pass generate_pdf=True to generate_course_package())
* HtmlCourseIndexWriter    renders course dashboard HTML
* HtmlModulePageWriter     renders individual module page HTML
* HtmlFinalExamWriter      renders final exam page HTML

DB Integration (v5.1):
* All HTML rendered IN MEMORY, saved to MongoDB immediately
* Files written to disk ONLY when user clicks Download
* course_database_mongo.CourseDatabase handles all persistence
* /api/generated-courses/* endpoints serve HTML from DB

Dual AI fallback chain (unchanged):
    Groq key 2  ->  Gemini pool  ->  static / rule-based fallback
"""

from __future__ import annotations

import importlib
import importlib.util
import itertools
import json
import os
import re
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen
import sys
sys.dont_write_bytecode = True

try:
    import requests
except Exception:
    requests = None

try:
    from fpdf import FPDF
except Exception:
    FPDF = None

bs4_module = importlib.import_module("bs4") if importlib.util.find_spec("bs4") else None
BeautifulSoup = getattr(bs4_module, "BeautifulSoup", None)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from agents.AIChat import ORIGINAL_SOPS_DIR, load_sops
except Exception:
    ORIGINAL_SOPS_DIR = Path("sops/original")
    def load_sops():
        return []

_course_db_instance = None

def get_course_db():
    global _course_db_instance
    if _course_db_instance is not None:
        return _course_db_instance
    try:
        try:
            from .course_database_mongo import CourseDatabase as _CourseDatabase # type: ignore
        except Exception:
            try:
                from course_database_mongo import CourseDatabase as _CourseDatabase # type: ignore
            except Exception:
                from Course_database_mongo import CourseDatabase as _CourseDatabase # type: ignore
        _course_db_instance = _CourseDatabase()
        _course_db_instance.init_schema()
        return _course_db_instance
    except Exception as _db_err:
        safe_err = str(_db_err).encode('ascii', 'ignore').decode('ascii')
        print(f"  [CourseGen] Warning: DB not available ({safe_err}). Falling back to disk-only mode.")
        return None


# ============================================================================
# CONSTANTS
# ============================================================================

BASE_DIR      = Path(__file__).resolve().parent
OUTPUT_DIR    = BASE_DIR.parent / "data" / "generated_courses"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

GROQ_API_KEY_2       = os.getenv("GROQ_API_KEY_2", "").strip()
GROQ_API_URL         = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL_2 = os.getenv("GROQ_MODEL_2", "llama-3.3-70b-versatile")

_gem_raw             = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
GEMINI_KEYS          = _gem_raw
GEMINI_API_BASE      = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
_gem_cycle           = itertools.cycle(GEMINI_KEYS) if GEMINI_KEYS else iter([])

def _next_gemini_key() -> str:
    try:
        return next(_gem_cycle)
    except StopIteration:
        return ""

DEFAULT_SITE_ROOT        = os.getenv("COURSE_SOURCE_SITE", "https://namandarshan.com")
DEFAULT_TIMEOUT          = int(os.getenv("COURSE_GENERATOR_TIMEOUT", "30"))
MCQ_QUESTIONS_PER_MODULE = int(os.getenv("MCQ_QUESTIONS_PER_MODULE", "8"))
LESSON_EXPLANATION_WORDS = int(os.getenv("LESSON_EXPLANATION_WORDS", "600"))

# -- Shared CSS design tokens -------------------------------------------------
SHARED_CSS_VARS = """
:root {
  --saffron:      #F97316;
  --saffron-dark: #C2410C;
  --saffron-lite: #FFF7ED;
  --saffron-mid:  #FDBA74;
  --cream:        #FFFBF5;
  --warm-dark:    #1C1917;
  --warm-mid:     #44403C;
  --warm-gray:    #78716C;
  --warm-light:   #F5F0E8;
  --border:       #E7DDD0;
  --white:        #FFFFFF;
  --green:        #16A34A;
  --green-lite:   #DCFCE7;
  --red:          #DC2626;
  --red-lite:     #FEE2E2;
  --blue:         #2563EB;
  --blue-lite:    #EFF6FF;
  --amber:        #F59E0B;
  --amber-lite:   #FFFBEB;
  --shadow-sm:    0 1px 3px rgba(0,0,0,.08);
  --shadow-md:    0 4px 16px rgba(0,0,0,.12);
  --shadow-lg:    0 12px 40px rgba(0,0,0,.16);
  --radius:       16px;
  --radius-sm:    10px;
  --radius-xs:    6px;
}"""

SHARED_BASE_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 16px; scroll-behavior: smooth; }
body {
  font-family: 'Nunito', sans-serif;
  background: var(--cream);
  color: var(--warm-dark);
  line-height: 1.75;
  min-height: 100vh;
}
h1,h2,h3,h4,h5 { font-family: 'Yeseva One', serif; line-height: 1.3; }
a { color: var(--saffron); text-decoration: none; }
a:hover { text-decoration: underline; }
p { margin-bottom: 1rem; }
p:last-child { margin-bottom: 0; }
ul,ol { padding-left: 1.4rem; }
li { margin-bottom: .4rem; }

/* NAVBAR */
.navbar {
  position: sticky; top: 0; z-index: 200;
  background: var(--warm-dark);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 2rem; height: 60px;
  box-shadow: 0 2px 12px rgba(0,0,0,.25);
}
.navbar-brand { display: flex; align-items: center; gap: .75rem; }
.navbar-logo {
  width: 34px; height: 34px; border-radius: 8px;
  background: linear-gradient(135deg, var(--saffron), var(--saffron-dark));
  display: flex; align-items: center; justify-content: center;
  color: white; font-family: 'Yeseva One',serif; font-size: 17px;
}
.navbar-title { font-family:'Yeseva One',serif; font-size:1.05rem; color:white; }
.navbar-title span { color: var(--saffron-mid); }
.navbar-links { display:flex; align-items:center; gap:1rem; }
.navbar-links a {
  font-size:.82rem; font-weight:700; color:rgba(255,255,255,.65);
  padding:.35rem .7rem; border-radius:6px; transition:all .15s;
}
.navbar-links a:hover, .navbar-links a.active {
  color:white; background:rgba(255,255,255,.12); text-decoration:none;
}
.navbar-badge {
  font-size:.72rem; font-weight:800; letter-spacing:.06em;
  padding:.3rem .8rem; border-radius:20px;
  background:rgba(249,115,22,.18); color:var(--saffron-mid);
  border:1px solid rgba(249,115,22,.3);
}
.progress-strip { height:3px; background:rgba(255,255,255,.1); }
.progress-fill {
  height:100%;
  background:linear-gradient(90deg,var(--saffron),var(--amber));
  transition:width .5s ease;
}

/* BUTTONS */
.btn {
  display:inline-flex; align-items:center; gap:.4rem;
  padding:.7rem 1.5rem; border-radius:var(--radius-sm);
  font-family:'Nunito',sans-serif; font-size:.9rem; font-weight:800;
  border:none; cursor:pointer; transition:all .18s; text-decoration:none;
}
.btn-primary { background:var(--saffron); color:white; }
.btn-primary:hover { background:var(--saffron-dark); transform:translateY(-1px); box-shadow:var(--shadow-md); text-decoration:none; color:white; }
.btn-ghost { background:transparent; color:var(--warm-gray); border:1.5px solid var(--border); }
.btn-ghost:hover { border-color:var(--saffron); color:var(--saffron); text-decoration:none; }
.btn-dark { background:var(--warm-dark); color:white; }
.btn-dark:hover { background:#2C2420; transform:translateY(-1px); text-decoration:none; color:white; }
.btn-green { background:var(--green); color:white; }
.btn-green:hover { background:#15803D; transform:translateY(-1px); text-decoration:none; color:white; }
.btn:disabled { opacity:.5; cursor:not-allowed; transform:none !important; }

/* CHIPS */
.chip {
  display:inline-flex; align-items:center; gap:.3rem;
  font-size:.75rem; font-weight:700;
  padding:.3rem .75rem; border-radius:20px;
  background:var(--warm-light); color:var(--warm-mid);
}
.chip-saffron { background:var(--saffron-lite); color:var(--saffron-dark); }
.chip-green { background:var(--green-lite); color:var(--green); }
.chip-blue { background:var(--blue-lite); color:var(--blue); }

/* SECTION CARD */
.s-card {
  background:var(--white); border:1px solid var(--border);
  border-radius:var(--radius); padding:2rem;
  margin-bottom:1.75rem; box-shadow:var(--shadow-sm);
}
.s-card-title {
  font-size:1.1rem; display:flex; align-items:center; gap:.6rem;
  padding-bottom:.85rem; margin-bottom:1.25rem;
  border-bottom:2px solid var(--warm-light);
}
.s-card-icon {
  width:32px; height:32px; border-radius:8px;
  background:var(--saffron-lite); color:var(--saffron);
  display:flex; align-items:center; justify-content:center;
  font-size:1rem; flex-shrink:0;
}

/* QUIZ */
.quiz-wrap { background:var(--white); border:2px solid var(--saffron); border-radius:var(--radius); padding:2rem; margin-bottom:1.75rem; }
.quiz-q { margin-bottom:1.75rem; }
.quiz-q-label { font-size:.7rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; color:var(--saffron); margin-bottom:.4rem; }
.quiz-q-text { font-weight:700; font-size:.975rem; margin-bottom:.85rem; line-height:1.5; color:var(--warm-dark); }
.quiz-opts { display:flex; flex-direction:column; gap:.5rem; }
.quiz-opt {
  display:flex; align-items:center; gap:.75rem;
  padding:.75rem 1rem; border:1.5px solid var(--border);
  border-radius:var(--radius-sm); cursor:pointer;
  font-family:'Nunito',sans-serif; font-size:.9rem;
  background:white; transition:all .15s; text-align:left;
}
.quiz-opt .ol {
  width:28px; height:28px; border-radius:6px;
  background:var(--warm-light); color:var(--warm-gray);
  font-size:.78rem; font-weight:900;
  display:flex; align-items:center; justify-content:center;
  flex-shrink:0; transition:all .15s;
}
.quiz-opt:hover { border-color:var(--saffron); background:var(--saffron-lite); }
.quiz-opt:hover .ol { background:var(--saffron); color:white; }
.quiz-opt.sel { border-color:var(--saffron); background:var(--saffron-lite); }
.quiz-opt.sel .ol { background:var(--saffron); color:white; }
.quiz-opt.correct { border-color:var(--green); background:var(--green-lite); pointer-events:none; }
.quiz-opt.correct .ol { background:var(--green); color:white; }
.quiz-opt.wrong { border-color:var(--red); background:var(--red-lite); pointer-events:none; }
.quiz-opt.wrong .ol { background:var(--red); color:white; }
.quiz-opt.dis { pointer-events:none; opacity:.65; }
.quiz-exp { display:none; margin-top:.6rem; padding:.75rem 1rem; background:var(--blue-lite); border-left:3px solid var(--blue); border-radius:0 var(--radius-xs) var(--radius-xs) 0; font-size:.85rem; color:#1D4ED8; line-height:1.55; }
.quiz-result { text-align:center; padding:2.5rem; border-radius:var(--radius-sm); background:var(--saffron-lite); border:1px solid var(--saffron-mid); display:none; margin-top:1.5rem; }
.quiz-result .rs { font-size:3.5rem; font-family:'Yeseva One',serif; color:var(--saffron); line-height:1; }
.quiz-result .rm { color:var(--warm-gray); margin:.5rem 0 1rem; font-size:.95rem; }
.result-badge { display:inline-block; font-size:.85rem; font-weight:700; padding:.4rem 1.2rem; border-radius:20px; }
.rb-pass { background:var(--green-lite); color:var(--green); }
.rb-fail { background:var(--red-lite); color:var(--red); }

@media (max-width:600px) {
  .navbar { padding:0 1rem; }
  .navbar-links { display:none; }
}"""

# -- Enhanced AI content prompt ------------------------------------------------
HTML_COURSE_CONTENT_SYSTEM = """\
You are a senior curriculum designer for NamanDarshan  a premium spiritual pilgrimage \
and puja services platform based in India. Generate a complete, richly detailed, \
professional training course.

Return ONLY valid JSON  no markdown fences, no preamble, no explanation outside JSON.

REQUIRED TOP-LEVEL KEYS:
  title, description, duration, level, audience, modules (array), final_exam (array)

EACH MODULE OBJECT must have:
  module_id  (e.g. "mod_1")
  title
  duration   (e.g. "75 min")
  content: {
    introduction        220-260 words, rich motivating prose specific to NamanDarshan
    why_it_matters      130-160 words, real operational impact
    learning_objectives  array of 5-6 specific measurable strings
    lessons: [
      {
        title
        body            650-800 words, 4-5 paragraphs of educational prose (NO bullet lists)
        example         160-200 words, specific NamanDarshan scenario
        key_points      array of 5-6 concise strings
        pro_tip         60-80 words expert insight
      }
    ]   (MINIMUM 5 lessons per module)
    do                  array of 5 best-practice strings
    dont                array of 5 common-mistake strings
    case_study: {
      title
      scenario          220-260 words, realistic NamanDarshan operational scenario
      outcome           90-110 words, result and learning
    }
    summary             160-190 words
    knowledge_check     array of 3-4 { question, answer } objects
  }
  quiz: [
    { id, question, options (4 strings), correct_answer, correct_index (int 0-3), explanation (70-90 words) }
  ]   (8-10 scenario-based questions  NOT trivial recall)

final_exam: 12-15 questions, same shape as quiz items, drawing from ALL modules.

RULES:
- MINIMUM 5 lessons per module. MINIMUM 4 modules.
- Lesson bodies MUST be flowing prose  never bullet points inside body text.
- Quiz/exam questions MUST test application and judgment, not mere memorization.
- Every example, case study, scenario MUST reference real NamanDarshan services:
  VIP Darshan, Yatra packages, Online Puja, Live Darshan, Prasad delivery,
  Temple booking, Pandit services, pilgrimage coordination.
- Do NOT generate lorem ipsum. Every sentence must be purposeful and educational.
- Output ONLY the JSON object. No markdown. No preamble. No explanation."""


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SourceDocument:
    source_type: str
    title: str
    url: str
    content: str

@dataclass
class LessonExplanation:
    lesson_title: str
    body: str
    key_points: list[str]
    real_world_example: str
    do_and_dont: dict

@dataclass
class ModuleBooklet:
    module_id: str
    module_index: int
    module_title: str
    department: str
    duration: str
    introduction: str
    why_it_matters: str
    goals: list[str]
    lesson_explanations: list[LessonExplanation]
    practice_activities: list[str]
    sop_checkpoints: list[str]
    module_recap: str
    whats_next: str
    generated_by: str

@dataclass
class MCQQuestion:
    id: str
    question: str
    options: list[str]
    correct_option_index: int
    explanation: str

@dataclass
class ModuleMCQ:
    module_title: str
    module_index: int
    questions: list[MCQQuestion]
    generated_by: str

@dataclass
class GeneratedCourse:
    department: str
    generated_at: str
    title: str
    summary: str
    audience: str
    prerequisites: list[str]
    learning_objectives: list[str]
    daily_workflows: list[str]
    modules: list[dict[str, Any]]
    assessments: list[str]
    quiz_questions: list[dict[str, Any]]
    manager_review_checklist: list[str]
    youtube_links: list[dict[str, str]]
    source_notes: list[str]
    raw_sources: list[SourceDocument]
    module_mcqs: list[ModuleMCQ] = field(default_factory=list)
    module_booklets: list[ModuleBooklet] = field(default_factory=list)


# ============================================================================
# PROGRESS TRACKER  (legacy JSON-file tracker  kept for backward compat)
# ============================================================================

class ProgressTracker:
    def __init__(self, path: Path = PROGRESS_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {}

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def record_assessment(self, learner_id, module_id, module_title,
                          department, score, total, answers) -> dict:
        data = self._load()
        if learner_id not in data:
            data[learner_id] = {"learner_id": learner_id, "modules": {}, "updated_at": ""}
        pct = round((score / total) * 100) if total else 0
        data[learner_id]["modules"][module_id] = {
            "module_id": module_id, "module_title": module_title,
            "department": department, "score": score, "total": total,
            "percentage": pct, "passed": pct >= 70,
            "completed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "answers": answers,
        }
        data[learner_id]["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        self._save(data)
        return data[learner_id]

    def get_progress(self, learner_id: str) -> dict:
        return self._load().get(learner_id, {})

    def get_all_progress(self) -> dict:
        return self._load()


# ============================================================================
# UTILITY HELPERS
# ============================================================================

def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "general"

def _strip_html(value: str) -> str:
    value = re.sub(r"<script.*?>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?>.*?</style>",   " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return text

def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (CourseGeneratorBot/5.0)", "Accept-Language": "en-US,en;q=0.9"}
    if requests is not None:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.encoding or "utf-8"
        return resp.text
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def _extract_links(base_url: str, html: str) -> list[str]:
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        return [urljoin(base_url, a.get("href", "").strip())
                for a in soup.find_all("a", href=True) if a.get("href", "").strip()]
    return [urljoin(base_url, h) for h in re.findall(r'href=["\']([^"\']+)["\']', html)]

def _extract_title(base_url: str, html: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    return m.group(1).strip() if m else base_url

def _visible_text(html: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for el in soup(["script", "style", "noscript"]):
            el.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
    return _strip_html(html)

def _dedupe_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        u = u.strip()
        if u and u not in seen:
            seen.add(u)
            result.append(u)
    return result

def _score_url(url: str, keywords: list[str]) -> int:
    low = url.lower()
    score = sum(3 for kw in keywords if kw in low)
    if any(w in low for w in ("blog", "course", "training")):
        score += 2
    return score

def _ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(i).strip() for i in value if str(i).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

def _ensure_link_list(value: Any) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                url   = str(item.get("url",   "")).strip()
                if title or url:
                    links.append({"title": title or "Resource", "url": url})
            elif isinstance(item, str) and item.strip():
                links.append({"title": item.strip(), "url": item.strip()})
    elif isinstance(value, str) and value.strip():
        links.append({"title": value.strip(), "url": value.strip()})
    return links

def _ensure_module_list(value: Any) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return modules
    for idx, item in enumerate(value, 1):
        if isinstance(item, dict):
            modules.append({
                "title":           str(item.get("title", f"Module {idx}")).strip(),
                "duration":        str(item.get("duration", "60 min")).strip() or "60 min",
                "goals":           _ensure_string_list(item.get("goals")),
                "lessons":         _ensure_string_list(item.get("lessons")),
                "practice":        _ensure_string_list(item.get("practice")),
                "references":      _ensure_string_list(item.get("references")),
                "sop_checkpoints": _ensure_string_list(item.get("sop_checkpoints")),
                "video_links":     _ensure_link_list(item.get("video_links")),
            })
        elif isinstance(item, str) and item.strip():
            modules.append({
                "title": item.strip(), "duration": "60 min",
                "goals": [], "lessons": [item.strip()],
                "practice": [], "references": [],
                "sop_checkpoints": [], "video_links": [],
            })
    return modules

def _ensure_quiz_list(value: Any) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return questions
    for idx, item in enumerate(value, 1):
        if isinstance(item, dict):
            opts = _ensure_string_list(item.get("options"))
            if len(opts) < 2:
                opts = ["Option A", "Option B", "Option C", "Option D"]
            try:
                correct = int(item.get("correctOptionIndex", item.get("correct_index", 0)))
            except (TypeError, ValueError):
                correct = 0
            questions.append({
                "id":                 str(item.get("id", f"q-{idx}")),
                "question":           str(item.get("question", f"Question {idx}")).strip(),
                "options":            opts,
                "correctOptionIndex": max(0, min(correct, len(opts) - 1)),
                "explanation":        str(item.get("explanation", "")).strip(),
            })
    return questions

def _esc_html(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

def _esc_js(s: str) -> str:
    return (str(s)
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("'", "\\'"))

def _prose_to_html(text: str) -> str:
    """Convert newline-separated prose paragraphs to <p> tags."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    return "".join(f"<p>{_esc_html(p)}</p>" for p in paras) if paras else f"<p>{_esc_html(text)}</p>"


# ============================================================================
# HTML COURSE INDEX WRITER
# ============================================================================

class HtmlCourseIndexWriter:
    """Generates the main course landing page (dashboard)."""

    INDEX_CSS = """
.hero {
  background: linear-gradient(135deg, var(--warm-dark) 0%, #3C2410 60%, #2A1A0A 100%);
  padding: 3.5rem 2.5rem; position: relative; overflow: hidden;
}
.hero::before {
  content: ""; position: absolute; right: 3rem; top: 50%; transform: translateY(-50%);
  font-family: 'Yeseva One',serif; font-size: 14rem; color: rgba(249,115,22,.06);
  line-height: 1; pointer-events: none;
}
.hero-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 2rem; flex-wrap: wrap; }
.hero-left { flex: 1; min-width: 280px; }
.hero-badge {
  display: inline-block; margin-bottom: 1rem;
  background: rgba(249,115,22,.2); color: var(--saffron-mid);
  border: 1px solid rgba(249,115,22,.3);
  font-size: .72rem; font-weight: 900; letter-spacing: .1em; text-transform: uppercase;
  padding: .35rem .9rem; border-radius: 20px;
}
.hero h1 { font-size: 2.4rem; color: white; margin-bottom: .75rem; line-height: 1.2; }
.hero-desc { color: rgba(255,255,255,.65); font-size: .975rem; max-width: 560px; margin-bottom: 1.5rem; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 1.25rem; }
.hero-meta-item { display: flex; align-items: center; gap: .4rem; font-size: .85rem; color: rgba(255,255,255,.5); }
.hero-meta-item strong { color: rgba(255,255,255,.85); }
.hero-right { flex-shrink: 0; }
.progress-ring-wrap {
  width: 140px; height: 140px; position: relative;
  display: flex; align-items: center; justify-content: center;
}
.progress-ring-wrap svg { position: absolute; inset: 0; transform: rotate(-90deg); }
.progress-ring-bg { fill: none; stroke: rgba(255,255,255,.1); stroke-width: 8; }
.progress-ring-fill { fill: none; stroke: var(--saffron); stroke-width: 8; stroke-linecap: round; transition: stroke-dashoffset .6s ease; }
.progress-ring-text { text-align: center; z-index: 1; }
.progress-ring-text .pct { font-family:'Yeseva One',serif; font-size: 2rem; color: white; line-height: 1; }
.progress-ring-text .plabel { font-size: .72rem; color: rgba(255,255,255,.5); font-weight: 700; margin-top: .2rem; }
.page-body { max-width: 1200px; margin: 0 auto; padding: 2.5rem 1.5rem; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 1.5rem; }
.section-head h2 { font-size: 1.5rem; }
.section-head span { font-size: .82rem; color: var(--warm-gray); font-weight: 700; }
.modules-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; margin-bottom: 3rem; }
.mod-card {
  background: var(--white); border: 1.5px solid var(--border);
  border-radius: var(--radius); padding: 1.75rem;
  display: flex; flex-direction: column; gap: .75rem;
  cursor: pointer; transition: all .22s; position: relative; overflow: hidden;
  text-decoration: none; color: inherit;
}
.mod-card::after {
  content: ""; position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, var(--saffron), var(--amber));
  transform: scaleX(0); transform-origin: left; transition: transform .25s;
}
.mod-card:hover { box-shadow: var(--shadow-md); transform: translateY(-3px); border-color: var(--saffron-mid); text-decoration: none; }
.mod-card:hover::after { transform: scaleX(1); }
.mod-card.done { border-color: var(--green); }
.mod-card.done::after { transform: scaleX(1); background: var(--green); }
.mod-card-num {
  width: 44px; height: 44px; border-radius: 12px;
  background: var(--saffron-lite); color: var(--saffron);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Yeseva One',serif; font-size: 1.15rem;
}
.mod-card.done .mod-card-num { background: var(--green-lite); color: var(--green); }
.mod-card h3 { font-size: 1rem; color: var(--warm-dark); line-height: 1.35; }
.mod-card p { font-size: .82rem; color: var(--warm-gray); flex: 1; line-height: 1.55; }
.mod-card-footer { display: flex; align-items: center; justify-content: space-between; margin-top: .25rem; }
.mod-card-footer .meta { font-size: .75rem; color: var(--warm-gray); display: flex; gap: .85rem; }
.mod-card-footer .cta {
  font-size: .78rem; font-weight: 800; padding: .3rem .9rem;
  border-radius: 20px; background: var(--saffron-lite); color: var(--saffron);
  transition: all .15s;
}
.mod-card:hover .cta { background: var(--saffron); color: white; }
.mod-card.done .cta { background: var(--green-lite); color: var(--green); }
.status-dot {
  position: absolute; top: 1.25rem; right: 1.25rem;
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--border);
}
.mod-card.done .status-dot { background: var(--green); box-shadow: 0 0 0 3px var(--green-lite); }
.exam-banner {
  background: linear-gradient(135deg, var(--warm-dark), #3C2410);
  border-radius: var(--radius); padding: 2.5rem; text-align: center;
  color: white; position: relative; overflow: hidden; margin-bottom: 2rem;
}
.exam-banner::before {
  content: ""; position: absolute; left: 2.5rem; top: 50%; transform: translateY(-50%);
  font-size: 4rem; opacity: .15;
}
.exam-banner h2 { color: white; font-size: 1.75rem; margin-bottom: .5rem; }
.exam-banner p { color: rgba(255,255,255,.6); max-width: 460px; margin: 0 auto 1.5rem; }
@media (max-width:900px) {
  .hero { padding: 2rem 1.25rem; }
  .hero h1 { font-size: 1.75rem; }
  .hero-right { display: none; }
  .modules-grid { grid-template-columns: 1fr; }
}"""

    def write(self, course_json: dict, module_filenames: list[str], exam_filename: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render(course_json, module_filenames, exam_filename)
        out_path.write_text(html, encoding="utf-8")
        return out_path

    def _render(self, c: dict, module_filenames: list[str], exam_filename: str) -> str:
        title       = _esc_html(c.get("title", "Course"))
        description = _esc_html(c.get("description", ""))
        duration    = _esc_html(c.get("duration", ""))
        level       = _esc_html(c.get("level", ""))
        audience    = _esc_html(c.get("audience", ""))
        dept        = _esc_html(c.get("department", ""))
        modules     = c.get("modules", [])
        slug        = _esc_js(c.get("slug", _slugify(c.get("department", "course"))))
        db_id       = str(c.get("db_course_id", ""))          # always str
        n           = len(modules)
        cards_html  = self._render_module_cards(modules, module_filenames, slug, db_id)
        ring_circ   = 2 * 3.14159 * 54

        dl_buttons = ""
        if db_id:
            dl_buttons = f"""
  <div style="margin-top:2rem;">
    <div style="font-size:.72rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.4);margin-bottom:.75rem;">Download Course Files</div>
    <div style="display:flex;gap:.6rem;flex-wrap:wrap;">
      <a href="/api/generated-courses/download/{db_id}/index?as_file=true" download class="btn btn-ghost" style="color:rgba(255,255,255,.7);border-color:rgba(255,255,255,.2);font-size:.8rem;padding:.5rem 1rem;"> Index</a>
      <a href="/api/generated-courses/download/{db_id}/exam?as_file=true" download class="btn btn-ghost" style="color:rgba(255,255,255,.7);border-color:rgba(255,255,255,.2);font-size:.8rem;padding:.5rem 1rem;"> Final Exam</a>
    </div>
  </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}  NamanDarshan LMS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Yeseva+One&family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
{SHARED_CSS_VARS}
{SHARED_BASE_CSS}
{self.INDEX_CSS}
</style>
</head>
<body>

<nav class="navbar">
  <div class="navbar-brand">
    <div class="navbar-logo"></div>
    <span class="navbar-title">Naman<span>LMS</span></span>
  </div>
  <div class="navbar-links">
    <a href="#" class="active">Home</a>
    <a href="/api/generated-courses/download/{db_id}/module/1">Modules</a>
    <a href="/api/generated-courses/download/{db_id}/exam">Final Exam</a>
  </div>
  {f'<span class="navbar-badge">{dept}</span>' if dept else ''}
</nav>

<div class="progress-strip">
  <div class="progress-fill" id="global-bar" style="width:0%"></div>
</div>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-left">
      <div class="hero-badge">{dept + " Department" if dept else "NamanDarshan LMS"}</div>
      <h1>{title}</h1>
      <p class="hero-desc">{description}</p>
      <div class="hero-meta">
        <div class="hero-meta-item"> <strong>{duration}</strong></div>
        <div class="hero-meta-item"> <strong>{level}</strong></div>
        <div class="hero-meta-item"> <strong>{audience}</strong></div>
        <div class="hero-meta-item"> <strong>{n} Modules</strong></div>
      </div>
      {dl_buttons}
    </div>
    <div class="hero-right">
      <div class="progress-ring-wrap">
        <svg viewBox="0 0 120 120" width="140" height="140">
          <circle class="progress-ring-bg" cx="60" cy="60" r="54"/>
          <circle class="progress-ring-fill" id="ring-fill" cx="60" cy="60" r="54"
            stroke-dasharray="{ring_circ:.1f}"
            stroke-dashoffset="{ring_circ:.1f}"/>
        </svg>
        <div class="progress-ring-text">
          <div class="pct" id="ring-pct">0%</div>
          <div class="plabel">Complete</div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="page-body">
  <div class="section-head">
    <h2>Course Modules</h2>
    <span id="done-count">0 of {n} completed</span>
  </div>
  <div class="modules-grid">
    {cards_html}
  </div>
  <div class="exam-banner">
    <h2>Ready for the Final Exam?</h2>
    <p>Complete all {n} modules and test your knowledge across the full course. You need 70% to pass.</p>
    <a href="/api/generated-courses/download/{db_id}/exam" class="btn btn-primary">Take Final Exam </a>
  </div>
</div>

<script>
const COURSE_SLUG  = '{slug}';
const TOTAL_MODS   = {n};
const COURSE_DB_ID = '{db_id}';

function loadProgress() {{
  let done = 0;
  for (let i = 1; i <= TOTAL_MODS; i++) {{
    const key = `nd_${{COURSE_SLUG}}_mod${{i}}`;
    try {{
      const data = JSON.parse(localStorage.getItem(key) || 'null');
      if (data && data.passed) {{
        done++;
        const card = document.getElementById('mod-card-' + i);
        if (card) card.classList.add('done');
        const cta = document.getElementById('cta-' + i);
        if (cta) cta.textContent = '[OK] Review';
      }}
    }} catch(e) {{}}
  }}
  const pct = TOTAL_MODS > 0 ? Math.round((done / TOTAL_MODS) * 100) : 0;
  document.getElementById('ring-pct').textContent = pct + '%';
  document.getElementById('done-count').textContent = done + ' of ' + TOTAL_MODS + ' completed';
  document.getElementById('global-bar').style.width = pct + '%';
  const circ = {ring_circ:.1f};
  const fill  = document.getElementById('ring-fill');
  if (fill) fill.style.strokeDashoffset = circ - (circ * pct / 100);
}}

document.addEventListener('DOMContentLoaded', loadProgress);
</script>
</body>
</html>"""

    def _render_module_cards(self, modules: list, filenames: list[str], slug: str, db_id: str) -> str:
        parts = []
        for i, m in enumerate(modules):
            idx   = i + 1
            href  = (f"/api/generated-courses/download/{db_id}/module/{idx}"
                     if db_id else f"./{filenames[i] if i < len(filenames) else '#'}")
            title = _esc_html(m.get("title", f"Module {idx}"))
            dur   = _esc_html(m.get("duration", ""))
            cnt   = m.get("content", {})
            intro = _esc_html((cnt.get("introduction", "") or "")[:120])
            if intro: intro += "..."
            nless = len(cnt.get("lessons", []))
            nqz   = len(m.get("quiz", []))
            parts.append(f"""<a href="{href}" class="mod-card" id="mod-card-{idx}" style="text-decoration:none;">
  <div class="status-dot" id="dot-{idx}"></div>
  <div class="mod-card-num">{idx}</div>
  <h3>{title}</h3>
  <p>{intro}</p>
  <div class="mod-card-footer">
    <div class="meta">
      <span> {dur}</span>
      <span> {nless} lessons</span>
      <span> {nqz} Qs</span>
    </div>
    <span class="cta" id="cta-{idx}">Start -></span>
  </div>
</a>""")
        return "\n".join(parts)


# ============================================================================
# HTML MODULE PAGE WRITER
# ============================================================================

class HtmlModulePageWriter:
    MODULE_CSS = """
.lms-wrap { display:flex; max-width:1200px; margin:0 auto; padding:2rem 1.5rem; gap:2rem; }
.mod-sidebar {
  width:260px; flex-shrink:0;
  position:sticky; top:75px; align-self:flex-start;
  max-height:calc(100vh - 90px); overflow-y:auto;
}
.mod-sidebar::-webkit-scrollbar { width:4px; }
.mod-sidebar::-webkit-scrollbar-thumb { background:var(--border); border-radius:4px; }
.sidebar-section { margin-bottom:1.5rem; }
.sidebar-label {
  font-size:.65rem; font-weight:900; letter-spacing:.1em;
  text-transform:uppercase; color:var(--warm-gray);
  padding:0 .5rem .6rem; display:block;
}
.sidebar-lessons { list-style:none; padding:0; display:flex; flex-direction:column; gap:.2rem; }
.sidebar-lessons li a {
  display:flex; align-items:center; gap:.6rem;
  padding:.55rem .75rem; border-radius:var(--radius-xs);
  font-size:.82rem; font-weight:700; color:var(--warm-mid);
  transition:all .15s; text-decoration:none;
}
.sidebar-lessons li a:hover { background:var(--saffron-lite); color:var(--saffron); text-decoration:none; }
.sidebar-lessons li a.done-lesson { color:var(--green); }
.sidebar-lessons li a.done-lesson .lesson-dot { background:var(--green); }
.lesson-dot { width:8px; height:8px; border-radius:50%; background:var(--border); flex-shrink:0; transition:background .2s; }
.lesson-num-small {
  width:20px; height:20px; border-radius:5px;
  background:var(--warm-light); color:var(--warm-gray);
  font-size:.68rem; font-weight:900; display:flex; align-items:center; justify-content:center; flex-shrink:0;
}
.sidebar-mod-nav { display:flex; flex-direction:column; gap:.4rem; }
.sidebar-mod-nav a {
  display:flex; align-items:center; gap:.5rem;
  padding:.55rem .75rem; border-radius:var(--radius-xs);
  font-size:.82rem; font-weight:700; color:var(--warm-mid);
  border:1.5px solid var(--border); transition:all .15s; text-decoration:none;
}
.sidebar-mod-nav a:hover { border-color:var(--saffron); color:var(--saffron); text-decoration:none; }
.sidebar-dl { margin-top:1rem; }
.sidebar-dl .dl-label { font-size:.65rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; color:var(--warm-gray); padding:0 .5rem .6rem; display:block; }
.sidebar-dl a {
  display:flex; align-items:center; gap:.5rem;
  padding:.5rem .75rem; border-radius:var(--radius-xs);
  font-size:.8rem; font-weight:700; color:var(--warm-mid);
  border:1.5px dashed var(--border); text-decoration:none; transition:all .15s;
  margin-bottom:.35rem;
}
.sidebar-dl a:hover { border-color:var(--saffron); color:var(--saffron); text-decoration:none; }
.mod-main { flex:1; min-width:0; }
.mod-header {
  background:var(--white); border:1px solid var(--border);
  border-left:5px solid var(--saffron);
  border-radius:var(--radius); padding:2rem; margin-bottom:1.75rem;
}
.mod-header .mbadge { font-size:.7rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; color:var(--saffron); margin-bottom:.5rem; }
.mod-header h2 { font-size:1.8rem; margin-bottom:.6rem; }
.mod-chips { display:flex; gap:.6rem; flex-wrap:wrap; margin-top:.85rem; }
.intro-box {
  background:linear-gradient(135deg,var(--saffron-lite),#FFF3E0);
  border:1px solid var(--saffron-mid); border-radius:var(--radius-sm);
  padding:1.5rem; margin-bottom:1.75rem;
}
.intro-box .ilabel { font-size:.68rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; color:var(--saffron-dark); margin-bottom:.5rem; }
.why-box { background:var(--blue-lite); border:1px solid #BFDBFE; border-radius:var(--radius-sm); padding:1.5rem; margin-bottom:1.75rem; }
.why-box .ilabel { font-size:.68rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; color:var(--blue); margin-bottom:.5rem; }
.obj-list { list-style:none; padding:0; display:flex; flex-direction:column; gap:.5rem; }
.obj-list li {
  display:flex; align-items:flex-start; gap:.75rem;
  padding:.6rem .75rem; background:var(--warm-light); border-radius:var(--radius-xs);
  font-size:.875rem; color:var(--warm-mid);
}
.obj-list li::before { content:""; color:var(--saffron); font-size:.6rem; margin-top:.35rem; flex-shrink:0; }
.lesson-card { border:1px solid var(--border); border-radius:var(--radius-sm); overflow:hidden; margin-bottom:1rem; }
.lesson-hdr {
  padding:1rem 1.25rem; background:var(--warm-light);
  display:flex; align-items:center; justify-content:space-between;
  cursor:pointer; user-select:none;
}
.lesson-hdr h4 { display:flex; align-items:center; gap:.6rem; font-size:.95rem; }
.lesson-num-badge {
  width:28px; height:28px; border-radius:7px;
  background:var(--saffron); color:white;
  font-size:.8rem; font-weight:900;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
}
.lesson-tog { color:var(--warm-gray); font-size:1.1rem; transition:transform .2s; flex-shrink:0; }
.lesson-body { padding:1.5rem; border-top:1px solid var(--border); display:none; }
.lesson-body.open { display:block; }
.lesson-prose { color:var(--warm-mid); line-height:1.85; margin-bottom:1.25rem; }
.lesson-prose p { margin-bottom:1rem; }
.lesson-example {
  background:var(--saffron-lite); border-left:4px solid var(--saffron);
  border-radius:0 var(--radius-xs) var(--radius-xs) 0;
  padding:1.1rem 1.25rem; margin-bottom:1.25rem;
}
.lesson-example .ex-label { font-size:.68rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; color:var(--saffron-dark); margin-bottom:.4rem; }
.pro-tip-box {
  background:var(--amber-lite); border:1px solid #FDE68A;
  border-radius:var(--radius-xs); padding:1rem 1.25rem; margin-bottom:1.25rem;
  display:flex; align-items:flex-start; gap:.75rem;
}
.pro-tip-box .pt-icon { font-size:1.25rem; flex-shrink:0; margin-top:.1rem; }
.pro-tip-box p { font-size:.875rem; color:#92400E; margin:0; }
.kp-list { list-style:none; padding:0; display:grid; grid-template-columns:1fr 1fr; gap:.4rem; }
.kp-list li {
  font-size:.85rem; color:var(--warm-mid);
  padding:.4rem .6rem .4rem 1.5rem; position:relative;
  background:var(--warm-light); border-radius:var(--radius-xs);
}
.kp-list li::before { content:""; position:absolute; left:.5rem; color:var(--saffron); font-size:.7rem; top:.5rem; }
.mark-read-btn {
  margin-top:1rem; padding:.55rem 1.25rem;
  border-radius:20px; border:1.5px solid var(--green);
  background:transparent; color:var(--green);
  font-family:'Nunito',sans-serif; font-size:.82rem; font-weight:800;
  cursor:pointer; transition:all .15s; display:inline-flex; align-items:center; gap:.4rem;
}
.mark-read-btn:hover { background:var(--green-lite); }
.mark-read-btn.done { background:var(--green-lite); cursor:default; border-color:var(--green); }
.case-study {
  background:linear-gradient(135deg, #1C1917, #3C2A1A);
  border-radius:var(--radius-sm); padding:1.75rem; color:white; margin-bottom:1.5rem;
}
.case-study .cs-label { font-size:.68rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; color:var(--saffron-mid); margin-bottom:.5rem; }
.case-study h4 { color:white; font-size:1rem; margin-bottom:.85rem; }
.case-study .cs-scenario { color:rgba(255,255,255,.75); font-size:.9rem; line-height:1.8; margin-bottom:1rem; }
.case-study .cs-outcome {
  background:rgba(249,115,22,.15); border-left:3px solid var(--saffron);
  padding:1rem 1.25rem; border-radius:0 var(--radius-xs) var(--radius-xs) 0;
  color:rgba(255,255,255,.9); font-size:.875rem;
}
.case-study .cs-outcome-label { font-size:.68rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; color:var(--saffron-mid); margin-bottom:.35rem; }
.do-dont { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1.5rem; }
.do-box { background:var(--green-lite); border:1px solid #BBF7D0; border-radius:var(--radius-sm); padding:1.25rem; }
.dont-box { background:var(--red-lite); border:1px solid #FECACA; border-radius:var(--radius-sm); padding:1.25rem; }
.do-box h4 { color:var(--green); font-size:.875rem; margin-bottom:.85rem; }
.dont-box h4 { color:var(--red); font-size:.875rem; margin-bottom:.85rem; }
.do-box li, .dont-box li { font-size:.855rem; position:relative; padding-left:1.4rem; margin-bottom:.4rem; list-style:none; }
.do-box li::before { content:""; position:absolute; left:0; color:var(--green); }
.dont-box li::before { content:""; position:absolute; left:0; color:var(--red); }
.kc-card { background:var(--saffron-lite); border:1px solid var(--saffron-mid); border-radius:var(--radius-xs); padding:1.15rem; margin-bottom:.75rem; }
.kc-q { font-weight:700; font-size:.9rem; margin-bottom:.5rem; }
.kc-a { font-size:.875rem; color:var(--warm-mid); padding:.65rem .9rem; background:white; border-radius:6px; border:1px solid var(--border); display:none; line-height:1.6; }
.kc-toggle {
  margin-top:.6rem; font-size:.78rem; font-weight:800;
  padding:.3rem .75rem; border-radius:6px;
  border:1px solid var(--saffron); background:transparent;
  color:var(--saffron); cursor:pointer; font-family:'Nunito',sans-serif; transition:all .15s;
}
.kc-toggle:hover { background:var(--saffron); color:white; }
.summary-box {
  background:linear-gradient(135deg,#1C1917,#3C2A1A);
  border-radius:var(--radius-sm); padding:1.75rem; color:white; margin-bottom:1.75rem;
}
.summary-box .sl { font-size:.68rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; color:var(--saffron-mid); margin-bottom:.5rem; }
.summary-box p { color:rgba(255,255,255,.8); margin:0; line-height:1.8; }
.lesson-bar-wrap { height:6px; background:var(--warm-light); border-radius:3px; margin-bottom:1.5rem; overflow:hidden; }
.lesson-bar-fill { height:100%; background:linear-gradient(90deg,var(--green),#22C55E); transition:width .4s; }
.lesson-bar-label { font-size:.75rem; font-weight:700; color:var(--warm-gray); margin-bottom:.4rem; }
.completion-banner {
  display:none; background:linear-gradient(135deg,var(--green),#15803D);
  border-radius:var(--radius); padding:2rem; text-align:center; color:white; margin-bottom:1.75rem;
}
.completion-banner h3 { color:white; font-size:1.5rem; margin-bottom:.5rem; }
.completion-banner p { color:rgba(255,255,255,.75); margin-bottom:1.25rem; }
.completion-banner .cb-btns { display:flex; gap:1rem; justify-content:center; flex-wrap:wrap; }
.mod-nav-row {
  display:flex; justify-content:space-between; align-items:center;
  padding:1.5rem 0; border-top:1px solid var(--border); margin-top:1rem;
}
@media (max-width:900px) {
  .lms-wrap { flex-direction:column; padding:1rem; }
  .mod-sidebar { width:100%; position:static; max-height:none; }
  .sidebar-lessons { flex-direction:row; flex-wrap:wrap; }
  .do-dont { grid-template-columns:1fr; }
  .kp-list { grid-template-columns:1fr; }
}"""

    def write(
        self,
        module: dict,
        module_index: int,
        total_modules: int,
        course_title: str,
        dept: str,
        slug: str,
        index_filename: str,
        prev_filename: Optional[str],
        next_filename: Optional[str],
        exam_filename: str,
        out_path: Path,
        db_course_id: str = "",      # <- str, not int
    ) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render(
            module, module_index, total_modules, course_title, dept, slug,
            index_filename, prev_filename, next_filename, exam_filename,
            db_course_id=db_course_id,
        )
        out_path.write_text(html, encoding="utf-8")
        return out_path

    def _render(
        self,
        m: dict,
        idx: int,
        total: int,
        course_title: str,
        dept: str,
        slug: str,
        index_fn: str,
        prev_fn: Optional[str],
        next_fn: Optional[str],
        exam_fn: str,
        db_course_id: str = "",      # <- str
    ) -> str:
        title    = _esc_html(m.get("title", f"Module {idx}"))
        duration = _esc_html(m.get("duration", ""))
        mod_id   = _esc_html(m.get("module_id", f"mod_{idx}"))
        content  = m.get("content", {})
        quiz     = m.get("quiz", [])

        intro     = content.get("introduction", "")
        why       = content.get("why_it_matters", "")
        objs      = content.get("learning_objectives", [])
        lessons   = content.get("lessons", [])
        do_list   = content.get("do", [])
        dont_list = content.get("dont", [])
        case_st   = content.get("case_study", {})
        summary   = content.get("summary", "")
        kc_list   = content.get("knowledge_check", [])

        def mod_url(mod_i: int) -> str:
            return (f"/api/generated-courses/download/{db_course_id}/module/{mod_i}"
                    if db_course_id else f"./{slug}-module-{mod_i:02d}.html")

        def exam_url() -> str:
            return (f"/api/generated-courses/download/{db_course_id}/exam"
                    if db_course_id else f"./{exam_fn}")

        def index_url() -> str:
            return (f"/api/generated-courses/download/{db_course_id}/index"
                    if db_course_id else f"./{index_fn}")

        prev_url = mod_url(idx - 1) if idx > 1 else None
        next_url = mod_url(idx + 1) if idx < total else None

        sidebar_html = self._render_sidebar(
            lessons, idx, total,
            index_url(), prev_url, next_url, exam_url(),
            db_course_id,
        )
        lessons_html  = self._render_lessons(lessons, idx)
        objs_html     = "".join(f"<li>{_esc_html(o)}</li>" for o in objs)
        case_html     = self._render_case_study(case_st, idx)
        do_dont_html  = self._render_do_dont(do_list, dont_list)
        kc_html       = self._render_knowledge_check(kc_list, idx)
        quiz_html     = self._render_quiz(quiz, idx)

        prev_btn = (f'<a href="{prev_url}" class="btn btn-ghost"><- Previous</a>'
                    if prev_url else '<span></span>')
        next_btn = (f'<a href="{next_url}" class="btn btn-primary">Next Module -></a>'
                    if next_url
                    else f'<a href="{exam_url()}" class="btn btn-primary">Final Exam </a>')

        quiz_data_js = json.dumps([
            {"ci": q.get("correct_index", 0), "exp": q.get("explanation", "")}
            for q in quiz
        ], ensure_ascii=False)

        n_lessons  = len(lessons)
        slug_js    = _esc_js(slug)
        title_js   = _esc_js(m.get("title", f"Module {idx}"))
        dept_js    = _esc_js(dept)
        db_id_js   = _esc_js(db_course_id)

        dl_sidebar = ""
        if db_course_id:
            dl_sidebar = f"""
<div class="sidebar-dl">
  <span class="dl-label">Download</span>
  <a href="/api/generated-courses/download/{db_course_id}/module/{idx}?as_file=true" download> This Module</a>
  <a href="/api/generated-courses/download/{db_course_id}/index?as_file=true" download> Course Index</a>
  <a href="/api/generated-courses/download/{db_course_id}/exam?as_file=true" download> Final Exam</a>
</div>"""

        cb_next = (f'<a href="{next_url}" class="btn btn-primary">Next Module -></a>'
                   if next_url
                   else f'<a href="{exam_url()}" class="btn btn-primary">Take Final Exam </a>')

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Module {idx}: {title}  NamanDarshan LMS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Yeseva+One&family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
{SHARED_CSS_VARS}
{SHARED_BASE_CSS}
{self.MODULE_CSS}
</style>
</head>
<body>

<nav class="navbar">
  <div class="navbar-brand">
    <div class="navbar-logo"></div>
    <span class="navbar-title">Naman<span>LMS</span></span>
  </div>
  <div class="navbar-links">
    <a href="{index_url()}"><- Course Home</a>
    <a href="{exam_url()}">Final Exam</a>
  </div>
  <span class="navbar-badge">Module {idx}/{total}</span>
</nav>

<div class="progress-strip">
  <div class="progress-fill" id="lesson-prog-bar" style="width:0%"></div>
</div>

<div class="lms-wrap">
  <aside class="mod-sidebar">
    {sidebar_html}
    {dl_sidebar}
  </aside>

  <main class="mod-main">
    <div class="mod-header">
      <div class="mbadge">Module {idx} of {total}  {dept}</div>
      <h2>{title}</h2>
      <div class="mod-chips">
        <span class="chip"> {duration}</span>
        <span class="chip"> {n_lessons} lessons</span>
        <span class="chip"> {len(quiz)} quiz questions</span>
      </div>
    </div>

    <div class="s-card" style="padding:1.25rem 1.5rem;">
      <div class="lesson-bar-label">Lesson Progress  <span id="lprog-label">0 of {n_lessons} read</span></div>
      <div class="lesson-bar-wrap"><div class="lesson-bar-fill" id="lesson-fill" style="width:0%"></div></div>
    </div>

    {('<div class="intro-box"><div class="ilabel">Module Introduction</div>' + _prose_to_html(intro) + '</div>') if intro else ''}
    {('<div class="why-box"><div class="ilabel"> Why This Matters</div>' + _prose_to_html(why) + '</div>') if why else ''}
    {('<div class="s-card"><h3 class="s-card-title"><span class="s-card-icon"></span>Learning Objectives</h3><ul class="obj-list">' + objs_html + '</ul></div>') if objs else ''}

    <div class="s-card">
      <h3 class="s-card-title"><span class="s-card-icon"></span>Lessons</h3>
      {lessons_html}
    </div>

    {case_html}
    {('<div class="s-card"><h3 class="s-card-title"><span class="s-card-icon">[OK]</span>Do&#39;s &amp; Don&#39;ts</h3>' + do_dont_html + '</div>') if (do_list or dont_list) else ''}
    {('<div class="s-card"><h3 class="s-card-title"><span class="s-card-icon"></span>Quick Knowledge Check</h3>' + kc_html + '</div>') if kc_list else ''}
    {('<div class="s-card"><h3 class="s-card-title"><span class="s-card-icon"></span>Module Summary</h3><div class="summary-box"><div class="sl">Key Takeaways</div>' + _prose_to_html(summary) + '</div></div>') if summary else ''}

    {quiz_html}

    <div class="completion-banner" id="completion-banner">
      <h3> Module Complete!</h3>
      <p>Great work! Your progress has been recorded. You scored <strong><span id="final-score"></span></strong> on this module.</p>
      <div class="cb-btns">
        {cb_next}
        <a href="{index_url()}" class="btn btn-ghost" style="color:white;border-color:rgba(255,255,255,.4);">Back to Course Home</a>
      </div>
    </div>

    <div class="mod-nav-row">
      {prev_btn}
      {next_btn}
    </div>
  </main>
</div>

<script>
const QUIZ_DATA     = {quiz_data_js};
const TOTAL_LESSONS = {n_lessons};
const COURSE_SLUG   = '{slug_js}';
const MODULE_IDX    = {idx};
const MODULE_ID     = '{_esc_js(mod_id)}';
const MODULE_TITLE  = '{title_js}';
const DEPT          = '{dept_js}';
const COURSE_DB_ID  = '{db_id_js}';

const readLessons = new Set();

function markLessonRead(lid) {{
  readLessons.add(lid);
  const btn = document.getElementById('read-btn-' + lid);
  if (btn) {{ btn.textContent = '[OK] Read'; btn.classList.add('done'); btn.disabled = true; }}
  const dot = document.querySelector('.sidebar-lessons li a[data-lid="' + lid + '"] .lesson-dot');
  if (dot) dot.style.background = 'var(--green)';
  const link = document.querySelector('.sidebar-lessons li a[data-lid="' + lid + '"]');
  if (link) link.classList.add('done-lesson');
  updateLessonProgress();
}}

function updateLessonProgress() {{
  const pct = TOTAL_LESSONS > 0 ? Math.round((readLessons.size / TOTAL_LESSONS) * 100) : 0;
  const fill = document.getElementById('lesson-fill');
  const bar  = document.getElementById('lesson-prog-bar');
  const lbl  = document.getElementById('lprog-label');
  if (fill) fill.style.width = pct + '%';
  if (bar)  bar.style.width  = pct + '%';
  if (lbl)  lbl.textContent  = readLessons.size + ' of ' + TOTAL_LESSONS + ' read';
}}

function toggleLesson(lid) {{
  const body = document.getElementById('lbody-' + lid);
  const tog  = document.getElementById('ltog-' + lid);
  if (!body) return;
  const open = body.classList.toggle('open');
  if (tog) tog.style.transform = open ? 'rotate(180deg)' : '';
  if (open) setTimeout(() => body.scrollIntoView({{ behavior:'smooth', block:'nearest' }}), 100);
}}

function toggleKC(kid) {{
  const ans = document.getElementById('kca-' + kid);
  const btn = document.getElementById('kcb-' + kid);
  if (!ans) return;
  const shown = ans.style.display === 'block';
  ans.style.display = shown ? 'none' : 'block';
  if (btn) btn.textContent = shown ? 'Show Answer' : 'Hide Answer';
}}

const chosen  = {{}};
let submitted = false;
let quizScore = 0;

function selectOpt(qi, oi) {{
  if (submitted) return;
  chosen[qi] = oi;
  const opts = document.querySelectorAll('[data-qi="' + qi + '"] .quiz-opt');
  opts.forEach((o, i) => o.classList.toggle('sel', i === oi));
}}

function submitQuiz() {{
  if (submitted) return;
  submitted = true;
  let correct = 0;
  QUIZ_DATA.forEach((q, qi) => {{
    const sel = chosen[qi];
    const opts = document.querySelectorAll('[data-qi="' + qi + '"] .quiz-opt');
    opts.forEach((o, i) => {{
      o.classList.add('dis');
      if (i === q.ci) o.classList.add('correct');
      else if (i === sel && i !== q.ci) o.classList.add('wrong');
    }});
    const exp = document.getElementById('qexp-' + qi);
    if (exp) exp.style.display = 'block';
    if (sel === q.ci) correct++;
  }});
  quizScore = QUIZ_DATA.length > 0 ? Math.round((correct / QUIZ_DATA.length) * 100) : 0;
  const res = document.getElementById('quiz-result');
  if (res) {{
    res.style.display = 'block';
    res.querySelector('.rs').textContent = quizScore + '%';
    res.querySelector('.rm').textContent = correct + ' of ' + QUIZ_DATA.length + ' correct';
    const badge = res.querySelector('.result-badge');
    if (quizScore >= 70) {{ badge.textContent = '[OK] Passed'; badge.className = 'result-badge rb-pass'; }}
    else {{ badge.textContent = ' Needs Improvement'; badge.className = 'result-badge rb-fail'; }}
  }}
  document.getElementById('submit-btn').style.display = 'none';
  document.getElementById('retry-btn').style.display  = 'inline-flex';
  if (quizScore >= 70) markComplete();
}}

function retryQuiz() {{
  submitted = false; quizScore = 0;
  Object.keys(chosen).forEach(k => delete chosen[k]);
  document.querySelectorAll('.quiz-opt').forEach(o => o.className = 'quiz-opt');
  document.querySelectorAll('[id^="qexp-"]').forEach(e => e.style.display = 'none');
  const res = document.getElementById('quiz-result');
  if (res) res.style.display = 'none';
  document.getElementById('submit-btn').style.display = 'inline-flex';
  document.getElementById('retry-btn').style.display  = 'none';
}}

function markComplete() {{
  const score = quizScore;
  const key   = `nd_${{COURSE_SLUG}}_mod${{MODULE_IDX}}`;
  try {{ localStorage.setItem(key, JSON.stringify({{ passed: score >= 70, score, completedAt: new Date().toISOString() }})); }} catch(e) {{}}
  const banner = document.getElementById('completion-banner');
  const fs     = document.getElementById('final-score');
  if (fs) fs.textContent = score + '%';
  if (banner) banner.style.display = 'block';
  postProgress(score);
}}

function postProgress(score) {{
  try {{
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const headers = {{ 'Content-Type': 'application/json', ...(token ? {{'Authorization': `Bearer ${{token}}`}} : {{}}) }};
    const learner_id = localStorage.getItem('nd_learner_id') || 'anonymous';

    if (COURSE_DB_ID) {{
      fetch('/api/generated-courses/progress', {{
        method: 'POST', headers,
        body: JSON.stringify({{
          learner_id, course_id: COURSE_DB_ID,
          module_id: MODULE_ID, module_title: MODULE_TITLE, department: DEPT,
          score, passed: score >= 70, source: 'html_module'
        }})
      }}).catch(() => {{}});
    }}

    fetch('/api/update-progress', {{
      method: 'POST', headers,
      body: JSON.stringify({{
        module_id: MODULE_ID, module_title: MODULE_TITLE, department: DEPT,
        score, passed: score >= 70, source: 'html_module', timestamp: new Date().toISOString()
      }})
    }}).catch(() => {{}});
  }} catch(e) {{}}
}}

document.addEventListener('DOMContentLoaded', () => {{
  const firstBody = document.querySelector('.lesson-body');
  if (firstBody) firstBody.classList.add('open');
  const firstTog = document.querySelector('.lesson-tog');
  if (firstTog) firstTog.style.transform = 'rotate(180deg)';
  try {{
    const key  = `nd_${{COURSE_SLUG}}_mod${{MODULE_IDX}}`;
    const data = JSON.parse(localStorage.getItem(key) || 'null');
    if (data && data.passed) {{
      const banner = document.getElementById('completion-banner');
      const fs     = document.getElementById('final-score');
      if (fs) fs.textContent = (data.score || '') + '%';
      if (banner) banner.style.display = 'block';
    }}
  }} catch(e) {{}}
}});
</script>
</body>
</html>"""

    def _render_sidebar(
        self, lessons: list, idx: int, total: int,
        index_url: str, prev_url: Optional[str], next_url: Optional[str], exam_url: str,
        db_course_id: str = "",
    ) -> str:
        lesson_items = ""
        for i, l in enumerate(lessons):
            lid    = f"m{idx}l{i}"
            ltitle = _esc_html(l.get("title", f"Lesson {i+1}"))
            lesson_items += f"""<li>
  <a href="#" onclick="toggleLesson('{lid}');return false;" data-lid="{lid}">
    <span class="lesson-num-small">{i+1}</span>
    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{ltitle}</span>
    <span class="lesson-dot"></span>
  </a>
</li>"""
        nav_links = f'<a href="{index_url}"> Course Home</a>\n'
        if prev_url:
            nav_links += f'<a href="{prev_url}"><- Previous Module</a>\n'
        if next_url:
            nav_links += f'<a href="{next_url}">Next Module -></a>\n'
        else:
            nav_links += f'<a href="{exam_url}"> Final Exam</a>\n'
        return f"""<div class="sidebar-section">
  <span class="sidebar-label">In This Module</span>
  <ul class="sidebar-lessons">{lesson_items}</ul>
</div>
<div class="sidebar-section">
  <span class="sidebar-label">Navigate</span>
  <div class="sidebar-mod-nav">{nav_links}</div>
</div>"""

    def _render_lessons(self, lessons: list, mod_idx: int) -> str:
        parts = []
        for i, l in enumerate(lessons):
            lid    = f"m{mod_idx}l{i}"
            ltitle = _esc_html(l.get("title", f"Lesson {i+1}"))
            body   = l.get("body", "")
            ex     = _esc_html(l.get("example", ""))
            kpts   = l.get("key_points", [])
            tip    = _esc_html(l.get("pro_tip", ""))
            kpts_html = "".join(f"<li>{_esc_html(k)}</li>" for k in kpts)
            body_html = _prose_to_html(body)
            parts.append(f"""<div class="lesson-card" id="lesson-{lid}">
  <div class="lesson-hdr" onclick="toggleLesson('{lid}')">
    <h4><span class="lesson-num-badge">{i+1}</span>{ltitle}</h4>
    <span class="lesson-tog" id="ltog-{lid}"></span>
  </div>
  <div class="lesson-body" id="lbody-{lid}">
    <div class="lesson-prose">{body_html}</div>
    {('<div class="lesson-example"><div class="ex-label"> Real-World Example</div>' + ex + '</div>') if ex else ''}
    {('<div class="pro-tip-box"><span class="pt-icon"></span><p><strong>Pro Tip:</strong> ' + tip + '</p></div>') if tip else ''}
    {('<ul class="kp-list">' + kpts_html + '</ul>') if kpts_html else ''}
    <button class="mark-read-btn" id="read-btn-{lid}" onclick="markLessonRead('{lid}')">Mark as Read [OK]</button>
  </div>
</div>""")
        return "\n".join(parts)

    def _render_case_study(self, cs: dict, mod_idx: int) -> str:
        if not cs:
            return ""
        title    = _esc_html(cs.get("title", "Case Study"))
        scenario = _prose_to_html(cs.get("scenario", ""))
        outcome  = _prose_to_html(cs.get("outcome", ""))
        return f"""<div class="s-card">
  <h3 class="s-card-title"><span class="s-card-icon"></span>Case Study</h3>
  <div class="case-study">
    <div class="cs-label">Case Study</div>
    <h4>{title}</h4>
    <div class="cs-scenario">{scenario}</div>
    <div class="cs-outcome"><div class="cs-outcome-label">Outcome &amp; Learning</div>{outcome}</div>
  </div>
</div>"""

    def _render_do_dont(self, do_list: list, dont_list: list) -> str:
        do_items   = "".join(f"<li>{_esc_html(d)}</li>" for d in do_list)
        dont_items = "".join(f"<li>{_esc_html(d)}</li>" for d in dont_list)
        return f"""<div class="do-dont">
  <div class="do-box"><h4> Best Practices (DO)</h4><ul>{do_items}</ul></div>
  <div class="dont-box"><h4> Common Mistakes (DON'T)</h4><ul>{dont_items}</ul></div>
</div>"""

    def _render_knowledge_check(self, kc_list: list, mod_idx: int) -> str:
        parts = []
        for i, kc in enumerate(kc_list):
            kid = f"m{mod_idx}kc{i}"
            q   = _esc_html(kc.get("question", ""))
            a   = _esc_html(kc.get("answer", ""))
            parts.append(f"""<div class="kc-card">
  <div class="kc-q">Q: {q}</div>
  <div class="kc-a" id="kca-{kid}">{a}</div>
  <button class="kc-toggle" id="kcb-{kid}" onclick="toggleKC('{kid}')">Show Answer</button>
</div>""")
        return "\n".join(parts)

    def _render_quiz(self, quiz: list, mod_idx: int) -> str:
        if not quiz:
            return ""
        q_html = []
        for qi, q in enumerate(quiz):
            qtext = _esc_html(q.get("question", ""))
            opts  = q.get("options", [])
            exp   = _esc_html(q.get("explanation", ""))
            opts_html = "".join(
                f'<button class="quiz-opt" data-qi="{qi}" onclick="selectOpt({qi},{oi})">'
                f'<span class="ol">{chr(65+oi)}</span>{_esc_html(opt)}</button>'
                for oi, opt in enumerate(opts)
            )
            q_html.append(f"""<div class="quiz-q" data-qi="{qi}">
  <div class="quiz-q-label">Question {qi+1} of {len(quiz)}</div>
  <div class="quiz-q-text">{qtext}</div>
  <div class="quiz-opts">{opts_html}</div>
  <div class="quiz-exp" id="qexp-{qi}">{exp}</div>
</div>""")
        return f"""<div class="quiz-wrap">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
    <h3 style="font-size:1.15rem;display:flex;align-items:center;gap:.5rem;border:none;padding:0;margin:0;"> Module Assessment</h3>
    <span style="font-size:.82rem;font-weight:700;color:var(--warm-gray);">Pass mark: 70%</span>
  </div>
  {"".join(q_html)}
  <div id="quiz-result" class="quiz-result">
    <div class="rs">0%</div>
    <div class="rm"></div>
    <span class="result-badge"></span>
  </div>
  <div style="display:flex;gap:.75rem;margin-top:1.5rem;flex-wrap:wrap;">
    <button class="btn btn-primary" id="submit-btn" onclick="submitQuiz()">Submit Answers</button>
    <button class="btn btn-ghost" id="retry-btn" onclick="retryQuiz()" style="display:none;"> Retry Quiz</button>
  </div>
</div>"""


# ============================================================================
# HTML FINAL EXAM WRITER
# ============================================================================

class HtmlFinalExamWriter:
    EXAM_CSS = """
.exam-page { max-width:860px; margin:0 auto; padding:2.5rem 1.5rem; }
.exam-hero {
  background:linear-gradient(135deg,#1C1917,#3C2A1A);
  border-radius:var(--radius); padding:3rem; text-align:center;
  color:white; margin-bottom:2.5rem; position:relative; overflow:hidden;
}
.exam-hero::before { content:""; position:absolute; right:2rem; top:50%; transform:translateY(-50%); font-size:8rem; opacity:.07; }
.exam-hero h1 { color:white; font-size:2rem; margin-bottom:.6rem; }
.exam-hero p { color:rgba(255,255,255,.6); max-width:480px; margin:0 auto; }
.exam-hero .eh-chips { display:flex; gap:.75rem; justify-content:center; flex-wrap:wrap; margin-top:1.25rem; }
.certificate {
  display:none; background:linear-gradient(135deg,var(--saffron-lite),#FFF3E0);
  border:2px solid var(--saffron-mid); border-radius:var(--radius);
  padding:3rem; text-align:center; margin-bottom:2rem;
}
.certificate .cert-icon { font-size:4rem; margin-bottom:1rem; }
.certificate h2 { font-size:1.75rem; color:var(--saffron-dark); margin-bottom:.5rem; }
.certificate p { color:var(--warm-gray); margin-bottom:1.5rem; }
.certificate .cert-score { font-family:'Yeseva One',serif; font-size:3.5rem; color:var(--saffron); line-height:1; margin-bottom:.25rem; }
.exam-dl-bar { text-align:center; margin-bottom:1.5rem; }"""

    def write(
        self,
        final_exam: list,
        course_title: str,
        dept: str,
        slug: str,
        total_modules: int,
        index_filename: str,
        out_path: Path,
        db_course_id: str = "",      # <- str
    ) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render(final_exam, course_title, dept, slug, total_modules, index_filename, db_course_id)
        out_path.write_text(html, encoding="utf-8")
        return out_path

    def _render(
        self,
        exam: list,
        course_title: str,
        dept: str,
        slug: str,
        total_modules: int,
        index_fn: str,
        db_course_id: str = "",      # <- str
    ) -> str:
        title   = _esc_html(course_title)
        dept_e  = _esc_html(dept)
        slug_js = _esc_js(slug)
        dept_js = _esc_js(dept)
        db_js   = _esc_js(db_course_id)
        n       = len(exam)

        index_url = (f"/api/generated-courses/download/{db_course_id}/index"
                     if db_course_id else f"./{index_fn}")

        dl_bar = ""
        if db_course_id:
            dl_bar = f"""<div class="exam-dl-bar">
  <a href="/api/generated-courses/download/{db_course_id}/exam?as_file=true" download class="btn btn-ghost" style="font-size:.82rem;"> Download This Exam as HTML</a>
</div>"""

        q_html = []
        for qi, q in enumerate(exam):
            qtext = _esc_html(q.get("question", ""))
            opts  = q.get("options", [])
            exp   = _esc_html(q.get("explanation", ""))
            opts_html = "".join(
                f'<button class="quiz-opt" data-qi="{qi}" onclick="selectOpt({qi},{oi})">'
                f'<span class="ol">{chr(65+oi)}</span>{_esc_html(opt)}</button>'
                for oi, opt in enumerate(opts)
            )
            q_html.append(f"""<div class="quiz-q" data-qi="{qi}">
  <div class="quiz-q-label">Question {qi+1} of {n}</div>
  <div class="quiz-q-text">{qtext}</div>
  <div class="quiz-opts">{opts_html}</div>
  <div class="quiz-exp" id="qexp-{qi}">{exp}</div>
</div>""")

        exam_data_js = json.dumps([
            {"ci": q.get("correct_index", 0), "exp": q.get("explanation", "")}
            for q in exam
        ], ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Final Exam  {title}  NamanDarshan LMS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Yeseva+One&family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
{SHARED_CSS_VARS}
{SHARED_BASE_CSS}
{self.EXAM_CSS}
</style>
</head>
<body>

<nav class="navbar">
  <div class="navbar-brand">
    <div class="navbar-logo"></div>
    <span class="navbar-title">Naman<span>LMS</span></span>
  </div>
  <div class="navbar-links">
    <a href="{index_url}"><- Course Home</a>
  </div>
  <span class="navbar-badge">{dept_e} Final Exam</span>
</nav>
<div class="progress-strip"><div class="progress-fill" style="width:100%"></div></div>

<div class="exam-page">
  <div class="exam-hero">
    <h1> Final Course Examination</h1>
    <p>This exam covers all {total_modules} modules. You need <strong>70%</strong> or above to receive your completion certificate.</p>
    <div class="eh-chips">
      <span class="chip chip-saffron"> {total_modules} Modules Covered</span>
      <span class="chip chip-saffron"> {n} Questions</span>
      <span class="chip chip-saffron"> ~{max(10, n*2)} min</span>
    </div>
  </div>

  {dl_bar}

  <div class="certificate" id="certificate">
    <div class="cert-icon"></div>
    <div class="cert-score" id="cert-score"></div>
    <h2>Course Completed!</h2>
    <p>Congratulations! You have successfully completed <strong>{title}</strong>.</p>
    <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
      <a href="{index_url}" class="btn btn-primary"><- Back to Course</a>
      <button class="btn btn-ghost" onclick="window.print()"> Print Certificate</button>
    </div>
  </div>

  <div class="quiz-wrap">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.75rem;">
      <h2 style="font-size:1.25rem;display:flex;align-items:center;gap:.5rem;border:none;padding:0;margin:0;">Final Exam Questions</h2>
      <span style="font-size:.82rem;font-weight:700;color:var(--warm-gray);">Pass mark: 70%</span>
    </div>
    {"".join(q_html)}
    <div id="quiz-result" class="quiz-result">
      <div class="rs">0%</div>
      <div class="rm"></div>
      <span class="result-badge"></span>
    </div>
    <div style="display:flex;gap:.75rem;margin-top:1.5rem;flex-wrap:wrap;">
      <button class="btn btn-primary" id="submit-btn" onclick="submitExam()">Submit Final Exam</button>
      <button class="btn btn-ghost" id="retry-btn" onclick="retryExam()" style="display:none;"> Retry Exam</button>
    </div>
  </div>
</div>

<script>
const EXAM_DATA    = {exam_data_js};
const COURSE_SLUG  = '{slug_js}';
const DEPT         = '{dept_js}';
const COURSE_DB_ID = '{db_js}';
const chosen = {{}};
let submitted = false;

function selectOpt(qi, oi) {{
  if (submitted) return;
  chosen[qi] = oi;
  const opts = document.querySelectorAll('[data-qi="' + qi + '"] .quiz-opt');
  opts.forEach((o, i) => o.classList.toggle('sel', i === oi));
}}

function submitExam() {{
  if (submitted) return;
  submitted = true;
  let correct = 0;
  EXAM_DATA.forEach((q, qi) => {{
    const sel = chosen[qi];
    const opts = document.querySelectorAll('[data-qi="' + qi + '"] .quiz-opt');
    opts.forEach((o, i) => {{
      o.classList.add('dis');
      if (i === q.ci) o.classList.add('correct');
      else if (i === sel && i !== q.ci) o.classList.add('wrong');
    }});
    const exp = document.getElementById('qexp-' + qi);
    if (exp) exp.style.display = 'block';
    if (sel === q.ci) correct++;
  }});
  const pct = EXAM_DATA.length > 0 ? Math.round((correct / EXAM_DATA.length) * 100) : 0;
  const res = document.getElementById('quiz-result');
  if (res) {{
    res.style.display = 'block';
    res.querySelector('.rs').textContent = pct + '%';
    res.querySelector('.rm').textContent = correct + ' of ' + EXAM_DATA.length + ' correct';
    const badge = res.querySelector('.result-badge');
    if (pct >= 70) {{ badge.textContent = '[OK] Passed  Certificate Awarded'; badge.className = 'result-badge rb-pass'; }}
    else {{ badge.textContent = ' Needs Improvement  Retry to pass'; badge.className = 'result-badge rb-fail'; }}
  }}
  document.getElementById('submit-btn').style.display = 'none';
  document.getElementById('retry-btn').style.display  = 'inline-flex';
  if (pct >= 70) {{
    try {{ localStorage.setItem(`nd_${{COURSE_SLUG}}_final`, JSON.stringify({{ passed:true, score:pct, completedAt:new Date().toISOString() }})); }} catch(e) {{}}
    const cert = document.getElementById('certificate');
    const cs   = document.getElementById('cert-score');
    if (cs) cs.textContent = pct + '%';
    if (cert) {{ cert.style.display = 'block'; cert.scrollIntoView({{ behavior:'smooth', block:'center' }}); }}
  }}
  postExamProgress(pct);
}}

function postExamProgress(pct) {{
  try {{
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const headers = {{ 'Content-Type': 'application/json', ...(token ? {{'Authorization': `Bearer ${{token}}`}} : {{}}) }};
    const learner_id = localStorage.getItem('nd_learner_id') || 'anonymous';
    if (COURSE_DB_ID) {{
      fetch('/api/generated-courses/progress', {{
        method: 'POST', headers,
        body: JSON.stringify({{
          learner_id, course_id: COURSE_DB_ID,
          module_id: 'final_exam', module_title: 'Final Exam', department: DEPT,
          score: pct, passed: pct >= 70, source: 'html_final_exam'
        }})
      }}).catch(() => {{}});
    }}
    fetch('/api/update-progress', {{
      method: 'POST', headers,
      body: JSON.stringify({{ module_id:'final_exam', module_title:'Final Exam', department:DEPT, score:pct, passed:pct>=70, source:'html_final_exam', timestamp:new Date().toISOString() }})
    }}).catch(() => {{}});
  }} catch(e) {{}}
}}

function retryExam() {{
  submitted = false;
  Object.keys(chosen).forEach(k => delete chosen[k]);
  document.querySelectorAll('.quiz-opt').forEach(o => o.className = 'quiz-opt');
  document.querySelectorAll('[id^="qexp-"]').forEach(e => e.style.display = 'none');
  const res = document.getElementById('quiz-result');
  if (res) res.style.display = 'none';
  document.getElementById('submit-btn').style.display = 'inline-flex';
  document.getElementById('retry-btn').style.display  = 'none';
}}
</script>
</body>
</html>"""


# ============================================================================
# LEGACY: HtmlCourseSpaWriter
# ============================================================================

class HtmlCourseSpaWriter:
    """DEPRECATED in v5. Use generate_html_course_package()."""

    def write(self, course_json: dict, out_path: Path) -> Path:
        dept  = course_json.get("department", "general")
        slug  = _slugify(dept)
        n     = len(course_json.get("modules", []))
        return HtmlCourseIndexWriter().write(
            course_json,
            [f"{slug}-module-{i+1:02d}.html" for i in range(n)],
            f"{slug}-final-exam.html",
            out_path,
        )


# ============================================================================
# PDF WRITERS
# ============================================================================

class BookletPdfWriter:
    LINE_H = 14

    def write(self, booklet: "ModuleBooklet", out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = self._booklet_to_lines(booklet)
        _SimplePdfWriter(booklet.module_title).write(out_path, lines)
        return out_path

    def _booklet_to_lines(self, b: "ModuleBooklet") -> list[str]:
        L = []
        def blank(n=1): L.extend([""] * n)
        def rule(): L.append("-" * 72)
        def h1(t): blank(); L.append(t.upper()); rule()
        def h2(t): blank(); L.append(f" {t}"); L.append("")
        def body(t):
            for line in textwrap.wrap(t, width=90): L.append(f"  {line}")
        def bullet(items, prefix="*"):
            for item in items:
                for i, w in enumerate(textwrap.wrap(item, width=85)):
                    L.append(f"    {prefix} {w}" if i == 0 else f"       {w}")

        blank(4)
        L += ["=" * 72, f"  NAMANDARSHAN  |  {b.department.upper()} DEPARTMENT", "=" * 72]
        blank(2)
        L.append(f"  MODULE {b.module_index}")
        blank()
        for line in textwrap.wrap(b.module_title.upper(), width=60): L.append(f"  {line}")
        blank(2)
        L += [f"  Duration  :  {b.duration}", f"  Module ID :  {b.module_id}",
              f"  Generated :  {datetime.utcnow().strftime('%d %b %Y')}"]
        blank(2)
        L += ["  Complete this module online  open the HTML course file.",
              "  Your score is recorded automatically in the Growth Report.",
              "=" * 72]
        blank(6)

        h1(f"Introduction to Module {b.module_index}: {b.module_title}")
        blank(); body(b.introduction); blank()
        h2("Why This Module Matters"); body(b.why_it_matters); blank()
        h2("Learning Goals"); bullet(b.goals); blank(2)

        for i, lesson in enumerate(b.lesson_explanations, 1):
            h1(f"Lesson {i}: {lesson.lesson_title}")
            blank(); body(lesson.body); blank()
            if lesson.key_points: h2("Key Points"); bullet(lesson.key_points); blank()
            if lesson.real_world_example: h2("Real-World Example"); body(lesson.real_world_example); blank()
            do_l = lesson.do_and_dont.get("do", [])
            dn_l = lesson.do_and_dont.get("dont", [])
            if do_l or dn_l:
                h2("Do's and Don'ts")
                if do_l: L.append("   DO:"); bullet(do_l, "")
                if dn_l: blank(); L.append("   DON'T:"); bullet(dn_l, "")
            blank(2)

        if b.sop_checkpoints:
            h1("SOP Checkpoints"); blank(); bullet(b.sop_checkpoints, ""); blank(2)

        h1("Module Recap"); blank(); body(b.module_recap); blank()
        if b.whats_next: h2("What's Next"); body(b.whats_next); blank(2)

        blank()
        L += ["=" * 72, "  ASSESSMENT REMINDER", "=" * 72, "",
              "  Open the HTML course file on your device to take the module quiz.",
              "  Your score updates the Growth Report instantly.",
              "", "  Passing score: 70% or above",
              "=" * 72, "  End of Module Booklet  |  NamanDarshan v5", "=" * 72]
        return L


class _SimplePdfWriter:
    def __init__(self, title: str):
        self.title = title

    def write(self, output_path: Path, lines: list[str]) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        safe_lines = [str(l) for l in lines if l is not None] or ["[Empty Content]"]

        if FPDF is not None:
            try:
                pdf = FPDF(unit="pt", format="A4")
                pdf.set_auto_page_break(auto=True, margin=36)
                pdf.set_title(self.title)
                pdf.set_author("NamanDarshan Course Generator v5")
                pdf.add_page()
                pdf.set_font("Helvetica", size=10)
                for line in safe_lines:
                    pdf.multi_cell(0, 14, line.encode("latin-1", errors="replace").decode("latin-1"))
                pdf.output(str(output_path))
                return output_path
            except Exception:
                pass

        pw, ph = 595, 842
        ml, mt = 54, 60
        lh, lpp, fs = 14, 48, 10
        wrapped: list[str] = []
        for line in safe_lines:
            if not line.strip(): wrapped.append("")
            else: wrapped.extend(textwrap.wrap(line, width=88) or [""])
        pages = [wrapped[i:i+lpp] for i in range(0, max(len(wrapped), 1), lpp)]

        def esc(t):
            s = t.encode("latin-1", errors="replace").decode("latin-1")
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        objs: dict[int, bytes] = {}
        def so(oid, data):
            objs[oid] = data.encode("latin-1", errors="replace") if isinstance(data, str) else data

        font_id = 1; cs = 2; ps = cs + len(pages); pages_id = ps + len(pages)
        cat_id = pages_id + 1; info_id = cat_id + 1

        so(font_id, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        cids, pids = [], []
        for pg in pages:
            sl = ["BT", f"/F1 {fs} Tf", f"{ml} {ph - mt} Td"]
            first = True
            for ln in pg:
                if not first: sl.append(f"0 -{lh} Td")
                first = False
                sl.append(f"({esc(ln)}) Tj")
            sl.append("ET")
            stream = "\n".join(sl)
            cid = cs + len(cids)
            so(cid, f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")
            cids.append(cid); pids.append(ps + len(pids))

        kids = " ".join(f"{p} 0 R" for p in pids)
        so(pages_id, f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
        for pid, cid in zip(pids, cids):
            so(pid, f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {pw} {ph}] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {cid} 0 R >>")
        so(cat_id,  f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
        so(info_id, f"<< /Title ({esc(self.title)}) /Producer (NamanDarshan CourseGen v5) "
                    f"/CreationDate (D:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}Z) >>")

        pdf_bytes = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for oid in range(1, info_id + 1):
            offsets.append(len(pdf_bytes))
            pdf_bytes.extend(f"{oid} 0 obj\n".encode())
            pdf_bytes.extend(objs[oid])
            pdf_bytes.extend(b"\nendobj\n")

        xref_off = len(pdf_bytes)
        pdf_bytes.extend(f"xref\n0 {info_id + 1}\n".encode())
        pdf_bytes.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            pdf_bytes.extend(f"{off:010d} 00000 n \n".encode())
        pdf_bytes.extend(
            f"trailer\n<< /Size {info_id + 1} /Root {cat_id} 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_off}\n%%EOF".encode()
        )
        output_path.write_bytes(pdf_bytes)
        return output_path


# ============================================================================
# COURSE GENERATOR AGENT
# ============================================================================

class CourseGeneratorAgent:

    def __init__(
        self,
        groq_api_key_2: Optional[str] = None,
        gemini_api_keys: Optional[list[str]] = None,
        gemini_model: Optional[str] = None,
        site_root: Optional[str] = None,
    ) -> None:
        self._groq_key2    = (groq_api_key_2 or GROQ_API_KEY_2).strip()
        self._gemini_model = gemini_model or DEFAULT_GEMINI_MODEL
        if gemini_api_keys:
            global _gem_cycle
            _gem_cycle = itertools.cycle(gemini_api_keys)
        self.site_root = (site_root or DEFAULT_SITE_ROOT).rstrip("/")

    # ------------------------------------------------------------------------
    # PUBLIC v5.1  generate_html_course_package()
    # ------------------------------------------------------------------------

    def generate_html_course_package(
        self,
        department: str,
        topic: Optional[str] = None,
        related_queries: Optional[list[str]] = None,
        output_dir: Optional[Path] = None,
        max_site_pages: int = 5,
        max_web_pages: int = 4,
        generate_pdf: bool = False,
        save_to_disk: bool = False,
    ) -> dict[str, Any]:
        dept = department.strip()
        top  = (topic or f"{dept} General Training").strip()
        print(f"\n  [CourseGen v5.1] Generating HTML course: {dept} | Topic: {top}")

        site_srcs = self._collect_site_sources(dept, max_pages=max_site_pages)
        web_srcs  = self._collect_related_web_sources(dept, related_queries or [], max_pages=max_web_pages)
        sop_srcs  = self._collect_sop_sources(dept)
        all_srcs  = [*site_srcs, *web_srcs, *sop_srcs] or [self._build_fallback_source(dept)]
        course_json = self._generate_html_course_json(dept, all_srcs, topic=top)
        course_json["department"] = dept

        modules    = course_json.get("modules", [])
        final_exam = course_json.get("final_exam", [])
        n          = len(modules)

        ts   = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        slug = _slugify(dept)
        course_json["slug"] = slug

        index_fn   = f"{slug}-index-{ts}.html"
        module_fns = [f"{slug}-module-{i+1:02d}-{ts}.html" for i in range(n)]
        exam_fn    = f"{slug}-final-exam-{ts}.html"

        mod_writer   = HtmlModulePageWriter()
        exam_writer  = HtmlFinalExamWriter()
        index_writer = HtmlCourseIndexWriter()

        # -- First pass: render with empty db_course_id -------------------
        module_html_strings: list[str] = []
        mod_results: list[dict]        = []

        for i, mod in enumerate(modules):
            html_str = mod_writer._render(
                mod, i + 1, n,
                course_json.get("title", f"{dept} Course"),
                dept, slug, index_fn,
                module_fns[i - 1] if i > 0 else None,
                module_fns[i + 1] if i < n - 1 else None,
                exam_fn,
                db_course_id="",
            )
            module_html_strings.append(html_str)
            print(f"  [CourseGen v5.1] Module {i+1}/{n} rendered in memory")

            mod_results.append({
                "module_index":  i + 1,
                "module_id":     mod.get("module_id", f"mod_{i+1}"),
                "title":         mod.get("title", f"Module {i+1}"),
                "duration":      mod.get("duration", ""),
                "lessons_count": len(mod.get("content", {}).get("lessons", [])),
                "quiz_count":    len(mod.get("quiz", [])),
                "html_filename": module_fns[i],
                "html_url":      "",
            })

        html_exam_str = exam_writer._render(
            final_exam,
            course_json.get("title", f"{dept} Course"),
            dept, slug, n, index_fn, db_course_id="",
        )
        course_json["db_course_id"] = ""
        html_index_str = index_writer._render(course_json, module_fns, exam_fn)

        print(f"  [CourseGen v5.1] All HTML rendered in memory (first pass)")

        # -- Persist to DB ------------------------------------------------
        db_course_id: str = ""
        _course_db = get_course_db()
        if _course_db is not None:
            try:
                module_htmls_for_db: dict[str, str] = {}
                for i, mod in enumerate(modules):
                    mod_id = mod.get("module_id", f"mod_{i+1}")
                    module_htmls_for_db[mod_id] = module_html_strings[i]

                db_course_id = _course_db.save_course(
                    course_metadata={
                        "title":       course_json.get("title", f"{dept} Course"),
                        "department":  dept,
                        "description": course_json.get("description", ""),
                        "duration":    course_json.get("duration", ""),
                        "level":       course_json.get("level", ""),
                        "audience":    course_json.get("audience", ""),
                    },
                    html_index=html_index_str,
                    module_htmls=module_htmls_for_db,
                    html_exam=html_exam_str,
                    course_json=course_json,
                )
                print(f"  [CourseGen v5.1] Saved to DB, course_id={db_course_id}")
            except Exception as _db_save_err:
                print(f"  [CourseGen v5.1] DB save failed ({_db_save_err}). Disk fallback.")
                save_to_disk = True

        # -- Second pass: re-render with real db_course_id in links -------
        # -- Second pass: re-render with real db_course_id in links -------
        if db_course_id:
            print(f"  [CourseGen v5.1] Re-rendering with db_course_id={db_course_id}")
            course_json["db_course_id"] = db_course_id
            module_html_strings_final: list[str] = []
            for i, mod in enumerate(modules):
                html_str = mod_writer._render(
                    mod, i + 1, n,
                    course_json.get("title", f"{dept} Course"),
                    dept, slug, index_fn,
                    module_fns[i - 1] if i > 0 else None,
                    module_fns[i + 1] if i < n - 1 else None,
                    exam_fn,
                    db_course_id=db_course_id,
                )
                module_html_strings_final.append(html_str)

            html_exam_final  = exam_writer._render(
                final_exam,
                course_json.get("title", f"{dept} Course"),
                dept, slug, n, index_fn, db_course_id=db_course_id,
            )
            html_index_final = index_writer._render(course_json, module_fns, exam_fn)

            # Push re-rendered HTML back to DB
            _course_db = get_course_db()
            if _course_db is not None:
                try:
                    _course_db.update_html(
                        db_course_id, html_index_final,
                        module_html_strings_final, html_exam_final,
                    )
                except Exception as _upd_err:
                    print(f"  [CourseGen v5.1] update_html failed ({_upd_err}).")
        else:
            # No DB or save failed  use first-pass HTML
            save_to_disk = True
            html_index_final          = html_index_str
            module_html_strings_final = module_html_strings
            html_exam_final           = html_exam_str

        # -- Fill download URLs -------------------------------------------
        for i, m in enumerate(mod_results):
            if db_course_id:
                m["html_url"] = f"/api/generated-courses/download/{db_course_id}/module/{m['module_index']}"
            else:
                m["html_url"] = f"/api/generated-courses/file/{module_fns[i]}"

        result: dict[str, Any] = {
            "success":         True,
            "format":          "html_multi",
            "db_course_id":    db_course_id,
            "department":      dept,
            "title":           course_json.get("title", f"{dept} Course"),
            "description":     course_json.get("description", ""),
            "duration":        course_json.get("duration", ""),
            "level":           course_json.get("level", ""),
            "audience":        course_json.get("audience", ""),
            "generated_at":    datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "index_html": {
                "html_filename": index_fn,
                "html_url": (f"/api/generated-courses/download/{db_course_id}/index"
                             if db_course_id else f"/api/generated-courses/file/{index_fn}"),
            },
            "pdf_url": (f"/api/generated-courses/download/{db_course_id}/index"
                        if db_course_id else f"/api/generated-courses/file/{index_fn}"),
            "module_htmls":   mod_results,
            "final_exam_html": {
                "html_filename": exam_fn,
                "html_url": (f"/api/generated-courses/download/{db_course_id}/exam"
                             if db_course_id else f"/api/generated-courses/file/{exam_fn}"),
            },
            # Backward compat
            "html_course": {
                "html_filename": index_fn,
                "html_url": (f"/api/generated-courses/download/{db_course_id}/index"
                             if db_course_id else f"/api/generated-courses/file/{index_fn}"),
            },
            "modules_count":    n,
            "final_exam_count": len(final_exam),
            "modules":          mod_results,
            "pdf_booklets":     [],
            "source_notes":     [s.title for s in all_srcs[:6]],
        }

        if save_to_disk:
            out_root = output_dir or OUTPUT_DIR
            out_root.mkdir(parents=True, exist_ok=True)
            (out_root / index_fn).write_text(html_index_final, encoding="utf-8")
            (out_root / exam_fn).write_text(html_exam_final, encoding="utf-8")
            for i, fn in enumerate(module_fns):
                html = (module_html_strings_final[i]
                        if i < len(module_html_strings_final)
                        else module_html_strings[i])
                (out_root / fn).write_text(html, encoding="utf-8")
            print(f"  [CourseGen v5.1] Files written to disk: {out_root}")
            result["index_html"]["html_path"]     = str(out_root / index_fn)
            result["final_exam_html"]["html_path"] = str(out_root / exam_fn)
            for i, m in enumerate(mod_results):
                m["html_path"] = str(out_root / module_fns[i])

        if generate_pdf:
            out_root = output_dir or OUTPUT_DIR
            result["pdf_booklets"] = self._generate_pdf_booklets(
                course_json, out_root, slug, ts, dept
            )

        return result

    # ------------------------------------------------------------------------
    # BACKWARD COMPAT
    # ------------------------------------------------------------------------

    def generate_course_package(
        self,
        department: str,
        related_queries: Optional[list[str]] = None,
        output_dir: Optional[Path] = None,
        generate_mcqs: bool = True,
        generate_pdf: bool = False,
    ) -> dict[str, Any]:
        result = self.generate_html_course_package(
            department=department,
            related_queries=related_queries,
            output_dir=output_dir,
            generate_pdf=generate_pdf,
        )
        result["format"]              = "html_multi"
        result["index_html_filename"] = result["index_html"]["html_filename"]
        result["index_html_path"]     = result["index_html"].get("html_path", "")
        result["modules_html"]        = result["module_htmls"]
        result["module_booklets"]     = result["module_htmls"]
        return result

    # ------------------------------------------------------------------------
    # PDF BOOKLETS
    # ------------------------------------------------------------------------

    def _generate_pdf_booklets(
        self, course_json: dict, out_root: Path, slug: str, ts: str, dept: str
    ) -> list[dict]:
        results    = []
        pdf_writer = BookletPdfWriter()
        for i, mod in enumerate(course_json.get("modules", []), 1):
            content     = mod.get("content", {})
            lessons_raw = content.get("lessons", [])
            lesson_exps = [
                LessonExplanation(
                    lesson_title=l.get("title", f"Lesson {j+1}"),
                    body=l.get("body", ""),
                    key_points=l.get("key_points", []),
                    real_world_example=l.get("example", ""),
                    do_and_dont={"do": content.get("do", []), "dont": content.get("dont", [])},
                )
                for j, l in enumerate(lessons_raw)
            ]
            booklet = ModuleBooklet(
                module_id=mod.get("module_id", f"mod_{i}"),
                module_index=i,
                module_title=mod.get("title", f"Module {i}"),
                department=dept,
                duration=mod.get("duration", "60 min"),
                introduction=content.get("introduction", ""),
                why_it_matters=content.get("why_it_matters", ""),
                goals=content.get("learning_objectives", []),
                lesson_explanations=lesson_exps,
                practice_activities=[],
                sop_checkpoints=[],
                module_recap=content.get("summary", ""),
                whats_next="Proceed to the next module.",
                generated_by="v5.1",
            )
            mod_slug = _slugify(mod.get("title", f"module-{i}"))
            pdf_fn   = f"{slug}-mod-{i:02d}-{mod_slug}-{ts}.pdf"
            pdf_path = out_root / pdf_fn
            pdf_writer.write(booklet, pdf_path)
            results.append({
                "module_index": i,
                "pdf_filename": pdf_fn,
                "pdf_url":      f"/api/generated-courses/file/{pdf_fn}",
            })
            print(f"  [CourseGen v5.1] PDF {i} -> {pdf_fn}")
        return results

    # ------------------------------------------------------------------------
    # AI GENERATION
    # ------------------------------------------------------------------------

    def _build_html_course_prompt(
        self, department: str, sources: list[SourceDocument], topic: str
    ) -> tuple[list[dict], str]:
        blocks = []
        for i, s in enumerate(sources[:6], 1):
            blocks.append(
                f"Source {i} [{s.source_type}]\nTitle: {s.title}\nURL: {s.url}\n"
                f"Content:\n{s.content[:2800]}\n"
            )
        sop_note = (
            "\n\nNote: SOP sources are included above. Ensure lessons directly reference "
            "these SOP steps, escalation paths, and operational checkpoints."
            if any(s.source_type.startswith("sop") for s in sources)
            else ""
        )
        user = (
            f"Department: {department}\n"
            f"Specific Topic: {topic}\n"
            f"Target Audience: {department} department employees at NamanDarshan\n"
            f"Level: Intermediate\n"
            f"Number of Modules: 5\n"
            f"Lessons per Module: minimum 5\n\n"
            "Use the source material below to make content specific to NamanDarshan's "
            "actual services and operations. Ground every lesson in real workflows.\n\n"
            + "\n\n".join(blocks)
            + sop_note
            + "\n\nGenerate the complete course JSON now. Return ONLY valid JSON."
        )
        messages = [
            {"role": "system", "content": HTML_COURSE_CONTENT_SYSTEM},
            {"role": "user",   "content": user},
        ]
        return messages, f"{HTML_COURSE_CONTENT_SYSTEM}\n\n{user}"

    def _is_complete_course(self, result: Any) -> bool:
        """Sanity check to ensure the AI actually generated content, not just a shell."""
        if not isinstance(result, dict):
            return False
        modules = result.get("modules")
        if not modules or not isinstance(modules, list) or len(modules) < 3:
            return False
        
        # Check if first module has at least one lesson with content
        first_mod = modules[0]
        content = first_mod.get("content", {})
        lessons = content.get("lessons", [])
        if not lessons or not isinstance(lessons, list) or len(lessons) < 1:
            return False
            
        # Basic check for a quiz (either in first module or final_exam)
        has_quiz = len(first_mod.get("quiz", [])) > 0 or len(result.get("final_exam", [])) > 0
        if not has_quiz:
            return False
            
        return True

    def _generate_html_course_json(
        self, department: str, sources: list[SourceDocument], topic: str
    ) -> dict:
        messages, flat = self._build_html_course_prompt(department, sources, topic=topic)
        
        # Try Groq (Fastest)
        result = self._call_groq_key2(messages)
        if self._is_complete_course(result):
            print("  [CourseGen] Groq generation SUCCESS (Complete course)")
            return result
        
        # Try Gemini (Fallback AI)
        print("  [CourseGen] Groq returned incomplete course. Trying Gemini fallback...")
        result = self._call_gemini(flat)
        if self._is_complete_course(result):
            print("  [CourseGen] Gemini generation SUCCESS (Complete course)")
            return result
            
        # Hard Fallback (Deterministic Rule-Based)
        print("  [CourseGen] AI generation failed or returned incomplete content. Using rule-based fallback.")
        return self._fallback_html_course_json(department, sources)

    def _fallback_html_course_json(
        self, department: str, sources: list[SourceDocument]
    ) -> dict:
        dept = department
        module_topics = [
            (f"{dept} Foundations & NamanDarshan Overview",
             [f"Understanding NamanDarshan's mission and services",
              f"Your role in the {dept} department",
              "SOP framework and why it matters",
              "Communication standards and escalation protocol",
              "Daily workflow rhythm and shift handover"]),
            (f"Core {dept} Workflows & SOPs",
             ["Reading and applying SOP documents",
              "Step-by-step task execution discipline",
              "Documentation practices and audit trails",
              "Handling exceptions and edge cases",
              "Escalation paths and when to use them"]),
            ("Service Quality & Pilgrim Experience",
             ["Quality standards at NamanDarshan",
              "Understanding pilgrim expectations",
              "Effective internal and external communication",
              "Feedback loops and continuous improvement",
              "Handling complaints and service recovery"]),
            ("Advanced Operations & Cross-Dept Coordination",
             ["Advanced workflows for complex scenarios",
              "Coordinating with other departments",
              "Performance metrics and KPIs for your role",
              "Technology tools and systems",
              "Continuous learning and career development"]),
            (f"{dept} Compliance, Ethics & Best Practices",
             ["Compliance requirements and legal awareness",
              "Data privacy and confidentiality",
              "Ethical decision-making in daily operations",
              "Incident reporting and corrective actions",
              "Building a culture of excellence"]),
        ]

        def _lesson(lt):
            return {
                "title": lt,
                "body": (
                    f"Understanding {lt.lower()} is essential for every {dept} team member at NamanDarshan. "
                    f"This topic sits at the intersection of operational excellence and the platform's mission: "
                    f"making sacred pilgrimage experiences seamless and accessible for millions of devotees "
                    f"across India. Without a deep grasp of {lt.lower()}, even well-intentioned team members "
                    f"can create friction in what should be a smooth spiritual journey.\n\n"
                    f"In practice, applying {lt.lower()} means following a structured approach. Begin by "
                    f"reviewing the relevant SOP document  not from memory, but fresh each time  then "
                    f"execute each step with care, logging actions as you go. This creates an auditable "
                    f"record that managers can review and that protects the team if questions arise later. "
                    f"Thoroughness here is never wasted; the few extra seconds spent documenting correctly "
                    f"can save hours of back-and-forth during reviews.\n\n"
                    f"The NamanDarshan context adds specific demands. Pilgrimage services are time-sensitive "
                    f"and emotionally significant for customers. A booking error on a VIP Darshan slot, for "
                    f"instance, can disrupt a family's once-in-a-lifetime trip. This means that {lt.lower()} "
                    f"must be executed not just accurately but promptly, with empathy for what each service "
                    f"means to the person on the other side of the transaction.\n\n"
                    f"Build proficiency through deliberate practice. Each time you complete a {lt.lower()} "
                    f"task, pause briefly to evaluate: did you follow the SOP exactly? Was documentation "
                    f"complete? Did any step create confusion that suggests the SOP needs improvement? Share "
                    f"these observations in team check-ins. The cumulative effect of small improvements, "
                    f"made consistently, is what separates a good team from an exceptional one.\n\n"
                    f"Finally, remember that expertise in {lt.lower()} earns trust. When managers and "
                    f"colleagues know you will handle this area reliably, they can delegate with confidence, "
                    f"creating space for you to take on higher-responsibility work and accelerate your growth "
                    f"within the {dept} department at NamanDarshan."
                ),
                "example": (
                    f"During the Char Dham Yatra season, the {dept} team received a surge of requests "
                    f"involving {lt.lower()}. One team member had recently completed refresher training on "
                    f"this exact topic. Rather than improvising, they opened the SOP, worked through each "
                    f"step methodically, and documented every action with a timestamp. When a query arose "
                    f"the following day about how a particular case had been handled, the complete audit "
                    f"trail meant the review was resolved in minutes rather than hours  and the pilgrim "
                    f"received a personalised follow-up that turned a potential complaint into a five-star review."
                ),
                "key_points": [
                    f"Always consult the SOP before executing {lt.lower()} tasks",
                    "Document every action with timestamps for full auditability",
                    "Escalate outside-scope situations via the defined escalation path",
                    "Empathy for pilgrim context elevates service quality",
                    "Share edge-case learnings to improve SOPs over time",
                    "Consistent accuracy builds trust and career opportunity",
                ],
                "pro_tip": (
                    f"If you find yourself unsure during a {lt.lower()} task, treat that uncertainty as "
                    f"a signal  stop, re-read the SOP section, and escalate if the SOP doesn't cover "
                    f"the scenario. Improvising without documentation creates downstream risk."
                ),
            }

        modules = []
        for mi, (mod_title, lessons_titles) in enumerate(module_topics):
            lessons = [_lesson(lt) for lt in lessons_titles]
            modules.append({
                "module_id": f"mod_{mi+1}",
                "title":     mod_title,
                "duration":  "75 min",
                "content": {
                    "introduction": (
                        f"Welcome to '{mod_title}', Module {mi+1} of your {dept} Learning Path at "
                        f"NamanDarshan. This module has been carefully designed to build the knowledge and "
                        f"practical skills you need to operate with confidence in your role. The content "
                        f"draws directly from NamanDarshan's service portfolio  VIP Darshan, Yatra packages, "
                        f"Online Puja, Prasad delivery, and Temple bookings  so every concept you study "
                        f"maps directly to situations you will encounter at your desk.\n\n"
                        f"Work through each lesson at your own pace. Pay special attention to the real-world "
                        f"examples and pro tips: these are drawn from actual scenarios the {dept} team has "
                        f"faced. The module ends with a short assessment quiz  you need 70% to pass, but "
                        f"treat it as a learning opportunity, not just a test. Your score is automatically "
                        f"recorded in the NamanDarshan Growth Report, supporting your performance review "
                        f"and career development."
                    ),
                    "why_it_matters": (
                        f"The {dept} department sits at the heart of NamanDarshan's promise to pilgrims. "
                        f"When your team operates at its best  following SOPs precisely, communicating "
                        f"proactively, and resolving issues before they escalate  devotees experience "
                        f"the seamless service they trusted NamanDarshan to deliver. Every task you "
                        f"complete well is a direct contribution to that experience. This module gives "
                        f"you the grounding to make that contribution consistently."
                    ),
                    "learning_objectives": [
                        f"Understand the scope and purpose of {mod_title} within {dept} operations",
                        "Apply SOP-backed steps accurately in real work scenarios",
                        "Document all actions with full auditability",
                        "Identify escalation triggers and respond via the correct path",
                        "Evaluate your own performance and contribute to SOP improvement",
                        f"Demonstrate empathy and professionalism in all {dept} tasks",
                    ],
                    "lessons": lessons,
                    "do": [
                        "Review the relevant SOP every time  never rely on memory alone",
                        "Document actions with timestamps, outcomes, and decision rationale",
                        "Escalate promptly via the defined escalation path when out of scope",
                        "Complete the module quiz  your score feeds the Growth Report directly",
                        "Share edge-case learnings in team check-ins to improve SOPs",
                    ],
                    "dont": [
                        "Skip steps in the SOP because they seem unnecessary that day",
                        "Delay documentation  it becomes impossible to reconstruct later",
                        "Attempt to resolve situations that are outside your authorisation level",
                        "Ignore small errors  they compound into customer-visible failures",
                        "Assume you know the answer without checking the SOP first",
                    ],
                    "case_study": {
                        "title": f"Festival Season Surge: {dept} Under Pressure",
                        "scenario": (
                            f"During the Navratri festival peak, the {dept} team at NamanDarshan handled "
                            f"a 340% increase in service requests over a 72-hour window. Two team members "
                            f"had recently completed their {mod_title} module training; two had not yet "
                            f"started. The difference in performance was immediately visible. The trained "
                            f"members worked through the surge methodically, following SOPs without cutting "
                            f"corners, logging every action, and escalating three edge cases that the "
                            f"untrained members had attempted to resolve independently  one of which, had "
                            f"it not been caught, would have caused a double-booking for a VIP Darshan slot "
                            f"on the most auspicious day of the festival.\n\n"
                            f"The team lead documented the outcomes at the end of the surge period. Average "
                            f"resolution time for the trained members was 28% faster. Error rate was 0% "
                            f"versus 4.2% for the untrained group. Most importantly, pilgrim satisfaction "
                            f"scores for transactions handled by trained members averaged 4.8/5 compared "
                            f"to 3.9/5 for the others  a gap entirely explained by process discipline "
                            f"and communication quality, not effort or intent."
                        ),
                        "outcome": (
                            f"The case made a compelling argument for making {mod_title} training "
                            f"mandatory before staff handle live requests during peak periods. The two "
                            f"undertrained members completed the module within the following week and "
                            f"reported that the SOP framework immediately reduced their cognitive load  "
                            f"they spent less mental energy improvising and more on delivering quality service. "
                            f"Lesson: structured knowledge directly translates to measurable performance."
                        ),
                    },
                    "summary": (
                        f"In this module, you explored the core principles behind {mod_title}. You learned "
                        f"how SOP adherence creates consistency, how documentation protects both the team "
                        f"and the business, and how even small behavioural shifts  reading before acting, "
                        f"logging before moving on, escalating before improvising  compound into dramatically "
                        f"better outcomes for NamanDarshan's pilgrims. The case study showed these principles "
                        f"in action under real pressure. Carry these habits into your daily work: they are "
                        f"the foundation of excellence in the {dept} department."
                    ),
                    "knowledge_check": [
                        {"question": f"What is the first step before executing any {dept} task?",
                         "answer":   "Review the relevant SOP document  not from memory, but fresh each time  then execute each step while logging your actions."},
                        {"question": "Why should you never skip documentation even for routine tasks?",
                         "answer":   "Documentation creates an auditable record that protects the team during reviews, enables manager oversight, and prevents errors from recurring."},
                        {"question": "When should you escalate a situation rather than resolving it yourself?",
                         "answer":   "Any time the situation falls outside the defined SOP steps, outside your authorisation level, or involves risk you are not trained to assess independently."},
                        {"question": "How does consistent SOP adherence benefit your career at NamanDarshan?",
                         "answer":   "Reliability earns trust. When managers know you execute correctly every time, they delegate higher-value work to you, accelerating your growth and responsibilities."},
                    ],
                },
                "quiz": [
                    {"id": f"m{mi+1}_q1","question": f"During a Yatra booking surge, a {dept} team member encounters a scenario not covered by the standard SOP. What is the correct first response?","options": ["Log the scenario and escalate via the defined escalation path immediately","Resolve it independently to avoid delays","Wait until end of shift and mention it to the manager","Ignore it if it seems minor"],"correct_answer": "Log the scenario and escalate via the defined escalation path immediately","correct_index": 0,"explanation": f"Out-of-scope situations require immediate escalation and documentation. Attempting independent resolution without authority creates risk for both the pilgrim and the {dept} team."},
                    {"id": f"m{mi+1}_q2","question": "A VIP Darshan slot booking shows conflicting information between two system records. Before acting, the team member should:","options": ["Cross-reference both records, document the discrepancy, and escalate per SOP","Update the newer record and assume it is correct","Cancel both records and ask the pilgrim to rebook","Proceed with whichever record appears first"],"correct_answer": "Cross-reference both records, document the discrepancy, and escalate per SOP","correct_index": 0,"explanation": "Data conflicts require systematic verification, not assumption. Documenting and escalating protects the pilgrim's experience and creates an audit trail for the discrepancy."},
                    {"id": f"m{mi+1}_q3","question": f"What does consistent documentation practice achieve for the {dept} department at NamanDarshan?","options": ["Creates audit trails, enables manager oversight, and prevents recurring errors","Only useful during peak periods and festivals","Required only for escalated cases, not routine tasks","Primarily for the IT team to reference"],"correct_answer": "Creates audit trails, enables manager oversight, and prevents recurring errors","correct_index": 0,"explanation": "Documentation is valuable for every task, not just exceptions. It enables continuous improvement, protects the team, and gives managers the visibility they need."},
                    {"id": f"m{mi+1}_q4","question": "A pilgrim contacts the team upset about a delayed Prasad delivery. The best immediate response combines:","options": ["Empathetic acknowledgment + immediate escalation + follow-up commitment","Apologising repeatedly without taking action","Explaining the delay is outside the team's control","Asking the pilgrim to recontact in 24 hours"],"correct_answer": "Empathetic acknowledgment + immediate escalation + follow-up commitment","correct_index": 0,"explanation": "Service recovery requires three elements: acknowledge the frustration, take immediate action via the escalation path, and commit to a follow-up."},
                    {"id": f"m{mi+1}_q5","question": "After completing a challenging task correctly during a busy shift, the most valuable next step is:","options": ["Note any SOP gaps or edge cases encountered and raise them in the next team check-in","Move immediately to the next task without reflection","Report the challenge to HR as a workload concern","Congratulate yourself and wait for manager recognition"],"correct_answer": "Note any SOP gaps or edge cases encountered and raise them in the next team check-in","correct_index": 0,"explanation": "Individual experiences are organisational intelligence. Raising edge cases in check-ins allows the SOP to be updated, preventing future team members from facing the same challenge unprepared."},
                    {"id": f"m{mi+1}_q6","question": "What is the significance of the 70% pass mark on module quizzes?","options": ["It indicates sufficient operational knowledge to apply the module's concepts safely in live work","It is an arbitrary HR requirement with no operational significance","It only matters for new joiners, not experienced staff","Passing on the first attempt is required  retries are not counted"],"correct_answer": "It indicates sufficient operational knowledge to apply the module's concepts safely in live work","correct_index": 0,"explanation": "70% is the threshold that indicates a team member has understood the module well enough to apply its concepts without creating operational risk."},
                    {"id": f"m{mi+1}_q7","question": f"A new {dept} team member asks why they should read the SOP again before a routine task they have done many times. The best answer is:","options": ["SOPs may have been updated, and consistent reference prevents memory-based errors that compound over time","They should trust their memory  re-reading wastes time","It is only required during onboarding, not ongoing work","SOPs are only for managers to verify, not for daily use"],"correct_answer": "SOPs may have been updated, and consistent reference prevents memory-based errors that compound over time","correct_index": 0,"explanation": "SOPs evolve as the business learns. Reading them consistently also prevents the natural degradation of memory-based execution, where small deviations accumulate into significant process drift."},
                    {"id": f"m{mi+1}_q8","question": "Cross-department coordination at NamanDarshan works best when:","options": ["Each team uses documented handover notes and follows the shared escalation path","Teams communicate informally and resolve issues without documentation","Departments work independently to avoid cross-team confusion","Only managers handle cross-department communication"],"correct_answer": "Each team uses documented handover notes and follows the shared escalation path","correct_index": 0,"explanation": "Documented handovers and shared escalation paths ensure that information doesn't get lost at team boundaries  one of the most common sources of customer-facing failures in service businesses."},
                ],
            })

        return {
            "title":       f"{dept} Department Learning Path",
            "description": (
                f"A comprehensive, SOP-backed training programme for the {dept} team at NamanDarshan. "
                f"Covers foundations, workflows, service quality, advanced operations, and compliance  "
                f"grounded in real NamanDarshan scenarios."
            ),
            "duration":   "6-8 hours",
            "level":      "Intermediate",
            "audience":   f"New and existing {dept} department employees at NamanDarshan",
            "department": dept,
            "modules":    modules,
            "final_exam": self._build_fallback_final_exam(dept),
        }

    def _build_fallback_final_exam(self, dept: str) -> list[dict]:
        return [
            {"id":"fe_1","question":f"What is the most important habit for a {dept} team member at NamanDarshan?","options":["Consistent SOP adherence combined with thorough, timestamped documentation","Completing tasks quickly without review","Memorising all SOPs from cover to cover","Minimising communication with other departments"],"correct_answer":"Consistent SOP adherence combined with thorough, timestamped documentation","correct_index":0,"explanation":"SOP adherence + documentation is the bedrock of operational quality and the single most important daily discipline."},
            {"id":"fe_2","question":"During a VIP Darshan booking conflict, the first action a team member should take is:","options":["Log the issue with full details and escalate immediately via the defined path","Try to resolve it independently to save time","Inform the pilgrim to rebook for a different date","Ignore it if it appears minor and move to the next task"],"correct_answer":"Log the issue with full details and escalate immediately via the defined path","correct_index":0,"explanation":"Booking conflicts affecting VIP Darshan slots are high-impact. Logging + immediate escalation ensures accountability and fast resolution with no pilgrim-facing disruption."},
            {"id":"fe_3","question":"A 70% or above score on a module quiz indicates:","options":["The learner has sufficient knowledge to apply the module's concepts in live operational scenarios","The learner has memorised all SOP text verbatim","The learner no longer requires manager guidance on any topic","The learner can skip all future training modules"],"correct_answer":"The learner has sufficient knowledge to apply the module's concepts in live operational scenarios","correct_index":0,"explanation":"70% signals adequate understanding for safe application. It is a minimum, not a ceiling  continued learning beyond passing is expected and encouraged."},
            {"id":"fe_4","question":"Which of the following is a core NamanDarshan service?","options":["VIP Darshan, Yatra packages, Online Puja, and Prasad delivery","Movie ticketing and hotel reservations","Grocery delivery and subscription boxes","Digital marketing and SEO consultancy"],"correct_answer":"VIP Darshan, Yatra packages, Online Puja, and Prasad delivery","correct_index":0,"explanation":"NamanDarshan specialises in pilgrimage facilitation and spiritual service delivery  all team members should be fluent in the core service portfolio."},
            {"id":"fe_5","question":"Why should team members share edge-case observations during check-ins?","options":["To improve SOPs and training so the whole team benefits from individual learning","To demonstrate personal initiative to managers","To reduce their own future workload by getting others to handle similar cases","Because it is a mandatory HR compliance requirement"],"correct_answer":"To improve SOPs and training so the whole team benefits from individual learning","correct_index":0,"explanation":"Individual observations are collective intelligence. Shared systematically, they drive SOP improvement and make the entire team more capable over time."},
            {"id":"fe_6","question":"What does the NamanDarshan Growth Report track?","options":["Module quiz scores, completion dates, and pass/fail status for each team member","Social media engagement metrics","Monthly revenue performance by department","Website traffic from pilgrimage-related searches"],"correct_answer":"Module quiz scores, completion dates, and pass/fail status for each team member","correct_index":0,"explanation":"The Growth Report is the learning performance record. Quiz scores are automatically posted when a module is completed, making the report a real-time reflection of each team member's training progress."},
            {"id":"fe_7","question":"Which behaviour most directly damages pilgrim trust at NamanDarshan?","options":["Providing inaccurate information or failing to follow up on a committed action","Taking slightly longer than expected to resolve a routine request","Escalating a query rather than resolving it independently","Asking a pilgrim clarifying questions before acting"],"correct_answer":"Providing inaccurate information or failing to follow up on a committed action","correct_index":0,"explanation":"Trust is built on accuracy and reliability. Inaccurate information or broken follow-up commitments are the two most common causes of pilgrim complaints."},
            {"id":"fe_8","question":"When documentation is incomplete, the primary operational risk is:","options":["Inability to reconstruct what happened during audits, reviews, or disputes","Increased storage costs in operational systems","Slower system performance during peak periods","Reduced marketing effectiveness"],"correct_answer":"Inability to reconstruct what happened during audits, reviews, or disputes","correct_index":0,"explanation":"Incomplete documentation makes it impossible to verify what occurred, resolve disputes fairly, or identify the root cause of errors."},
            {"id":"fe_9","question":"Cross-department coordination at NamanDarshan succeeds when teams:","options":["Use documented handover notes and follow the shared escalation path consistently","Communicate informally to move quickly without bureaucracy","Allow only managers to communicate across department boundaries","Resolve every issue within the originating department before escalating"],"correct_answer":"Use documented handover notes and follow the shared escalation path consistently","correct_index":0,"explanation":"Documented handovers prevent information loss at team boundaries, the most frequent source of errors in multi-team service delivery."},
            {"id":"fe_10","question":"A pilgrim leaves a negative review about their Online Puja experience. The correct team response is:","options":["Acknowledge, investigate using documentation records, resolve root cause, and follow up with the pilgrim","Delete the review and offer a discount for the next booking","Escalate to senior management only and await instructions","Do nothing  negative reviews are normal in service businesses"],"correct_answer":"Acknowledge, investigate using documentation records, resolve root cause, and follow up with the pilgrim","correct_index":0,"explanation":"Every complaint is a data point and a recovery opportunity. Following up with the pilgrim demonstrates accountability and often converts detractors to advocates."},
            {"id":"fe_11","question":"The primary purpose of an SOP at NamanDarshan is:","options":["To ensure every team member executes tasks consistently, safely, and in line with quality standards","To reduce the number of staff needed by automating decisions","To create paperwork that satisfies external auditors","To prevent team members from exercising any independent judgment"],"correct_answer":"To ensure every team member executes tasks consistently, safely, and in line with quality standards","correct_index":0,"explanation":"SOPs standardise quality. They are the mechanism through which NamanDarshan's service promise is reliably delivered regardless of which team member handles a given task."},
            {"id":"fe_12","question":"Which mindset best describes a high-performing NamanDarshan team member?","options":["Process-disciplined, documentation-consistent, and proactively escalating  while remaining empathetic to pilgrim needs","Task-focused and fast, minimising time spent on documentation and checks","Autonomous and innovative, rewriting procedures when they seem inefficient","Cautious and risk-averse, declining any task that isn't explicitly in the SOP"],"correct_answer":"Process-disciplined, documentation-consistent, and proactively escalating  while remaining empathetic to pilgrim needs","correct_index":0,"explanation":"Excellence at NamanDarshan combines technical process discipline with genuine care for pilgrims. Neither quality alone is sufficient  the combination is what creates consistently outstanding service."},
        ]

    # ------------------------------------------------------------------------
    # AI CALLING
    # ------------------------------------------------------------------------

    def _call_groq_key2(self, messages: list[dict]) -> Optional[dict]:
        if not self._groq_key2:
            return None
        payload = {
            "model": DEFAULT_GROQ_MODEL_2,
            "temperature": 0.35,
            "response_format": {"type": "json_object"},
            "messages": messages,
            "max_tokens": 8000,
        }
        headers = {
            "Authorization": f"Bearer {self._groq_key2}",
            "Content-Type": "application/json",
        }
        try:
            if requests is not None:
                r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
                r.raise_for_status()
                raw = r.json()
            else:
                req = Request(GROQ_API_URL, data=json.dumps(payload).encode(), headers=headers, method="POST")
                with urlopen(req, timeout=DEFAULT_TIMEOUT) as r:
                    raw = json.loads(r.read().decode())
            text = raw.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            return json.loads(_strip_fences(text))
        except Exception:
            return None

    def _call_gemini(self, flat_prompt: str) -> Optional[dict]:
        if not GEMINI_KEYS:
            return None
        payload = {
            "contents": [{"parts": [{"text": flat_prompt}]}],
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }
        tried: set[str] = set()
        while len(tried) < len(GEMINI_KEYS):
            key = _next_gemini_key()
            if key in tried:
                continue
            tried.add(key)
            url = f"{GEMINI_API_BASE}/models/{self._gemini_model}:generateContent?key={key}"
            try:
                if requests is not None:
                    r = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
                    r.raise_for_status()
                    data = r.json()
                else:
                    req = Request(url, data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                    with urlopen(req, timeout=DEFAULT_TIMEOUT) as r:
                        data = json.loads(r.read().decode())
                text = (data.get("candidates", [{}])[0]
                        .get("content", {}).get("parts", [{}])[0].get("text", "{}"))
                return json.loads(_strip_fences(text))
            except Exception as exc:
                if "429" in str(exc):
                    time.sleep(2)
                continue
        return None

    # ------------------------------------------------------------------------
    # SOURCE COLLECTION
    # ------------------------------------------------------------------------

    def _build_fallback_source(self, department: str) -> SourceDocument:
        return SourceDocument(
            source_type="fallback_template",
            title=f"{department} Training Template",
            url="internal://fallback",
            content=f"{department} department baseline training for NamanDarshan.",
        )

    def _collect_site_sources(self, department: str, max_pages: int) -> list[SourceDocument]:
        keywords = [_slugify(department), department.lower(), "course", "training", "darshan", "puja", "yatra"]
        try:
            homepage_html = _http_get(self.site_root)
        except Exception:
            return []
        internal = [l for l in _extract_links(self.site_root, homepage_html)
                    if urlparse(l).netloc.endswith(urlparse(self.site_root).netloc)]
        ranked   = sorted(_dedupe_urls(internal), key=lambda u: _score_url(u, keywords), reverse=True)
        selected = [self.site_root] + ranked[:max(0, max_pages - 1)]
        sources: list[SourceDocument] = []
        for url in selected:
            try:
                html    = homepage_html if url == self.site_root else _http_get(url)
                content = _visible_text(html)[:6000]
                if content:
                    sources.append(SourceDocument("namandarshan_site", _extract_title(url, html), url, content))
            except Exception:
                continue
        return sources

    def _collect_related_web_sources(
        self, department: str, related_queries: list[str], max_pages: int
    ) -> list[SourceDocument]:
        queries = related_queries or [
            f"{department} training best practices",
            f"{department} SOP pilgrimage services India",
        ]
        sources: list[SourceDocument] = []
        for query in queries[:max_pages]:
            search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            try:
                html = _http_get(search_url)
            except Exception:
                continue
            result_links = []
            if BeautifulSoup:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("a.result__a"):
                    href = a.get("href", "").strip()
                    if href:
                        result_links.append(href)
            else:
                result_links = re.findall(r'class="result__a".*?href="([^"]+)"', html)
            for link in _dedupe_urls(result_links)[:1]:
                try:
                    pg      = _http_get(link)
                    content = _visible_text(pg)[:4000]
                    if content:
                        sources.append(SourceDocument("web_context", _extract_title(link, pg), link, content))
                    break
                except Exception:
                    continue
        return sources

    def _collect_sop_sources(self, department: str) -> list[SourceDocument]:
        norm    = department.strip().lower()
        sources: list[SourceDocument] = []
        for sop in load_sops():
            if sop.department.strip().lower() != norm:
                continue
            parts = [sop.title, *sop.steps]
            if sop.escalation:
                parts.append(f"Escalation: {sop.escalation}")
            sources.append(SourceDocument(
                "sop_knowledge", sop.title,
                f"sop://{_slugify(sop.department)}/{_slugify(sop.title)}",
                " ".join(parts),
            ))
        if ORIGINAL_SOPS_DIR.exists():
            for pdf in ORIGINAL_SOPS_DIR.glob("*.pdf"):
                # If it's the comprehensive SOP, or matches the department, include it
                if "comprehensive" in pdf.name.lower() or norm in pdf.stem.lower():
                    # Extract raw text from the PDF to provide as context
                    try:
                        from agents.AIChat import extract_pdf_chunks
                        chunks = extract_pdf_chunks(pdf)
                        content = "\n\n".join([c.text for c in chunks])
                    except Exception as e:
                        print(f"  [CourseGen] Warning: Could not extract text from {pdf.name}: {e}")
                        content = f"SOP PDF: {pdf.name} (Text extraction failed)"
                    
                    sources.append(SourceDocument(
                        "sop_pdf", pdf.stem.replace("_", " ").title(),
                        str(pdf), content,
                    ))
        return sources

    # ------------------------------------------------------------------------
    # LEGACY v3 METHODS
    # ------------------------------------------------------------------------

    def generate_department_course(
        self, department, related_queries=None, max_site_pages=5, max_web_pages=4,
        generate_mcqs=True, generate_booklets=False,
    ):
        dept      = department.strip()
        site_srcs = self._collect_site_sources(dept, max_pages=max_site_pages)
        web_srcs  = self._collect_related_web_sources(dept, related_queries or [], max_pages=max_web_pages)
        sop_srcs  = self._collect_sop_sources(dept)
        all_srcs  = [*site_srcs, *web_srcs, *sop_srcs] or [self._build_fallback_source(dept)]
        course_json = self._generate_html_course_json(dept, all_srcs)
        modules     = course_json.get("modules", [])
        return GeneratedCourse(
            department=dept,
            generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            title=course_json.get("title", f"{dept} Learning Path"),
            summary=course_json.get("description", ""),
            audience=course_json.get("audience", f"{dept} team members"),
            prerequisites=[], learning_objectives=[], daily_workflows=[],
            modules=_ensure_module_list(modules),
            assessments=[], quiz_questions=[], manager_review_checklist=[],
            youtube_links=[],
            source_notes=[s.title for s in all_srcs[:6]],
            raw_sources=all_srcs,
        )

    def _mcq_to_dict(self, mcq: ModuleMCQ) -> dict:
        return {
            "module_title":  mcq.module_title,
            "module_index":  mcq.module_index,
            "generated_by":  mcq.generated_by,
            "questions": [
                {"id": q.id, "question": q.question, "options": q.options,
                 "correctOptionIndex": q.correct_option_index, "explanation": q.explanation}
                for q in mcq.questions
            ],
        }


# ============================================================================
# FastAPI ROUTER
# ============================================================================

def _make_router():
    try:
        from fastapi import APIRouter, HTTPException
        from fastapi.responses import HTMLResponse, StreamingResponse
        from pydantic import BaseModel
        import io as _io

        router = APIRouter(prefix="/api/generated-courses", tags=["courses"])
        _agent = CourseGeneratorAgent()

        class GenerateCourseRequest(BaseModel):
            department: str
            related_queries: Optional[list[str]] = None
            generate_pdf: bool = False
            save_to_disk: bool = False

        class RecordProgressRequest(BaseModel):
            learner_id: str
            course_id: str           # <- str (MongoDB UUID)
            module_id: str
            module_title: str
            department: str
            score: int
            passed: bool
            source: str = "html_module"

        @router.post("/generate")
        async def generate_course(req: GenerateCourseRequest):
            try:
                # Force generation of physical files so they can be served via /api/generated-courses/file/
                return _agent.generate_html_course_package(
                    department=req.department,
                    related_queries=req.related_queries,
                    generate_pdf=True,
                    save_to_disk=True,
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/list")
        async def list_courses(department: Optional[str] = None):
            _db = get_course_db()
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.list_courses(department or "")

        @router.get("/search")
        async def search_courses(q: str, department: Optional[str] = None):
            _db = get_course_db()
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.search_courses(q, department or "")

        @router.get("/stats/db")
        async def db_stats():
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.get_db_stats()

        @router.get("/{course_id}/meta")
        async def get_course_meta(course_id: str):          # <- str
            _db = get_course_db()
            if _db is None: raise HTTPException(503, "DB not available")
            course = _db.get_course(course_id)
            if not course: raise HTTPException(404, "Course not found")
            modules = _db.get_modules(course_id)
            for m in modules:
                m.pop("html_content", None)
                m.pop("module_json", None)
            course.pop("html_index", None)
            course.pop("html_exam", None)
            course.pop("course_json", None)
            return {"course": course, "modules": modules}

        @router.get("/download/{course_id}/index", response_class=HTMLResponse)
        async def download_index(course_id: str, as_file: bool = False):   # <- str
            _db = get_course_db()
            if _db is None: raise HTTPException(503, "DB not available")
            html, filename = _db.get_html_for_download(course_id, "index")
            if not html: raise HTTPException(404, "Index HTML not found")
            if as_file:
                return StreamingResponse(
                    _io.BytesIO(html.encode("utf-8")), media_type="text/html",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
            return HTMLResponse(content=html)

        @router.get("/download/{course_id}/exam", response_class=HTMLResponse)
        async def download_exam(course_id: str, as_file: bool = False):    # <- str
            _db = get_course_db()
            if _db is None: raise HTTPException(503, "DB not available")
            html, filename = _db.get_html_for_download(course_id, "exam")
            if not html: raise HTTPException(404, "Exam HTML not found")
            if as_file:
                return StreamingResponse(
                    _io.BytesIO(html.encode("utf-8")), media_type="text/html",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
            return HTMLResponse(content=html)

        @router.get("/download/{course_id}/module/{module_index}", response_class=HTMLResponse)
        async def download_module(course_id: str, module_index: int, as_file: bool = False):
            _db = get_course_db()
            if _db is None: raise HTTPException(503, "DB not available")
            html, filename = _db.get_html_for_download(course_id, f"module:{module_index}")
            if not html: raise HTTPException(404, f"Module {module_index} HTML not found")
            if as_file:
                return StreamingResponse(
                    _io.BytesIO(html.encode("utf-8")), media_type="text/html",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
            return HTMLResponse(content=html)

        @router.get("/download/{course_id}/all-files")
        async def download_all_files(course_id: str):       # <- str
            if _db is None: raise HTTPException(503, "DB not available")
            written = _db.write_to_disk(course_id, OUTPUT_DIR)
            return {"course_id": course_id, "files_written": len(written),
                    "paths": {k: str(v) for k, v in written.items()}}

        @router.post("/progress")
        async def record_progress(req: RecordProgressRequest):
            if _db is None: raise HTTPException(503, "DB not available")
            _db.record_progress(
                learner_id=req.learner_id, course_id=req.course_id,
                module_id=req.module_id, module_title=req.module_title,
                department=req.department, score=req.score,
                passed=req.passed, source=req.source,
            )
            if req.module_id == "final_exam" and req.passed:
                _db.issue_certificate(req.learner_id, req.course_id, req.score)
            return {"status": "recorded"}

        @router.get("/progress/{learner_id}")
        async def get_progress(learner_id: str, course_id: Optional[str] = None):  # <- str
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.get_learner_progress(learner_id, course_id or "")

        @router.get("/stats/{course_id}")
        async def get_stats(course_id: str):                # <- str
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.get_course_stats(course_id)

        @router.get("/leaderboard/{course_id}")
        async def get_leaderboard(course_id: str, limit: int = 10):  # <- str (no leaderboard in mongo yet)
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.get_course_stats(course_id)  # fallback to stats

        @router.get("/certificates/{learner_id}")
        async def list_certs(learner_id: str):
            if _db is None: raise HTTPException(503, "DB not available")
            return _db.list_certificates(learner_id)

        @router.get("/{course_id}/assessments")
        async def get_assessments(course_id: str):          # <- str
            if _db is None: raise HTTPException(503, "DB not available")
            modules = _db.get_modules(course_id)
            return [{"module_index": m.get("module_index"), "module_title": m.get("title", "")}
                    for m in modules]

        @router.get("/{course_id}/final-exam-questions")
        async def get_final_exam_questions(course_id: str):  # <- str
            if _db is None: raise HTTPException(503, "DB not available")
            course = _db.get_course(course_id)
            if not course: raise HTTPException(404, "Course not found")
            cj = course.get("course_json", {})
            return cj.get("final_exam", [])

        @router.delete("/{course_id}")
        async def delete_course(course_id: str, hard: bool = False):  # <- str
            if _db is None: raise HTTPException(503, "DB not available")
            ok = _db.delete_course(course_id) if hard else _db.archive_course(course_id)
            if not ok: raise HTTPException(404, "Course not found")
            return {"status": "deleted" if hard else "archived", "course_id": course_id}

        return router

    except ImportError:
        return None


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    department = input("Department name: ").strip()
    if not department:
        raise SystemExit("Department is required.")

    print(f"\n[CourseGen v5.1] Department : {department}")
    print(f"[CourseGen v5.1] Groq Key 2 : {'configured' if GROQ_API_KEY_2 else 'NOT SET  will use fallback'}")
    print(f"[CourseGen v5.1] Gemini     : {len(GEMINI_KEYS)} key(s)")
    print(f"[CourseGen v5.1] Database   : {'MongoDB connected' if _course_db else 'NOT AVAILABLE  disk mode'}")

    pdf_opt  = input("Also generate PDF booklets? (download-only) [y/N]: ").strip().lower()
    disk_opt = input("Also write HTML files to disk? [y/N]: ").strip().lower()
    gen_pdf  = pdf_opt  == "y"
    to_disk  = disk_opt == "y"

    agent  = CourseGeneratorAgent()
    result = agent.generate_html_course_package(
        department, generate_pdf=gen_pdf, save_to_disk=to_disk
    )

    print(f"\n[OK] Course generated: {result['title']}")
    print(f"   DB Course ID : {result['db_course_id']}")
    print(f"   Index URL    : {result['index_html']['html_url']}")
    for m in result["module_htmls"]:
        print(f"   Module {m['module_index']:02d}     : {m['html_url']}  ({m['lessons_count']} lessons, {m['quiz_count']} quiz Qs)")
    print(f"   Final Exam   : {result['final_exam_html']['html_url']}")
    if result.get("pdf_booklets"):
        print(f"   PDFs         : {len(result['pdf_booklets'])} booklet(s) generated")
    if to_disk:
        print(f"\n   Disk files   : {OUTPUT_DIR}")
    else:
        print(f"\n   Serve HTML   : /api/generated-courses/download/{result['db_course_id']}/index")


if __name__ == "__main__":
    main()
# -- Exported Router -----------------------------------------------------------
router = _make_router()
