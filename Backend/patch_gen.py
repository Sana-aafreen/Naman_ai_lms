import os

def patch_generator():
    path = "agents/Course_generator.py"
    with open(path, "r", encoding="ascii", errors="ignore") as f:
        content = f.read()
    
    # Target content to replace
    old_target = """        @router.post("/generate")
        async def generate_course(req: GenerateCourseRequest):
            try:
                return _agent.generate_html_course_package(
                    department=req.department,
                    related_queries=req.related_queries,
                    generate_pdf=req.generate_pdf,
                    save_to_disk=req.save_to_disk,
                )"""
                
    new_content = """        @router.post("/generate")
        async def generate_course(req: GenerateCourseRequest):
            try:
                # Force generation of physical files so they can be served via /api/generated-courses/file/
                return _agent.generate_html_course_package(
                    department=req.department,
                    related_queries=req.related_queries,
                    generate_pdf=True,
                    save_to_disk=True,
                )"""
    
    if old_target in content:
        content = content.replace(old_target, new_content)
        with open(path, "w", encoding="ascii") as f:
            f.write(content)
        print("Patched Course_generator.py")
    else:
        print("Target not found in Course_generator.py")

if __name__ == "__main__":
    patch_generator()
