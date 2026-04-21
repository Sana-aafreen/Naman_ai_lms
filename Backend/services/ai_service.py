import os
import builtins
from typing import Optional
from dotenv import load_dotenv

# Load env in case it's not loaded
load_dotenv()

def safe_print(*args, **kwargs):
    """Fallback safe print for unicode issues."""
    try:
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [
            str(arg).encode('ascii', 'ignore').decode('ascii') 
            for arg in args
        ]
        builtins.print(*safe_args, **kwargs)

class GeminiService:
    def __init__(self):
        self.client = None
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        
        # Priority fallback models including versioned variants
        self.fallback_models = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-002",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest"
        ]
        
        if not self.api_key:
            safe_print("⚠️  [AI Service] GEMINI_API_KEY not found in environment.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            
            # Verify connectivity and select best available model
            # We filter out models that are known to fail temporarily
            test_models = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
            
            found_working = False
            for m in test_models:
                try:
                    # Low-token test to verify model availability
                    self.client.models.generate_content(model=m, contents="ping")
                    self.model_name = m
                    safe_print(f"✅ [AI Service] Gemini initialized with model: {self.model_name}")
                    found_working = True
                    break
                except Exception as e:
                    err_msg = str(e).lower()
                    if "429" in err_msg or "quota" in err_msg:
                        safe_print(f"⌛ [AI Service] Model {m} is rate-limited (429/Quota).")
                    elif "404" in err_msg:
                        # Try with prefix if short name failed (though genai client usually handles this)
                        if not m.startswith("models/"):
                            try:
                                full_m = f"models/{m}"
                                self.client.models.generate_content(model=full_m, contents="ping")
                                self.model_name = full_m
                                safe_print(f"✅ [AI Service] Gemini initialized with full path: {self.model_name}")
                                found_working = True
                                break
                            except Exception: pass
                        safe_print(f"❓ [AI Service] Model {m} not found (404).")
                    else:
                        safe_print(f"⚠️  [AI Service] Model {m} error: {e}")
                    continue
            
            if not found_working:
                safe_print("❌ [AI Service] All Gemini models currently unreachable. Using heuristic fallbacks.")
                self.client = None
                
        except ImportError:
            safe_print("⚠️  [AI Service] google-genai library not installed. Install with: pip install google-genai")
            self.client = None
        except Exception as e:
            safe_print(f"❌ [AI Service] Initialization error: {e}")
            self.client = None

    def generate_content(self, prompt: str, system: str = "") -> str:
        if not self.client:
            return self.get_fallback_response(prompt)
            
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            return response.text.strip()
        except Exception as e:
            safe_print(f"❌ [AI Service] Generation error: {e}")
            return self.get_fallback_response(prompt)

    def get_fallback_response(self, prompt: str) -> str:
        """Heuristic-based fallback when AI is unavailable."""
        p = prompt.lower()
        if "progress" in p or "analysis" in p or "streak" in p:
            return "📊 Your learning journey is looking strong! You've been building consistent habits. To accelerate your growth, try revisiting topics you found challenging and setting clear weekly milestones. Every small step counts towards your ultimate goal!"
        elif "recommend" in p or "course" in p or "next" in p:
            return "📚 I suggest exploring courses that align with your current department goals. Based on common paths, advanced modules in your field would be a great next step. What specific skill are you looking to master today?"
        elif "quiz" in p or "score" in p or "test" in p:
            return "🎯 Consistent practice is the key to high quiz scores! Focus on understanding the core concepts before attempting the quiz. If you hit a blocker, review the specific module and try again. You've got this!"
        elif "goal" in p or "plan" in p or "future" in p:
            return "🎯 A clear roadmap makes any goal achievable. Let's break down your career objectives into actionable steps. Tell me one major skill you want to achieve this quarter, and we can build a plan together."
        else:
            return "I'm your NamanDarshan LMS coach! I can help with progress tracking, course recommendations, and career planning. Ask me anything about your professional development journey!"

class GroqService:
    def __init__(self):
        self.client = None
        self.api_key = os.getenv("GROQ_API_KEY_TUTOR", os.getenv("GROQ_API_KEY", ""))
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        if not self.api_key:
            safe_print("⚠️  [Groq Service] GROQ_API_KEY_TUTOR not found.")
            return

        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            safe_print(f"✅ [Groq Service] Initialized with model: {self.model}")
        except ImportError:
            safe_print("⚠️  [Groq Service] groq library not installed.")
        except Exception as e:
            safe_print(f"❌ [Groq Service] Initialization error: {e}")

    def generate_content(self, prompt: str, system: str = "") -> str:
        if not self.client:
            return "I'm having trouble connecting to my brain right now. Please check my API configuration."
            
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=1,
                stream=False
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            safe_print(f"❌ [Groq Service] Generation error: {e}")
            return f"Error: {str(e)}"

# Singleton instances
ai_service = GeminiService()
groq_service = GroqService()

def get_gemini_response(prompt: str, system: str = "") -> str:
    return ai_service.generate_content(prompt, system)

def get_groq_response(prompt: str, system: str = "") -> str:
    return groq_service.generate_content(prompt, system)
