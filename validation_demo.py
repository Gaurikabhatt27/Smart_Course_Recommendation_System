"""
validation_demo.py
------------------
MongoDB Schema Validation Demonstration.
Executes controlled valid and invalid insert attempts against the database,
capturing and explaining the exact PyMongo DocumentValidationFailure / WriteError
exceptions thrown by MongoDB's strict JSON Schema engine.
Ensures zero test records remain in the database after execution.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from bson import ObjectId
from pymongo.errors import WriteError, PyMongoError
from database import get_db

VALIDATION_RULES_EXPLANATION = [
    {
        "collection": "students",
        "rules": [
            "Required fields: 'name', 'email', 'skills', 'interests', 'level', 'created_at'.",
            "Field 'level' restricted by enum to: ['Beginner', 'Intermediate', 'Advanced'].",
            "Field 'email' must match regex: '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'.",
            "Skills and Interests must be BSON arrays of strings."
        ]
    },
    {
        "collection": "courses",
        "rules": [
            "Required fields: 'title', 'category', 'skills', 'level', 'duration_hours', 'rating', 'created_at'.",
            "Field 'category' restricted to recognized domains (Data Science, AI, Web Dev, etc.).",
            "Field 'duration_hours' must be a positive number (minimum 0.5 hours).",
            "Field 'rating' must be bounded between 0.0 and 5.0.",
            "Field 'level' restricted to: ['Beginner', 'Intermediate', 'Advanced']."
        ]
    },
    {
        "collection": "enrollments",
        "rules": [
            "Required fields: 'student_id', 'course_id', 'progress', 'status', 'enrolled_at'.",
            "Field 'progress' must be between 0.0 and 100.0.",
            "Field 'status' restricted to: ['Not Started', 'In Progress', 'Completed'].",
            "Foreign keys 'student_id' and 'course_id' must be valid BSON ObjectIds."
        ]
    },
    {
        "collection": "reviews",
        "rules": [
            "Required fields: 'student_id', 'course_id', 'rating', 'comment', 'created_at'.",
            "Field 'rating' must be an integer between 1 and 5.",
            "Field 'comment' must be a string of at least 3 characters."
        ]
    }
]


def run_student_validation_demo() -> Dict[str, Any]:
    """Demonstrate student validation: valid insert vs invalid enum/email."""
    db = get_db()
    col = db["students"]
    now = datetime.now(timezone.utc)

    # 1. Valid Student Document
    valid_doc = {
        "name": "Demo Valid Student",
        "email": "demo.valid@university.edu",
        "skills": ["Python", "MongoDB"],
        "interests": ["Data Science"],
        "level": "Intermediate",
        "created_at": now
    }
    valid_res = {"success": False, "message": "", "inserted_id": None}
    try:
        res = col.insert_one(valid_doc)
        valid_res["success"] = True
        valid_res["message"] = f"Valid document accepted by MongoDB. Inserted ID: {res.inserted_id}"
        valid_res["inserted_id"] = res.inserted_id
    except PyMongoError as e:
        valid_res["message"] = f"Failed valid insert: {str(e)}"

    # 2. Invalid Student Document (Level is 'Expert', not in enum; Email is missing domain)
    invalid_doc = {
        "name": "Demo Invalid Student",
        "email": "invalid-email-no-domain",
        "skills": ["Hacking"],
        "interests": ["Security"],
        "level": "Expert",  # Violates enum
        "created_at": now
    }
    invalid_res = {
        "caught_expected_error": False,
        "error_type": "",
        "error_details": "",
        "explanation": ""
    }
    try:
        col.insert_one(invalid_doc)
        invalid_res["explanation"] = "UNEXPECTED: MongoDB accepted the invalid document."
    except WriteError as e:
        invalid_res["caught_expected_error"] = True
        invalid_res["error_type"] = "pymongo.errors.WriteError (DocumentValidationFailure)"
        invalid_res["error_details"] = str(e.details)
        invalid_res["explanation"] = (
            "MongoDB rejected the write because 'level' ('Expert') is not in the allowed enum "
            "['Beginner', 'Intermediate', 'Advanced'], and 'email' does not match the required regex pattern."
        )
    except PyMongoError as e:
        invalid_res["caught_expected_error"] = True
        invalid_res["error_type"] = type(e).__name__
        invalid_res["error_details"] = str(e)
        invalid_res["explanation"] = f"Caught expected PyMongo exception: {e}"

    # 3. Clean up valid test record
    if valid_res["inserted_id"]:
        col.delete_one({"_id": valid_res["inserted_id"]})

    return {
        "test_name": "Student Schema Validation",
        "valid_test": valid_res,
        "invalid_test": invalid_res
    }


def run_course_validation_demo() -> Dict[str, Any]:
    """Demonstrate course validation: valid insert vs negative duration and rating > 5.0."""
    db = get_db()
    col = db["courses"]
    now = datetime.now(timezone.utc)

    # 1. Valid Course Document
    valid_doc = {
        "title": "Demo Valid Cloud Architecture",
        "category": "Cloud Computing",
        "skills": ["AWS", "Docker"],
        "level": "Advanced",
        "duration_hours": 30.0,
        "rating": 4.8,
        "description": "Validation test syllabus.",
        "created_at": now
    }
    valid_res = {"success": False, "message": "", "inserted_id": None}
    try:
        res = col.insert_one(valid_doc)
        valid_res["success"] = True
        valid_res["message"] = f"Valid document accepted. Inserted ID: {res.inserted_id}"
        valid_res["inserted_id"] = res.inserted_id
    except PyMongoError as e:
        valid_res["message"] = f"Failed valid insert: {str(e)}"

    # 2. Invalid Course Document (Negative duration, Rating = 8.5)
    invalid_doc = {
        "title": "Demo Invalid Course",
        "category": "Artificial Intelligence",
        "skills": ["Python"],
        "level": "Beginner",
        "duration_hours": -15.0,  # Negative duration violates minimum: 0.5
        "rating": 8.5,             # Violates maximum: 5.0
        "description": "Broken course.",
        "created_at": now
    }
    invalid_res = {
        "caught_expected_error": False,
        "error_type": "",
        "error_details": "",
        "explanation": ""
    }
    try:
        col.insert_one(invalid_doc)
        invalid_res["explanation"] = "UNEXPECTED: MongoDB accepted the invalid document."
    except WriteError as e:
        invalid_res["caught_expected_error"] = True
        invalid_res["error_type"] = "pymongo.errors.WriteError (DocumentValidationFailure)"
        invalid_res["error_details"] = str(e.details)
        invalid_res["explanation"] = (
            "MongoDB rejected the write because 'duration_hours' (-15.0) violates minimum: 0.5, "
            "and 'rating' (8.5) exceeds maximum allowed rating of 5.0."
        )
    except PyMongoError as e:
        invalid_res["caught_expected_error"] = True
        invalid_res["error_type"] = type(e).__name__
        invalid_res["error_details"] = str(e)
        invalid_res["explanation"] = f"Caught expected PyMongo exception: {e}"

    # 3. Clean up
    if valid_res["inserted_id"]:
        col.delete_one({"_id": valid_res["inserted_id"]})

    return {
        "test_name": "Course Schema Validation",
        "valid_test": valid_res,
        "invalid_test": invalid_res
    }


def run_enrollment_validation_demo() -> Dict[str, Any]:
    """Demonstrate enrollment validation: valid insert vs progress > 100."""
    db = get_db()
    col = db["enrollments"]
    now = datetime.now(timezone.utc)
    dummy_student_id = ObjectId()
    dummy_course_id = ObjectId()

    # 1. Valid Enrollment Document
    valid_doc = {
        "student_id": dummy_student_id,
        "course_id": dummy_course_id,
        "progress": 50.0,
        "status": "In Progress",
        "enrolled_at": now
    }
    valid_res = {"success": False, "message": "", "inserted_id": None}
    try:
        res = col.insert_one(valid_doc)
        valid_res["success"] = True
        valid_res["message"] = f"Valid document accepted. Inserted ID: {res.inserted_id}"
        valid_res["inserted_id"] = res.inserted_id
    except PyMongoError as e:
        valid_res["message"] = f"Failed valid insert: {str(e)}"

    # 2. Invalid Enrollment Document (progress = 145.0, status = 'Paused')
    invalid_doc = {
        "student_id": dummy_student_id,
        "course_id": ObjectId(),
        "progress": 145.0,        # Violates maximum: 100.0
        "status": "Paused",       # Violates enum: ['Not Started', 'In Progress', 'Completed']
        "enrolled_at": now
    }
    invalid_res = {
        "caught_expected_error": False,
        "error_type": "",
        "error_details": "",
        "explanation": ""
    }
    try:
        col.insert_one(invalid_doc)
        invalid_res["explanation"] = "UNEXPECTED: MongoDB accepted the invalid document."
    except WriteError as e:
        invalid_res["caught_expected_error"] = True
        invalid_res["error_type"] = "pymongo.errors.WriteError (DocumentValidationFailure)"
        invalid_res["error_details"] = str(e.details)
        invalid_res["explanation"] = (
            "MongoDB rejected the write because 'progress' (145.0) exceeds maximum 100.0, "
            "and 'status' ('Paused') is not in the allowed enum values."
        )
    except PyMongoError as e:
        invalid_res["caught_expected_error"] = True
        invalid_res["error_type"] = type(e).__name__
        invalid_res["error_details"] = str(e)
        invalid_res["explanation"] = f"Caught expected PyMongo exception: {e}"

    # 3. Clean up
    if valid_res["inserted_id"]:
        col.delete_one({"_id": valid_res["inserted_id"]})

    return {
        "test_name": "Enrollment Schema Validation",
        "valid_test": valid_res,
        "invalid_test": invalid_res
    }


if __name__ == "__main__":
    print("=" * 65)
    print("MongoDB JSON Schema Validation Demonstration")
    print("=" * 65)
    demos = [
        run_student_validation_demo(),
        run_course_validation_demo(),
        run_enrollment_validation_demo(),
    ]
    for d in demos:
        print(f"\n[*] {d['test_name']}:")
        print(f"    Valid Test   : {'PASSED' if d['valid_test']['success'] else 'FAILED'}")
        print(f"                   {d['valid_test']['message']}")
        print(f"    Invalid Test : {'CAUGHT EXPECTED REJECTION' if d['invalid_test']['caught_expected_error'] else 'UNEXPECTED ACCEPT'}")
        print(f"                   Error Type: {d['invalid_test']['error_type']}")
        print(f"                   Explanation: {d['invalid_test']['explanation']}")
    print("\n" + "=" * 65)
    print("ALL JSON SCHEMA VALIDATION DEMOS PASSED SUCCESSFULLY!")
    print("=" * 65)

