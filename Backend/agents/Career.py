"""
Career Portal - FastAPI Router
Naman LMS | career.py
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, cast
import os, json, httpx, io
from groq import Groq
import google.generativeai as genai
from google.generativeai import GenerativeModel, configure  # type: ignore
from groq.types.chat import ChatCompletionMessageParam

router = APIRouter(prefix="/api/career", tags=["Career Portal"])

# -- Init AI clients ------------------------------------------------------------
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
if _GEMINI_KEY:
    configure(api_key=_GEMINI_KEY)
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# -- Pydantic Models ------------------------------------------------------------

class JobSearchParams(BaseModel):
    query: Optional[str] = ""
    department: Optional[str] = "all"
    type: Optional[str] = "all"   # full-time | part-time | contract
    page: int = 1
    limit: int = 12


class ApplyRequest(BaseModel):
    job_id: str
    employee_id: str
    cover_note: Optional[str] = ""


class InterviewMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class InterviewRequest(BaseModel):
    job_role: str
    department: str
    history: list[InterviewMessage]
    user_answer: str


class AssessmentRequest(BaseModel):
    job_role: str
    question: str
    answer: str


class CVData(BaseModel):
    full_name: str
    email: str
    phone: str
    location: str
    summary: str
    experience: list[dict]
    education: list[dict]
    skills: list[str]
    certifications: Optional[list[str]] = []


class ATSOptimizeRequest(BaseModel):
    job_description: str
    cv_data: CVData


class PDFRequest(BaseModel):
    cv_data: CVData
    template: str = "classic"


# -- Mock DB (replace with real DB queries) -------------------------------------

JOBS_DB = [
    {
        "id": "JOB001",
        "title": "Senior Yatra Operations Manager",
        "department": "Operations",
        "location": "Varanasi / Remote",
        "type": "full-time",
        "posted": "2025-04-01",
        "deadline": "2025-04-30",
        "description": "Lead the end-to-end Yatra package operations, coordinating with temple authorities and transport partners.",
        "requirements": ["5+ years ops experience", "Temple circuit knowledge", "Team leadership"],
        "salary_range": "Rs. 8L - Rs. 12L",
        "is_internal": True,
        "applicants": 4,
        "status": "open",
    },
    {
        "id": "JOB002",
        "title": "AI/ML Engineer - Darshan Tech",
        "department": "Technology",
        "location": "Remote",
        "type": "full-time",
        "posted": "2025-04-03",
        "deadline": "2025-05-15",
        "description": "Build AI features for our NamanDarshan platform including live darshan scheduling and recommendation engines.",
        "requirements": ["Python", "FastAPI", "LLM integration", "React"],
        "salary_range": "Rs. 10L - Rs. 18L",
        "is_internal": False,
        "applicants": 12,
        "status": "open",
    },
    {
        "id": "JOB003",
        "title": "VIP Darshan Relationship Manager",
        "department": "Client Services",
        "location": "Delhi / Haridwar",
        "type": "full-time",
        "posted": "2025-03-28",
        "deadline": "2025-04-20",
        "description": "Manage premium VIP darshan bookings and provide white-glove service to high-value clients.",
        "requirements": ["CRM experience", "Fluent Hindi & English", "Spiritual sensitivity"],
        "salary_range": "Rs. 5L - Rs. 9L",
        "is_internal": True,
        "applicants": 7,
        "status": "open",
    },
    {
        "id": "JOB004",
        "title": "Digital Marketing Lead - Online Puja",
        "department": "Marketing",
        "location": "Remote",
        "type": "full-time",
        "posted": "2025-04-05",
        "deadline": "2025-05-01",
        "description": "Drive user acquisition and retention for Online Puja services via SEO, social media, and influencer partnerships.",
        "requirements": ["3+ years digital marketing", "Meta/Google Ads", "Content strategy"],
        "salary_range": "Rs. 6L - Rs. 10L",
        "is_internal": False,
        "applicants": 9,
        "status": "open",
    },
    {
        "id": "JOB005",
        "title": "Finance & Accounts Executive",
        "department": "Finance",
        "location": "Patna",
        "type": "full-time",
        "posted": "2025-04-02",
        "deadline": "2025-04-25",
        "description": "Manage AP/AR, GST filing, and financial reporting for the NamanDarshan group entities.",
        "requirements": ["B.Com/CA Inter", "Tally/SAP", "GST knowledge"],
        "salary_range": "Rs. 4L - Rs. 7L",
        "is_internal": True,
        "applicants": 3,
        "status": "open",
    },
    {
        "id": "JOB006",
        "title": "Content Creator - Spiritual & Travel",
        "department": "Content",
        "location": "Remote",
        "type": "contract",
        "posted": "2025-04-04",
        "deadline": "2025-04-28",
        "description": "Create compelling blog, video, and social content around India's pilgrimage circuit and temple culture.",
        "requirements": ["Strong Hindi writing", "Video editing", "Pilgrimage knowledge"],
        "salary_range": "Rs. 2.5L - Rs. 5L",
        "is_internal": False,
        "applicants": 21,
        "status": "open",
    },
]

DEPARTMENTS = ["Operations", "Technology", "Client Services", "Marketing", "Finance", "Content", "HR"]

INTERVIEW_QUESTIONS_BY_ROLE = {
    "default": [
        "Tell me about yourself and why you want to join NamanDarshan.",
        "Describe a challenging project you led and how you overcame obstacles.",
        "How do you handle tight deadlines with multiple competing priorities?",
        "Where do you see yourself in 5 years?",
        "What do you know about our VIP Darshan and Yatra services?",
    ]
}


# -- Endpoints -----------------------------------------------------------------

@router.get("/jobs")
async def get_jobs(
    query: str = "",
    department: str = "all",
    type: str = "all",
    page: int = 1,
    limit: int = 12,
):
    """Return filtered, paginated job listings."""
    filtered = JOBS_DB

    if query:
        q = query.lower()
        filtered = [
            j for j in filtered
            if q in j["title"].lower() or q in j["department"].lower() or q in j["description"].lower()
        ]
    if department != "all":
        filtered = [j for j in filtered if j["department"] == department]
    if type != "all":
        filtered = [j for j in filtered if j["type"] == type]

    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit

    return {
        "jobs": filtered[start:end],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "departments": DEPARTMENTS,
    }


@router.get("/jobs/{job_id}")
async def get_job_detail(job_id: str):
    job = next((j for j in JOBS_DB if j["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/apply")
async def apply_to_job(job_id: str, req: ApplyRequest):
    job = next((j for j in JOBS_DB if j["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # TODO: persist to DB, trigger email notification
    return {"success": True, "message": f"Application submitted for {job['title']}", "application_id": f"APP-{job_id}-{req.employee_id}"}


# -- Interview Prep -------------------------------------------------------------

@router.post("/interview/stream")
async def stream_interview_response(req: InterviewRequest):
    """
    Groq powers mock interview conversation. 
    Simplified to return a single JSON string for frontend apiPost helper.
    """
    system_prompt = f"""You are 'Arjun', a senior HR interviewer at NamanDarshan - India's premium pilgrimage services company.
You are conducting a mock interview for the role of {req.job_role} in the {req.department} department.
Be professional yet warm. Ask ONE follow-up question at a time.
After every 3 exchanges, briefly acknowledge the candidate's growth.
Keep responses concise (2-3 sentences max per turn).
Speak naturally, as if in a real interview. Do not use bullet points."""

    messages: list[ChatCompletionMessageParam] = [
        cast(ChatCompletionMessageParam, {"role": "system", "content": system_prompt})
    ]
    for msg in req.history[-10:]:
        messages.append(cast(ChatCompletionMessageParam, {"role": msg.role, "content": msg.content}))
    messages.append(cast(ChatCompletionMessageParam, {"role": "user", "content": req.user_answer}))

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            stream=False,
            max_tokens=300,
            temperature=0.7,
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/assess")
async def assess_answer(req: AssessmentRequest):
    """
    Gemini 1.5 Pro does structured technical assessment of the candidate's answer.
    """
    prompt = f"""You are a technical assessment engine for NamanDarshan HR.
Role being interviewed for: {req.job_role}

Interview Question: {req.question}
Candidate's Answer: {req.answer}

Assess the answer and return a JSON object with exactly these fields:
{{
  "score": <integer 1-10>,
  "strengths": [<string>, <string>],
  "improvements": [<string>, <string>],
  "ideal_keywords": [<string>, <string>, <string>],
  "overall_feedback": "<2-sentence summary>",
  "star_rating": <float 1-5>
}}
Return only the JSON. No markdown, no explanation."""

    try:
        if not _GEMINI_KEY:
            raise ValueError("GEMINI_API_KEY is not set.")
        model = GenerativeModel(_GEMINI_MODEL)
        response = model.generate_content(prompt)
        raw_text = response.text or ""
        raw = raw_text.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@router.get("/interview/questions/{role}")
async def get_interview_questions(role: str):
    questions = INTERVIEW_QUESTIONS_BY_ROLE.get(role, INTERVIEW_QUESTIONS_BY_ROLE["default"])
    return {"questions": questions, "role": role}


# -- CV Builder ----------------------------------------------------------------

@router.post("/cv/optimize-ats")
async def optimize_cv_ats(req: ATSOptimizeRequest):
    """
    Gemini analyzes a job description and CV to suggest ATS-optimizing keywords.
    """
    cv_summary = f"""
Name: {req.cv_data.full_name}
Summary: {req.cv_data.summary}
Skills: {', '.join(req.cv_data.skills)}
Experience: {json.dumps(req.cv_data.experience[:3], indent=2)}
"""
    prompt = f"""You are an expert ATS Resume Optimizer.

Job Description:
{req.job_description}

Candidate's Current CV Summary:
{cv_summary}

Analyze the job description and the CV. Return a JSON object:
{{
  "ats_score_estimate": <integer 0-100>,
  "missing_keywords": [<up to 10 keywords/phrases from JD missing in CV>],
  "suggested_skills": [<3-5 skills to add>],
  "summary_rewrite": "<rewritten professional summary optimized for this JD>",
  "keyword_density_tips": "<1-2 sentence tip on where to naturally embed these keywords>",
  "overall_match": "<strong|moderate|weak>"
}}
Return only JSON. No markdown."""

    try:
        if not _GEMINI_KEY:
            raise ValueError("GEMINI_API_KEY is not set.")
        model = GenerativeModel(_GEMINI_MODEL)
        response = model.generate_content(prompt)
        raw_text = response.text or ""
        raw = raw_text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ATS optimization failed: {str(e)}")


@router.post("/cv/generate-pdf")
async def generate_cv_pdf(req: PDFRequest):
    """
    Generates a PDF CV using ReportLab.
    Returns PDF as a downloadable file.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        navy   = colors.HexColor("#0A1628")
        gold   = colors.HexColor("#F59E0B")
        gray   = colors.HexColor("#64748B")
        white  = colors.white

        styles = getSampleStyleSheet()
        name_style = ParagraphStyle("name", fontSize=24, textColor=navy,
                                     fontName="Helvetica-Bold", spaceAfter=4)
        contact_style = ParagraphStyle("contact", fontSize=9, textColor=gray,
                                        fontName="Helvetica", spaceAfter=2)
        section_style = ParagraphStyle("section", fontSize=11, textColor=navy,
                                        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4)
        body_style = ParagraphStyle("body", fontSize=9.5, textColor=colors.HexColor("#1E293B"),
                                     fontName="Helvetica", spaceAfter=3, leading=14)

        cv = req.cv_data
        story = []

        # Header
        story.append(Paragraph(cv.full_name, name_style))
        contact_info = f"{cv.email}  |  {cv.phone}  |  {cv.location}"
        story.append(Paragraph(contact_info, contact_style))
        story.append(HRFlowable(width="100%", thickness=2, color=gold, spaceAfter=8))

        # Summary
        if cv.summary:
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
            story.append(Paragraph(cv.summary, body_style))

        # Experience
        if cv.experience:
            story.append(Paragraph("WORK EXPERIENCE", section_style))
            for exp in cv.experience:
                title = f"<b>{exp.get('title', '')}</b> - {exp.get('company', '')}"
                story.append(Paragraph(title, body_style))
                period = f"{exp.get('start', '')} - {exp.get('end', 'Present')}  |  {exp.get('location', '')}"
                story.append(Paragraph(f"<font color='#64748B' size='9'>{period}</font>", body_style))
                for bullet in exp.get("bullets", []):
                    story.append(Paragraph(f"* {bullet}", body_style))
                story.append(Spacer(1, 6))

        # Education
        if cv.education:
            story.append(Paragraph("EDUCATION", section_style))
            for edu in cv.education:
                line = f"<b>{edu.get('degree', '')}</b>, {edu.get('institution', '')} ({edu.get('year', '')})"
                story.append(Paragraph(line, body_style))

        # Skills
        if cv.skills:
            story.append(Paragraph("SKILLS", section_style))
            skills_text = "  *  ".join(cv.skills)
            story.append(Paragraph(skills_text, body_style))

        # Certifications
        if cv.certifications:
            story.append(Paragraph("CERTIFICATIONS", section_style))
            for cert in cv.certifications:
                story.append(Paragraph(f"* {cert}", body_style))

        doc.build(story)
        buffer.seek(0)

        filename = f"CV_{cv.full_name.replace(' ', '_')}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
