import os

main_path = r"c:\Users\sumbu\Downloads\namandarshan-learn-ai-fullstack\namandarshan-learn-ai-fullstack\Backend\main.py"

with open(main_path, "r", encoding="utf-8") as f:
    text = f.read()

if "profile_router" not in text.split("app.include_router(profile_router)")[0]:
    # This means the import is missing!
    text = text.replace(
        "from agents.Career import router as career_router",
        "from agents.Career import router as career_router\nfrom agents.Profile_routes import router as profile_router"
    )
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("profile_router import added!")
else:
    print("profile_router import already exists.")

# Check for syntax errors by compiling
try:
    compile(text, main_path, "exec")
    print("Syntax OK!")
except Exception as e:
    print(f"Syntax error! {e}")
