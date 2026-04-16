import mongo_db
import json

def list_all_employees():
    mongo_db.init_mongodb()
    emps = mongo_db.find_many("employees")
    for e in emps:
        # Hide password but show other fields
        clean = dict(e)
        clean["gsheet_password"] = "***"
        print(json.dumps(clean))

if __name__ == "__main__":
    list_all_employees()
