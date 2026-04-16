import mongo_db
import sys

def debug_user():
    mongo_db.init_mongodb()
    user = mongo_db.find_one("employees", {"gsheet_uid": "EMP006"})
    if not user:
        print("User EMP006 not found!")
        return
    
    pwd = user.get("gsheet_password", "")
    print(f"UID: {user.get('gsheet_uid')}")
    print(f"Pwd length: {len(pwd)}")
    print(f"Pwd starts with space: {pwd.startswith(' ')}")
    print(f"Pwd ends with space: {pwd.endswith(' ')}")
    print(f"Role: {user.get('role')}")
    print(f"Department: {user.get('department')}")

if __name__ == "__main__":
    debug_user()
