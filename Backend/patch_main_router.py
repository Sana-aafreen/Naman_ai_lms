import os

main_path = r"c:\Users\sumbu\Downloads\namandarshan-learn-ai-fullstack\namandarshan-learn-ai-fullstack\Backend\main.py"

with open(main_path, "r", encoding="utf-8") as f:
    text = f.read()

if "profile_router" not in text:
    # Just a safety check
    pass

if "app.include_router(profile_router)" not in text:
    new_text = text.replace(
        'if __name__ == "__main__":',
        '# Register Profile router\napp.include_router(profile_router)\n\nif __name__ == "__main__":'
    )
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("profile_router included.")
else:
    print("Already included.")
