import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.ai_service import get_groq_response
from mongo_db import get_db, find_one

logger = logging.getLogger(__name__)

class AITutorAgent:
    def __init__(self):
        self.db = get_db()

    def get_system_prompt(self, department: str, context: Optional[str] = None) -> str:
        context_msg = f'ADDITIONAL CONTEXT:\n{context}' if context else ''
        return f"""You are Naman AI Tutor — a warm, knowledgeable learning mentor. You help students learn effectively.

DEPARTMENT: {department or 'general'}

CORE BEHAVIORS:
- When asked to "generate a module" on a topic, respond with a structured JSON block in ```json``` format containing: title, topic, overview, key_concepts (array of {{title, description}}), examples (array), practice_questions (array), mini_project (string), summary
- When recommending resources, provide REAL working URLs (YouTube, freeCodeCamp, MDN, Khan Academy, Coursera, etc.)
- Always be department-aware: tailor examples and language to the student's department
- Be structured, clear, and encouraging — not robotic
- Track context from conversation to provide personalized guidance
- When discussing strengths/weaknesses, be constructive and specific

{context_msg}

RESOURCE LINKS RULES:
- Always use full https:// URLs
- Only recommend well-known, free, accessible resources
- Format recommendations as markdown links that open in new tabs"""

    async def chat(self, messages: List[Dict[str, str]], department: str, user_id: str) -> str:
        # Fetch some context from DB if needed
        profile = find_one("user_profiles", {"user_id": user_id})
        progress = list(self.db["tutor_progress"].find({"user_id": user_id}))
        
        context = f"User Profile: {json.dumps(profile if profile else {})}\nUser Progress: {json.dumps(progress if progress else [])}"
        system_prompt = self.get_system_prompt(department, context)
        
        # We simplify the history for the AI service call
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
        prompt = f"{history_text}\nAssistant:"
        
        return get_groq_response(prompt, system=system_prompt)

    def save_module(self, user_id: str, module_data: Dict[str, Any]) -> str:
        module_data["user_id"] = user_id
        module_data["created_at"] = datetime.now()
        result = self.db["tutor_modules"].insert_one(module_data)
        return str(result.inserted_id)

    def get_user_modules(self, user_id: str) -> List[Dict[str, Any]]:
        modules = list(self.db["tutor_modules"].find({"user_id": user_id}))
        for m in modules:
            m["id"] = str(m["_id"])
            del m["_id"]
        return modules

    def upsert_progress(self, user_id: str, progress_data: Dict[str, Any]):
        module_id = progress_data.get("module_id")
        self.db["tutor_progress"].update_one(
            {"user_id": user_id, "module_id": module_id},
            {"$set": {**progress_data, "updated_at": datetime.now()}, "$setOnInsert": {"created_at": datetime.now()}},
            upsert=True
        )

    def get_user_progress(self, user_id: str) -> List[Dict[str, Any]]:
        progress = list(self.db["tutor_progress"].find({"user_id": user_id}))
        for p in progress:
            p["id"] = str(p["_id"])
            del p["_id"]
        return progress

    def save_assessment(self, user_id: str, assessment_data: Dict[str, Any]):
        assessment_data["user_id"] = user_id
        assessment_data["created_at"] = datetime.now()
        self.db["tutor_assessments"].insert_one(assessment_data)

tutor_agent = AITutorAgent()
