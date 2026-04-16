# Test mongo_db serialization fix
from mongo_db import clean_doc
from bson.objectid import ObjectId

def test_serialization():
    # Mock some data with ObjectId
    doc = {
        "_id": ObjectId("661e7c9f8b3a4f2e9a5d7c1a"),
        "user_id": "EMP001",
        "nested": {
            "ref_id": ObjectId("661e7c9f8b3a4f2e9a5d7c1b")
        },
        "list": [ObjectId("661e7c9f8b3a4f2e9a5d7c1c"), "regular string"]
    }
    
    cleaned = clean_doc(doc)
    print(f"Original: {type(doc['_id'])}")
    print(f"Cleaned:  {type(cleaned['_id'])}")
    print(f"Nested:   {type(cleaned['nested']['ref_id'])}")
    print(f"List:     {type(cleaned['list'][0])}")
    
    assert isinstance(cleaned["_id"], str)
    assert isinstance(cleaned["nested"]["ref_id"], str)
    assert isinstance(cleaned["list"][0], str)
    print("\n✅ Serialization test passed!")

if __name__ == "__main__":
    test_serialization()
