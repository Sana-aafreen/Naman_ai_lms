# -*- coding: utf-8 -*-
"""
mongo_db.py  MongoDB Connection & Helpers for NamanDarshan LMS
================================================================

Provides centralized MongoDB connection and helper functions to replace SQLite.

Environment Variables:
  MONGODB_URL: Connection string (default: mongodb://localhost:27017)
  MONGODB_DB:  Database name (default: naman_lms)

Usage:
  from mongo_db import get_db, insert_one, find_one, update_one, etc.
  
  db = get_db()  # Returns pymongo.database.Database
  
  # Collections auto-created on first use
  users_col = db['users']
  courses_col = db['courses']
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

# -- Configuration -------------------------------------------------------------

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "naman_lms")
MONGODB_TIMEOUT = int(os.getenv("MONGODB_TIMEOUT", "10000"))  # ms

# -- Global connection ---------------------------------------------------------

_client: Optional[MongoClient] = None
_db: Optional[Database] = None
_connection_failed = False  # Flag to prevent repeated connection attempts


def connect() -> Database:
    """
    Establish MongoDB connection and return database instance.
    Creates indexes on first call.
    """
    global _client, _db, _connection_failed
    
    if _db is not None:
        return _db
    
    if _connection_failed:
        raise ConnectionFailure("MongoDB connection previously failed, not retrying")
    
    try:
        print(f"  [Mongo] Connecting to: {MONGODB_URL}")
        _client = MongoClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=MONGODB_TIMEOUT,
            connectTimeoutMS=MONGODB_TIMEOUT,
            socketTimeoutMS=MONGODB_TIMEOUT,
        )
        
        # Test connection
        _client.admin.command("ping")
        _db = _client[MONGODB_DB]
        
        print(f"  [Mongo] Connected to database: {MONGODB_DB}")
        _create_indexes()
        return _db
    
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        _connection_failed = True
        safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"  [Mongo] Connection failed: {safe_err}")
        print(f"  [Mongo] Warning: Make sure MongoDB is running at {MONGODB_URL}")
        raise


def get_db() -> Database:
    """Get the MongoDB database instance (connects if needed)."""
    global _db
    if _db is None:
        _db = connect()
    return _db


def close() -> None:
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("  [Mongo] Connection closed")


# -- Index Creation -------------------------------------------------------------

def _create_indexes() -> None:
    """Create all necessary indexes for efficient querying."""
    global _db
    
    if _db is None:
        _db = connect()
    
    db = _db
    
    try:
        # Employees (renamed from users for consistency with current code)
        db["employees"].create_index("gsheet_uid", unique=True, sparse=True)
        db["employees"].create_index("email", unique=True, sparse=True)
        db["employees"].create_index("department")
        
        # Meetings and Calendar
        db["meetings"].create_index("date")
        db["meetings"].create_index("organizer_id")
        db["meeting_attendees"].create_index([("meeting_id", ASCENDING), ("employee_id", ASCENDING)], unique=True)
        db["leaves"].create_index("employee_id")
        db["holidays"].create_index("date", unique=True)
        
        # KPI and Performance
        db["kpi_ratings"].create_index([("employee_id", ASCENDING), ("month", ASCENDING)], unique=True)
        
        # Existing indexing logic...
        db["users"].create_index("user_id", unique=True, sparse=True)
        db["users"].create_index("email", unique=True, sparse=True)
        db["users"].create_index("department")
        
        # Courses collection indexes
        db["courses"].create_index("department")
        db["courses"].create_index("created_at", name="idx_created_at")
        db["courses"].create_index([("title", "text"), ("summary", "text")])
        
        # Course modules indexes
        db["course_modules"].create_index("course_id")
        db["course_modules"].create_index([("course_id", ASCENDING), ("module_index", ASCENDING)])
        
        # Course progress indexes
        db["course_progress"].create_index([("learner_id", ASCENDING), ("course_id", ASCENDING)])
        db["course_progress"].create_index("course_id")
        db["course_progress"].create_index("learner_id")
        
        # Quiz results indexes
        db["quiz_results"].create_index([("user_id", ASCENDING), ("course_id", ASCENDING)])
        db["quiz_results"].create_index("user_id")
        db["quiz_results"].create_index("course_id")
        db["quiz_results"].create_index("created_at")
        
        # Published courses indexes
        db["published_courses"].create_index("department")
        db["published_courses"].create_index([("department", ASCENDING), ("created_at", DESCENDING)])
        
        # Calendars indexes
        db["calendars"].create_index([("user_id", ASCENDING), ("date", ASCENDING)])
        db["calendars"].create_index("user_id")
        
        # User profiles indexes
        db["user_profiles"].create_index("user_id", unique=True, sparse=True)
        
        print("  [Mongo] Indexes created for all collections")
    
    except Exception as e:
        safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"  [Mongo] Warning creating indexes: {safe_err}")


def now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_doc(doc: Any) -> Any:
    """Recursive helper to convert BSON types (ObjectId, datetime) to JSON-serializable types."""
    if isinstance(doc, list):
        return [clean_doc(d) for d in doc]
    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if k == "_id":
                # Ensure every document has a string 'id' field for frontend/legacy compatibility
                new_doc["id"] = str(v)
                new_doc[k] = str(v)
            else:
                new_doc[k] = clean_doc(v)
        
        # Double check 'id' exists if '_id' was missing but it's a dict
        if "id" not in new_doc and "_id" in new_doc:
             new_doc["id"] = str(new_doc["_id"])
             
        return new_doc
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc


def insert_one(collection_name: str, document: Dict[str, Any]) -> str:
    """
    Insert a document and return its ID.
    
    Args:
        collection_name: Name of the collection
        document: Document to insert (can include _id)
    
    Returns:
        The inserted document's _id as string
    """
    db = get_db()
    result = db[collection_name].insert_one(document)
    return str(result.inserted_id)


def insert_many(collection_name: str, documents: List[Dict[str, Any]]) -> List[str]:
    """Insert multiple documents."""
    db = get_db()
    result = db[collection_name].insert_many(documents)
    return [str(id_) for id_ in result.inserted_ids]


def find_one(
    collection_name: str,
    query: Dict[str, Any],
    projection: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    """Find one document matching the query."""
    db = get_db()
    res = db[collection_name].find_one(query, projection=projection)
    return clean_doc(res) if res else None


def find_many(
    collection_name: str,
    query: Dict[str, Any] = None,
    projection: Optional[Dict[str, int]] = None,
    limit: int = 0,
    skip: int = 0,
    sort: Optional[List[tuple]] = None,
) -> List[Dict[str, Any]]:
    """Find multiple documents matching the query."""
    db = get_db()
    query = query or {}
    cursor = db[collection_name].find(query, projection=projection)
    
    if sort:
        cursor = cursor.sort(sort)
    
    if skip > 0:
        cursor = cursor.skip(skip)
    
    if limit > 0:
        cursor = cursor.limit(limit)
    
    return [clean_doc(doc) for doc in list(cursor)]


def update_one(
    collection_name: str,
    query: Dict[str, Any],
    update: Dict[str, Any],
    upsert: bool = False,
) -> bool:
    """
    Update one document.
    
    Args:
        collection_name: Name of the collection
        query: Query filter
        update: Update operations (use {"$set": {...}} format)
        upsert: If True, insert if not found
    
    Returns:
        True if document was modified or inserted, False otherwise
    """
    db = get_db()
    result = db[collection_name].update_one(query, update, upsert=upsert)
    return result.modified_count > 0 or (upsert and result.upserted_id is not None)


def update_many(
    collection_name: str,
    query: Dict[str, Any],
    update: Dict[str, Any],
) -> int:
    """Update multiple documents. Returns count of modified documents."""
    db = get_db()
    result = db[collection_name].update_many(query, update)
    return result.modified_count


def delete_one(collection_name: str, query: Dict[str, Any]) -> bool:
    """Delete one document. Returns True if deleted."""
    db = get_db()
    result = db[collection_name].delete_one(query)
    return result.deleted_count > 0


def delete_many(collection_name: str, query: Dict[str, Any]) -> int:
    """Delete multiple documents. Returns count of deleted documents."""
    db = get_db()
    result = db[collection_name].delete_many(query)
    return result.deleted_count


def count_documents(collection_name: str, query: Dict[str, Any] = None) -> int:
    """Count documents matching the query."""
    db = get_db()
    query = query or {}
    return db[collection_name].count_documents(query)


def aggregate(
    collection_name: str,
    pipeline: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Run an aggregation pipeline.
    """
    db = get_db()
    results = list(db[collection_name].aggregate(pipeline))
    return [clean_doc(res) for res in results]


# -- Collection Helpers ----------------------------------------------------------

class MongoCollection:
    """Helper class for common operations on a specific collection."""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.db = get_db()
        self.col = self.db[collection_name]
    
    def insert(self, document: Dict[str, Any]) -> str:
        """Insert and return ID."""
        return insert_one(self.collection_name, document)
    
    def find_all(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Find all documents."""
        return find_many(self.collection_name, limit=limit)
    
    def find(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find documents matching query."""
        return find_many(self.collection_name, query)
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find one document."""
        return find_one(self.collection_name, query)
    
    def find_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find document by _id."""
        from bson.objectid import ObjectId
        try:
            return find_one(self.collection_name, {"_id": ObjectId(doc_id)})
        except:
            return None
    
    def update(self, query: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update document(s) with $set."""
        return update_one(self.collection_name, query, {"$set": data})
    
    def upsert(self, query: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update or insert document."""
        return update_one(self.collection_name, query, {"$set": data}, upsert=True)
    
    def delete(self, query: Dict[str, Any]) -> bool:
        """Delete document."""
        return delete_one(self.collection_name, query)
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents."""
        return count_documents(self.collection_name, query)


# -- Initialization --------------------------------------------------------------

def init_mongodb() -> Database:
    """Initialize MongoDB connection (call on app startup)."""
    return connect()
