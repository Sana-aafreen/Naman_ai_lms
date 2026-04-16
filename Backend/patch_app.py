import os
from pathlib import Path

backend_dir = Path("Backend")
cal_path = backend_dir / "agents" / "calendar_manager.py"
main_path = backend_dir / "main.py"

# --- 1. Fix calendar_manager.py ---
with open(cal_path, "r", encoding="utf-8") as f:
    cal_content = f.read()

# Replace `@app.` with `@router.`
cal_content = cal_content.replace("@app.", "@router.")

# Remove lifespan and app=FastAPI definition, replace with APIRouter
target_block = """# ════════════════════════════════════════════════════════════
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────
    init_db()
    # Keep startup banner ASCII-only to avoid Windows console encoding issues (cp1252).
    print("\\n  Calendar Manager | Gemini AI x Google Calendar")
    print("  " + ("-" * 52))
    print("  Syncing employees from Google Sheet...")
    sync_employees_from_gsheet()
    print("  Initializing Google Calendar API...")
    get_gcal_api()
    print("  http://localhost:8000\\n")
    yield
    # ── shutdown (nothing to clean up) ──────────────────

app = FastAPI(title="Calendar Manager (Gemini x Google Calendar)",
              version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])"""

new_block = """# ════════════════════════════════════════════════════════════
from fastapi import APIRouter
router = APIRouter()"""

# We'll use a more flexible replacement in case of whitespace differences
import re
# We just find `app = FastAPI(...)` and replace it
cal_content = re.sub(
    r'from contextlib import asynccontextmanager.*?allow_headers=\["\*"\]\)',
    new_block,
    cal_content,
    flags=re.DOTALL
)

with open(cal_path, "w", encoding="utf-8") as f:
    f.write(cal_content)

print("calendar_manager.py updated.")

# --- 2. Fix main.py ---
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()

# Replace the import
main_content = main_content.replace(
    "from agents.calendar_manager import app, _create_auth_token, _get_current_user",
    "from agents.calendar_manager import router as calendar_router, _create_auth_token, _get_current_user"
)

# Replace the app.add_middleware line that was importing app
main_content = main_content.replace(
    'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])',
    ""
)

# Now define app and lifespan in main.py, right where the FastAPI import is or just after the imports
# wait, main.py already imports uvicorn and FastAPI.
# Let's insert the lifespan + app definition where the old middleware line used to be or at the very top of module body

app_def = """from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────
    from agents.calendar_manager import init_db, sync_employees_from_gsheet, get_gcal_api
    init_db()
    print("\\n  NamanDarshan LMS | General Startup")
    print("  " + ("-" * 52))
    print("  Syncing employees from Google Sheet...")
    sync_employees_from_gsheet()
    print("  Initializing Google Calendar API...")
    get_gcal_api()
    print("  http://localhost:8000\\n")
    yield

app = FastAPI(title="NamanDarshan LMS", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(calendar_router)
"""

# Let's insert app_def somewhere at the top level
# I'll put it right after the imports. Let's find "from services.sheets import ("
insert_idx = main_content.find("from services.sheets import (")
if insert_idx != -1:
    end_of_imports = main_content.find(")\n", insert_idx) + 2
    
    first_part = main_content[:end_of_imports]
    second_part = main_content[end_of_imports:]
    
    main_content = first_part + "\n" + app_def + "\n" + second_part

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_content)

print("main.py updated.")

