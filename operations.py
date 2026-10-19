"""
operations.py
-------------
Comprehensive, robust CRUD operations module for MongoDB using PyMongo.
Provides application-level referential checks, validation, and safe error handling
for Students, Courses, Enrollments, and Reviews.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, WriteError, PyMongoError
from database import get_collection, get_db

VALID_LEVELS = ["Beginner", "Intermediate", "Advanced"]
VALID_CATEGORIES = [
    "Data Science",
    "Artificial Intelligence",
    "Web Development",
    "Database Systems",
    "Cloud Computing",
    "Cybersecurity"
]
VALID_STATUSES = ["Not Started", "In Progress", "Completed"]


def to_object_id(id_val: Union[str, ObjectId]) -> Optional[ObjectId]:
    """Safely convert string or ObjectId into ObjectId."""
    if isinstance(id_val, ObjectId):
        return id_val
    try:
        return ObjectId(str(id_val).strip())
    except (InvalidId, TypeError):
        return None


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert BSON ObjectIds and datetimes to serializable/display-friendly values."""
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d and isinstance(d["_id"], ObjectId):
        d["_id_str"] = str(d["_id"])
    for k, v in d.items():
        if isinstance(v, ObjectId):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.strftime("%Y-%m-%d %H:%M UTC")
    return d


# ==============================================================================
# STUDENTS CRUD OPERATIONS
# ==============================================================================

def create_student(
    name: str,
    email: str,
    skills: List[str],
    interests: List[str],
    level: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Insert a new student document with schema validation and unique email check.
    """
    students: Collection = get_collection("students")
    name = (name or "").strip()
    email = (email or "").strip().lower()
    level = (level or "").strip()

    if not name or len(name) < 2:
        return False, "Validation Error: Student name must be at least 2 characters.", None
    if not email or "@" not in email:
        return False, "Validation Error: A valid email address is required.", None
    if level not in VALID_LEVELS:
        return False, f"Validation Error: Level must be one of {VALID_LEVELS}.", None

    clean_skills = [s.strip() for s in skills if s and s.strip()]
    clean_interests = [i.strip() for i in interests if i and i.strip()]

    doc = {
        "name": name,
        "email": email,
        "skills": clean_skills,
        "interests": clean_interests,
        "level": level,
        "created_at": datetime.now(timezone.utc)
    }

    try:
        result = students.insert_one(doc)
        return True, "Student registered successfully.", str(result.inserted_id)
    except DuplicateKeyError:
        return False, f"Constraint Error: A student with email '{email}' already exists.", None
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}", None
    except PyMongoError as e:
        return False, f"Database error: {str(e)}", None


def get_all_students(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve all students sorted by name."""
    students: Collection = get_collection("students")
    cursor = students.find({}).sort("name", 1).limit(limit)
    return [serialize_doc(s) for s in cursor if s]


def get_student_by_id(student_id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
    """Fetch single student document by ObjectId."""
    oid = to_object_id(student_id)
    if not oid:
        return None
    students: Collection = get_collection("students")
    doc = students.find_one({"_id": oid})
    return serialize_doc(doc)


def search_students(query: str) -> List[Dict[str, Any]]:
    """Search students by regex on name or email (case-insensitive)."""
    students: Collection = get_collection("students")
    q = (query or "").strip()
    if not q:
        return get_all_students()
    filter_query = {
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}}
        ]
    }
    cursor = students.find(filter_query).sort("name", 1)
    return [serialize_doc(s) for s in cursor if s]


def update_student(
    student_id: Union[str, ObjectId],
    name: Optional[str] = None,
    skills: Optional[List[str]] = None,
    interests: Optional[List[str]] = None,
    level: Optional[str] = None
) -> Tuple[bool, str]:
    """Update student fields."""
    oid = to_object_id(student_id)
    if not oid:
        return False, "Invalid Student ID."

    updates: Dict[str, Any] = {}
    if name is not None:
        name_clean = name.strip()
        if len(name_clean) < 2:
            return False, "Name must be at least 2 characters."
        updates["name"] = name_clean
    if skills is not None:
        updates["skills"] = [s.strip() for s in skills if s and s.strip()]
    if interests is not None:
        updates["interests"] = [i.strip() for i in interests if i and i.strip()]
    if level is not None:
        if level not in VALID_LEVELS:
            return False, f"Level must be one of {VALID_LEVELS}."
        updates["level"] = level

    if not updates:
        return False, "No fields provided to update."

    students: Collection = get_collection("students")
    try:
        res = students.update_one({"_id": oid}, {"$set": updates})
        if res.matched_count == 0:
            return False, "Student not found."
        return True, "Student updated successfully."
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}"
    except PyMongoError as e:
        return False, f"Database error: {str(e)}"


def delete_student(student_id: Union[str, ObjectId], cascade: bool = True) -> Tuple[bool, str]:
    """
    Delete a student safely.
    If cascade is True, also deletes associated enrollments and reviews.
    """
    oid = to_object_id(student_id)
    if not oid:
        return False, "Invalid Student ID."

    db = get_db()
    students = db["students"]
    enrollments = db["enrollments"]
    reviews = db["reviews"]

    try:
        # Check if student exists
        student = students.find_one({"_id": oid})
        if not student:
            return False, "Student not found."

        if not cascade:
            enr_count = enrollments.count_documents({"student_id": oid})
            if enr_count > 0:
                return False, f"Cannot delete: Student has {enr_count} active enrollments. Use cascade delete."

        # Perform cascade cleanup
        enrollments.delete_many({"student_id": oid})
        reviews.delete_many({"student_id": oid})
        students.delete_one({"_id": oid})
        return True, f"Student '{student.get('name')}' and associated records removed successfully."
    except PyMongoError as e:
        return False, f"Database error during deletion: {str(e)}"


# ==============================================================================
# COURSES CRUD OPERATIONS
# ==============================================================================

def create_course(
    title: str,
    category: str,
    skills: List[str],
    level: str,
    duration_hours: float,
    rating: float,
    description: str
) -> Tuple[bool, str, Optional[str]]:
    """Insert a new course document into the catalog."""
    courses: Collection = get_collection("courses")
    title = (title or "").strip()
    category = (category or "").strip()
    level = (level or "").strip()
    description = (description or "").strip()

    if not title or len(title) < 3:
        return False, "Validation Error: Title must be at least 3 characters.", None
    if category not in VALID_CATEGORIES:
        return False, f"Validation Error: Category must be one of {VALID_CATEGORIES}.", None
    if level not in VALID_LEVELS:
        return False, f"Validation Error: Level must be one of {VALID_LEVELS}.", None
    if duration_hours < 0.5:
        return False, "Validation Error: Duration must be at least 0.5 hours.", None
    if rating < 0.0 or rating > 5.0:
        return False, "Validation Error: Rating must be between 0.0 and 5.0.", None

    clean_skills = [s.strip() for s in skills if s and s.strip()]

    doc = {
        "title": title,
        "category": category,
        "skills": clean_skills,
        "level": level,
        "duration_hours": float(duration_hours),
        "rating": float(rating),
        "description": description,
        "created_at": datetime.now(timezone.utc)
    }

    try:
        result = courses.insert_one(doc)
        return True, "Course added to catalog successfully.", str(result.inserted_id)
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}", None
    except PyMongoError as e:
        return False, f"Database error: {str(e)}", None


def get_all_courses(category: Optional[str] = None, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve courses with optional category and level filters."""
    courses: Collection = get_collection("courses")
    query: Dict[str, Any] = {}
    if category and category != "All":
        query["category"] = category
    if level and level != "All":
        query["level"] = level

    cursor = courses.find(query).sort([("rating", -1), ("title", 1)])
    return [serialize_doc(c) for c in cursor if c]


def get_course_by_id(course_id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
    """Fetch a single course document by ObjectId."""
    oid = to_object_id(course_id)
    if not oid:
        return None
    courses: Collection = get_collection("courses")
    doc = courses.find_one({"_id": oid})
    return serialize_doc(doc)


def search_courses(query: str, category: Optional[str] = None, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search courses by title or description, filtered by category and level."""
    courses: Collection = get_collection("courses")
    filter_conditions: List[Dict[str, Any]] = []

    q = (query or "").strip()
    if q:
        filter_conditions.append({
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"skills": {"$regex": q, "$options": "i"}}
            ]
        })
    if category and category != "All":
        filter_conditions.append({"category": category})
    if level and level != "All":
        filter_conditions.append({"level": level})

    query_doc = {"$and": filter_conditions} if filter_conditions else {}
    cursor = courses.find(query_doc).sort("rating", -1)
    return [serialize_doc(c) for c in cursor if c]


def update_course(
    course_id: Union[str, ObjectId],
    title: Optional[str] = None,
    category: Optional[str] = None,
    skills: Optional[List[str]] = None,
    level: Optional[str] = None,
    duration_hours: Optional[float] = None,
    rating: Optional[float] = None,
    description: Optional[str] = None
) -> Tuple[bool, str]:
    """Update details for an existing course."""
    oid = to_object_id(course_id)
    if not oid:
        return False, "Invalid Course ID."

    updates: Dict[str, Any] = {}
    if title is not None:
        if len(title.strip()) < 3:
            return False, "Title must be at least 3 characters."
        updates["title"] = title.strip()
    if category is not None:
        if category not in VALID_CATEGORIES:
            return False, f"Category must be one of {VALID_CATEGORIES}."
        updates["category"] = category
    if skills is not None:
        updates["skills"] = [s.strip() for s in skills if s and s.strip()]
    if level is not None:
        if level not in VALID_LEVELS:
            return False, f"Level must be one of {VALID_LEVELS}."
        updates["level"] = level
    if duration_hours is not None:
        if duration_hours < 0.5:
            return False, "Duration must be at least 0.5 hours."
        updates["duration_hours"] = float(duration_hours)
    if rating is not None:
        if rating < 0.0 or rating > 5.0:
            return False, "Rating must be between 0.0 and 5.0."
        updates["rating"] = float(rating)
    if description is not None:
        updates["description"] = description.strip()

    if not updates:
        return False, "No fields provided to update."

    courses: Collection = get_collection("courses")
    try:
        res = courses.update_one({"_id": oid}, {"$set": updates})
        if res.matched_count == 0:
            return False, "Course not found."
        return True, "Course updated successfully."
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}"
    except PyMongoError as e:
        return False, f"Database error: {str(e)}"


def delete_course(course_id: Union[str, ObjectId], cascade: bool = True) -> Tuple[bool, str]:
    """Delete a course safely with application-level referential checks."""
    oid = to_object_id(course_id)
    if not oid:
        return False, "Invalid Course ID."

    db = get_db()
    courses = db["courses"]
    enrollments = db["enrollments"]
    reviews = db["reviews"]

    try:
        course = courses.find_one({"_id": oid})
        if not course:
            return False, "Course not found."

        if not cascade:
            enr_count = enrollments.count_documents({"course_id": oid})
            if enr_count > 0:
                return False, f"Cannot delete: Course has {enr_count} active enrollments. Enable cascade delete."

        enrollments.delete_many({"course_id": oid})
        reviews.delete_many({"course_id": oid})
        courses.delete_one({"_id": oid})
        return True, f"Course '{course.get('title')}' and associated records deleted."
    except PyMongoError as e:
        return False, f"Database error during deletion: {str(e)}"


# ==============================================================================
# ENROLLMENTS CRUD OPERATIONS
# ==============================================================================

def enroll_student(
    student_id: Union[str, ObjectId],
    course_id: Union[str, ObjectId],
    progress: float = 0.0,
    status: str = "Not Started"
) -> Tuple[bool, str, Optional[str]]:
    """
    Enroll a student into a course.
    - Performs application-level referential integrity checks.
    - Prevents duplicate enrollments via compound check and index.
    - Enforces progress consistency (Completed requires progress=100.0).
    """
    s_oid = to_object_id(student_id)
    c_oid = to_object_id(course_id)
    if not s_oid or not c_oid:
        return False, "Invalid Student or Course ID.", None

    db = get_db()
    # 1. Referential check: verify student and course exist
    if not db["students"].find_one({"_id": s_oid}):
        return False, "Referential Integrity Error: Student does not exist in database.", None
    if not db["courses"].find_one({"_id": c_oid}):
        return False, "Referential Integrity Error: Course does not exist in database.", None

    # 2. Check for duplicate enrollment
    enrollments: Collection = db["enrollments"]
    existing = enrollments.find_one({"student_id": s_oid, "course_id": c_oid})
    if existing:
        return False, "Duplicate Enrollment: Student is already enrolled in this course.", None

    # 3. Consistency enforcement
    progress = max(0.0, min(100.0, float(progress)))
    if progress == 100.0:
        status = "Completed"
    elif progress > 0.0:
        status = "In Progress"
    else:
        status = "Not Started"

    doc = {
        "student_id": s_oid,
        "course_id": c_oid,
        "progress": progress,
        "status": status,
        "enrolled_at": datetime.now(timezone.utc)
    }

    try:
        res = enrollments.insert_one(doc)
        return True, "Enrollment created successfully.", str(res.inserted_id)
    except DuplicateKeyError:
        return False, "Duplicate Enrollment: Unique compound index constraint violated.", None
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}", None
    except PyMongoError as e:
        return False, f"Database error: {str(e)}", None


def get_student_enrollments(student_id: Union[str, ObjectId]) -> List[Dict[str, Any]]:
    """
    Get all enrollments for a given student with joined Course details.
    Uses MongoDB $lookup pipeline.
    """
    s_oid = to_object_id(student_id)
    if not s_oid:
        return []

    db = get_db()
    pipeline = [
        {"$match": {"student_id": s_oid}},
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course_info"
            }
        },
        {"$unwind": {"path": "$course_info", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"enrolled_at": -1}}
    ]

    results = []
    for doc in db["enrollments"].aggregate(pipeline):
        item = serialize_doc(doc)
        if "course_info" in item and item["course_info"]:
            item["course_info"] = serialize_doc(item["course_info"])
            item["course_title"] = item["course_info"].get("title", "Unknown Course")
            item["course_category"] = item["course_info"].get("category", "General")
        else:
            item["course_title"] = "Deleted / Missing Course"
            item["course_category"] = "N/A"
        results.append(item)
    return results


def get_all_enrollments(limit: int = 200) -> List[Dict[str, Any]]:
    """Get all enrollments joined with student name and course title."""
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": "students",
                "localField": "student_id",
                "foreignField": "_id",
                "as": "student"
            }
        },
        {"$unwind": {"path": "$student", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course"
            }
        },
        {"$unwind": {"path": "$course", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"enrolled_at": -1}},
        {"$limit": limit}
    ]

    results = []
    for doc in db["enrollments"].aggregate(pipeline):
        item = serialize_doc(doc)
        item["student_name"] = item.get("student", {}).get("name", "Unknown Student") if item.get("student") else "Unknown Student"
        item["course_title"] = item.get("course", {}).get("title", "Unknown Course") if item.get("course") else "Unknown Course"
        item["course_category"] = item.get("course", {}).get("category", "Unknown") if item.get("course") else "Unknown"
        results.append(item)
    return results


def update_enrollment_progress(
    enrollment_id: Union[str, ObjectId],
    new_progress: float
) -> Tuple[bool, str]:
    """
    Update student learning progress.
    Maintains strict consistency: 100% -> Completed, 0% -> Not Started, 1-99% -> In Progress.
    """
    oid = to_object_id(enrollment_id)
    if not oid:
        return False, "Invalid Enrollment ID."

    progress = max(0.0, min(100.0, float(new_progress)))
    if progress == 100.0:
        status = "Completed"
    elif progress > 0.0:
        status = "In Progress"
    else:
        status = "Not Started"

    enrollments: Collection = get_collection("enrollments")
    try:
        res = enrollments.update_one(
            {"_id": oid},
            {"$set": {"progress": progress, "status": status}}
        )
        if res.matched_count == 0:
            return False, "Enrollment record not found."
        return True, f"Progress updated to {progress}% ({status})."
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}"
    except PyMongoError as e:
        return False, f"Database error: {str(e)}"


def delete_enrollment(enrollment_id: Union[str, ObjectId]) -> Tuple[bool, str]:
    """Cancel / remove an enrollment."""
    oid = to_object_id(enrollment_id)
    if not oid:
        return False, "Invalid Enrollment ID."
    enrollments: Collection = get_collection("enrollments")
    try:
        res = enrollments.delete_one({"_id": oid})
        if res.deleted_count == 0:
            return False, "Enrollment record not found."
        return True, "Enrollment canceled successfully."
    except PyMongoError as e:
        return False, f"Database error: {str(e)}"


# ==============================================================================
# REVIEWS CRUD OPERATIONS
# ==============================================================================

def add_review(
    student_id: Union[str, ObjectId],
    course_id: Union[str, ObjectId],
    rating: int,
    comment: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Submit a course review.
    - Validates student and course exist (application-level foreign key check).
    - Validates rating is integer between 1 and 5.
    """
    s_oid = to_object_id(student_id)
    c_oid = to_object_id(course_id)
    if not s_oid or not c_oid:
        return False, "Invalid Student or Course ID.", None

    comment = (comment or "").strip()
    if len(comment) < 3:
        return False, "Comment must contain at least 3 characters.", None

    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            return False, "Rating must be an integer between 1 and 5.", None
    except (ValueError, TypeError):
        return False, "Rating must be a valid integer.", None

    db = get_db()
    # Check references
    if not db["students"].find_one({"_id": s_oid}):
        return False, "Referential Error: Reviewer (student) not found in database.", None
    if not db["courses"].find_one({"_id": c_oid}):
        return False, "Referential Error: Reviewed course not found in database.", None

    doc = {
        "student_id": s_oid,
        "course_id": c_oid,
        "rating": rating_int,
        "comment": comment,
        "created_at": datetime.now(timezone.utc)
    }

    reviews: Collection = db["reviews"]
    try:
        res = reviews.insert_one(doc)
        return True, "Review submitted successfully.", str(res.inserted_id)
    except WriteError as e:
        return False, f"MongoDB Schema Validation Error: {e.details.get('errmsg', str(e))}", None
    except PyMongoError as e:
        return False, f"Database error: {str(e)}", None


def get_course_reviews(course_id: Union[str, ObjectId]) -> List[Dict[str, Any]]:
    """Fetch all reviews for a course joined with student name."""
    c_oid = to_object_id(course_id)
    if not c_oid:
        return []

    db = get_db()
    pipeline = [
        {"$match": {"course_id": c_oid}},
        {
            "$lookup": {
                "from": "students",
                "localField": "student_id",
                "foreignField": "_id",
                "as": "student"
            }
        },
        {"$unwind": {"path": "$student", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"created_at": -1}}
    ]

    results = []
    for doc in db["reviews"].aggregate(pipeline):
        item = serialize_doc(doc)
        item["student_name"] = item.get("student", {}).get("name", "Anonymous Student") if item.get("student") else "Anonymous Student"
        results.append(item)
    return results


def get_all_reviews(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch all reviews joined with student and course details."""
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": "students",
                "localField": "student_id",
                "foreignField": "_id",
                "as": "student"
            }
        },
        {"$unwind": {"path": "$student", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course"
            }
        },
        {"$unwind": {"path": "$course", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"created_at": -1}},
        {"$limit": limit}
    ]

    results = []
    for doc in db["reviews"].aggregate(pipeline):
        item = serialize_doc(doc)
        item["student_name"] = item.get("student", {}).get("name", "Unknown Student") if item.get("student") else "Unknown Student"
        item["course_title"] = item.get("course", {}).get("title", "Unknown Course") if item.get("course") else "Unknown Course"
        results.append(item)
    return results


def delete_review(review_id: Union[str, ObjectId]) -> Tuple[bool, str]:
    """Delete a review by ID."""
    oid = to_object_id(review_id)
    if not oid:
        return False, "Invalid Review ID."
    reviews: Collection = get_collection("reviews")
    try:
        res = reviews.delete_one({"_id": oid})
        if res.deleted_count == 0:
            return False, "Review record not found."
        return True, "Review removed successfully."
    except PyMongoError as e:
        return False, f"Database error: {str(e)}"
