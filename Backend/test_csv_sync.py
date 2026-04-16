import sys
from pathlib import Path
# Add Backend to path
sys.path.append(str(Path(__file__).resolve().parent))

from agents.calendar_manager import sync_employees_from_csv
import mongo_db

def test_sync():
    mongo_db.init_mongodb()
    initial_count = mongo_db.count_documents("employees")
    print(f"Initial count: {initial_count}")
    
    sync_employees_from_csv()
    
    final_count = mongo_db.count_documents("employees")
    print(f"Final count: {final_count}")
    
    # Check for a specific user from the CSV (Amit Sharma - EMP001)
    amit = mongo_db.find_one("employees", {"gsheet_uid": "EMP001"})
    print(f"Found Amit: {amit is not None}")
    if amit:
        print(f"Amit Role: {amit.get('role')}")

if __name__ == "__main__":
    test_sync()
