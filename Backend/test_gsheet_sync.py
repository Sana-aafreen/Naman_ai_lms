import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add Backend to path
sys.path.append(str(Path(__file__).resolve().parent))
load_dotenv()

from agents.calendar_manager import sync_employees_from_gsheet
import mongo_db

def test_gsheet_sync():
    print("Testing Google Sheets Sync...")
    mongo_db.init_mongodb()
    
    initial_count = mongo_db.count_documents("employees")
    print(f"Initial count in DB: {initial_count}")
    
    sync_employees_from_gsheet()
    
    final_count = mongo_db.count_documents("employees")
    print(f"Final count in DB after GSheet sync: {final_count}")
    
    if final_count > 0:
        print("SUCCESS: Google Sheets sync populated the database.")
    else:
        print("FAILURE: Google Sheets sync did not populate the database.")

if __name__ == "__main__":
    test_gsheet_sync()
