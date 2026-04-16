import mongo_db
from bson.objectid import ObjectId
import json

def inspect_course(id_str):
    db = mongo_db.get_db()
    doc = db.published_courses.find_one({"_id": ObjectId(id_str)})
    if not doc:
        print("NOT FOUND")
        return
    
    print(f"Title: {doc.get('title')}")
    print(f"Department: {doc.get('department')}")
    print(f"Modules Count: {len(doc.get('modules', []))}")
    
    modules = doc.get("modules", [])
    for i, m in enumerate(modules):
        print(f"  Module {i+1}: {m.get('title')} ({len(m.get('lessons', []))} lessons)")
        for j, lesson in enumerate(m.get('lessons', [])):
            content = lesson.get('content', '')
            print(f"    - Lesson {j+1}: {lesson.get('title')} ({len(content)} chars)")

    quiz = doc.get("quiz_questions", [])
    print(f"Quiz Questions: {len(quiz)}")

if __name__ == "__main__":
    inspect_course("69df83415075d8e5c8ece1bc")
