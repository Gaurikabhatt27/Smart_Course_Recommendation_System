"""
setup_db.py
-----------
Database Initialization and Schema Setup Script.
- Configures collection JSON Schema validators on all 4 collections.
- Establishes performance, compound, unique, and text indexes.
- Idempotently populates realistic seed data (Students, Courses, Enrollments, Reviews).
- Validates cross-collection referential integrity.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from bson import ObjectId
from pymongo.errors import PyMongoError, OperationFailure
from database import get_db, check_connection

# ==============================================================================
# 1. JSON SCHEMA VALIDATORS
# ==============================================================================

STUDENT_VALIDATOR: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "email", "skills", "interests", "level", "created_at"],
        "properties": {
            "name": {
                "bsonType": "string",
                "minLength": 2,
                "description": "Student full name is required and must have at least 2 characters."
            },
            "email": {
                "bsonType": "string",
                "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                "description": "Valid email address is required and must follow standard RFC email format."
            },
            "skills": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "List of current technical skills."
            },
            "interests": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "List of academic and domain interests."
            },
            "level": {
                "enum": ["Beginner", "Intermediate", "Advanced"],
                "description": "Student proficiency level must be Beginner, Intermediate, or Advanced."
            },
            "created_at": {
                "bsonType": "date",
                "description": "Timestamp when student profile was created."
            }
        }
    }
}

COURSE_VALIDATOR: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["title", "category", "skills", "level", "duration_hours", "rating", "created_at"],
        "properties": {
            "title": {
                "bsonType": "string",
                "minLength": 3,
                "description": "Course title is required and must be at least 3 characters."
            },
            "category": {
                "bsonType": "string",
                "enum": [
                    "Data Science",
                    "Artificial Intelligence",
                    "Web Development",
                    "Database Systems",
                    "Cloud Computing",
                    "Cybersecurity"
                ],
                "description": "Course category must be one of the recognized domains."
            },
            "skills": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "Key technical skills taught in this course."
            },
            "level": {
                "enum": ["Beginner", "Intermediate", "Advanced"],
                "description": "Course difficulty level must be Beginner, Intermediate, or Advanced."
            },
            "duration_hours": {
                "bsonType": ["double", "int", "long", "decimal"],
                "minimum": 0.5,
                "description": "Duration in hours must be a positive number of at least 0.5 hours."
            },
            "rating": {
                "bsonType": ["double", "int", "long", "decimal"],
                "minimum": 0.0,
                "maximum": 5.0,
                "description": "Course rating must be a decimal value between 0.0 and 5.0."
            },
            "description": {
                "bsonType": "string",
                "description": "Comprehensive course syllabus and objective summary."
            },
            "created_at": {
                "bsonType": "date",
                "description": "Timestamp when course was added to catalog."
            }
        }
    }
}

ENROLLMENT_VALIDATOR: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["student_id", "course_id", "progress", "status", "enrolled_at"],
        "properties": {
            "student_id": {
                "bsonType": "objectId",
                "description": "BSON ObjectId referencing a valid student document."
            },
            "course_id": {
                "bsonType": "objectId",
                "description": "BSON ObjectId referencing a valid course document."
            },
            "progress": {
                "bsonType": ["double", "int", "long", "decimal"],
                "minimum": 0.0,
                "maximum": 100.0,
                "description": "Completion percentage must be between 0 and 100."
            },
            "status": {
                "enum": ["Not Started", "In Progress", "Completed"],
                "description": "Enrollment status must be Not Started, In Progress, or Completed."
            },
            "enrolled_at": {
                "bsonType": "date",
                "description": "Timestamp when enrollment occurred."
            }
        }
    }
}

REVIEW_VALIDATOR: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["student_id", "course_id", "rating", "comment", "created_at"],
        "properties": {
            "student_id": {
                "bsonType": "objectId",
                "description": "BSON ObjectId referencing the reviewer (student)."
            },
            "course_id": {
                "bsonType": "objectId",
                "description": "BSON ObjectId referencing the reviewed course."
            },
            "rating": {
                "bsonType": ["int", "long"],
                "minimum": 1,
                "maximum": 5,
                "description": "Rating must be an integer score from 1 to 5 stars."
            },
            "comment": {
                "bsonType": "string",
                "minLength": 3,
                "description": "Review feedback comment must contain at least 3 characters."
            },
            "created_at": {
                "bsonType": "date",
                "description": "Timestamp when review was submitted."
            }
        }
    }
}

VALIDATORS = {
    "students": STUDENT_VALIDATOR,
    "courses": COURSE_VALIDATOR,
    "enrollments": ENROLLMENT_VALIDATOR,
    "reviews": REVIEW_VALIDATOR,
}


# ==============================================================================
# 2. SCHEMA AND VALIDATION SETUP
# ==============================================================================

def apply_validators(db) -> Dict[str, str]:
    """
    Apply JSON Schema validators to all collections using create_collection or collMod.
    Safe to run repeatedly.
    """
    results = {}
    existing_collections = set(db.list_collection_names())

    for coll_name, validator in VALIDATORS.items():
        try:
            if coll_name in existing_collections:
                db.command(
                    "collMod",
                    coll_name,
                    validator=validator,
                    validationLevel="strict",
                    validationAction="error"
                )
                results[coll_name] = "Updated existing validator via collMod"
            else:
                db.create_collection(
                    coll_name,
                    validator=validator,
                    validationLevel="strict",
                    validationAction="error"
                )
                results[coll_name] = "Created new collection with strict validator"
        except OperationFailure as e:
            results[coll_name] = f"Warning: {e.details.get('errmsg', str(e))}"
    return results


# ==============================================================================
# 3. INDEX CONFIGURATION
# ==============================================================================

def create_indexes(db) -> Dict[str, List[str]]:
    """
    Establish performance indexes, compound keys, and unique constraints.
    """
    results: Dict[str, List[str]] = {}

    # Students collection indexes
    students_col = db["students"]
    s_idx1 = students_col.create_index(
        [("email", 1)],
        unique=True,
        name="idx_students_email_unique"
    )
    s_idx2 = students_col.create_index(
        [("level", 1)],
        name="idx_students_level"
    )
    results["students"] = [s_idx1, s_idx2]

    # Courses collection indexes
    courses_col = db["courses"]
    c_idx1 = courses_col.create_index(
        [("category", 1)],
        name="idx_courses_category"
    )
    c_idx2 = courses_col.create_index(
        [("category", 1), ("level", 1)],
        name="idx_courses_category_level"
    )
    # Text index on title and description for full-text search capability
    c_idx3 = courses_col.create_index(
        [("title", "text"), ("description", "text")],
        name="idx_courses_text_title_desc"
    )
    c_idx4 = courses_col.create_index(
        [("rating", -1)],
        name="idx_courses_rating"
    )
    results["courses"] = [c_idx1, c_idx2, c_idx3, c_idx4]

    # Enrollments collection indexes
    enrollments_col = db["enrollments"]
    e_idx1 = enrollments_col.create_index(
        [("student_id", 1)],
        name="idx_enrollments_student_id"
    )
    e_idx2 = enrollments_col.create_index(
        [("course_id", 1)],
        name="idx_enrollments_course_id"
    )
    # Compound unique index prevents duplicate enrollments for same student + course
    e_idx3 = enrollments_col.create_index(
        [("student_id", 1), ("course_id", 1)],
        unique=True,
        name="idx_enrollments_student_course_unique"
    )
    e_idx4 = enrollments_col.create_index(
        [("status", 1)],
        name="idx_enrollments_status"
    )
    results["enrollments"] = [e_idx1, e_idx2, e_idx3, e_idx4]

    # Reviews collection indexes
    reviews_col = db["reviews"]
    r_idx1 = reviews_col.create_index(
        [("course_id", 1)],
        name="idx_reviews_course_id"
    )
    r_idx2 = reviews_col.create_index(
        [("student_id", 1)],
        name="idx_reviews_student_id"
    )
    results["reviews"] = [r_idx1, r_idx2]

    return results


# ==============================================================================
# 4. REALISTIC SEED DATA (IDEMPOTENT)
# ==============================================================================

SEED_STUDENTS = [
    {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "skills": ["Python", "SQL", "Pandas"],
        "interests": ["Data Science", "Artificial Intelligence"],
        "level": "Intermediate",
    },
    {
        "name": "Priya Patel",
        "email": "priya.patel@example.com",
        "skills": ["HTML", "CSS", "JavaScript", "React"],
        "interests": ["Web Development", "Cloud Computing"],
        "level": "Intermediate",
    },
    {
        "name": "Rohan Verma",
        "email": "rohan.verma@example.com",
        "skills": ["Python", "Machine Learning", "PyTorch", "Docker"],
        "interests": ["Artificial Intelligence", "Data Science"],
        "level": "Advanced",
    },
    {
        "name": "Ananya Iyer",
        "email": "ananya.iyer@example.com",
        "skills": ["SQL", "Data Modeling", "MongoDB"],
        "interests": ["Database Systems", "Cloud Computing"],
        "level": "Intermediate",
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.singh@example.com",
        "skills": ["Linux", "Networking", "Bash"],
        "interests": ["Cybersecurity", "Cloud Computing"],
        "level": "Beginner",
    },
    {
        "name": "Neha Gupta",
        "email": "neha.gupta@example.com",
        "skills": ["Python", "Statistics"],
        "interests": ["Data Science", "Database Systems"],
        "level": "Beginner",
    },
    {
        "name": "Aditya Kulkarni",
        "email": "aditya.k@example.com",
        "skills": ["AWS", "Docker", "Kubernetes", "Terraform"],
        "interests": ["Cloud Computing", "Cybersecurity"],
        "level": "Advanced",
    },
    {
        "name": "Sneha Roy",
        "email": "sneha.roy@example.com",
        "skills": ["JavaScript", "Node.js", "Express", "MongoDB"],
        "interests": ["Web Development", "Database Systems"],
        "level": "Intermediate",
    },
    {
        "name": "Karan Malhotra",
        "email": "karan.m@example.com",
        "skills": ["C++", "Algorithms", "Data Structures"],
        "interests": ["Artificial Intelligence", "Database Systems"],
        "level": "Beginner",
    },
    {
        "name": "Divya Nambiar",
        "email": "divya.n@example.com",
        "skills": ["Ethical Hacking", "Wireshark", "Cryptography"],
        "interests": ["Cybersecurity"],
        "level": "Intermediate",
    }
]

SEED_COURSES = [
    # Data Science
    {
        "title": "Mastering Data Science with Python & Pandas",
        "category": "Data Science",
        "skills": ["Python", "Pandas", "NumPy", "Statistics", "Data Visualization"],
        "level": "Intermediate",
        "duration_hours": 36.0,
        "rating": 4.8,
        "description": "Comprehensive practical data science course covering exploratory data analysis, data wrangling, and statistical inference with Python."
    },
    {
        "title": "Foundations of Applied Statistics & Probability",
        "category": "Data Science",
        "skills": ["Statistics", "Python", "Probability", "Data Analysis"],
        "level": "Beginner",
        "duration_hours": 20.0,
        "rating": 4.5,
        "description": "Essential mathematical and statistical foundations required for data scientists and machine learning engineers."
    },
    # Artificial Intelligence
    {
        "title": "Deep Learning & Neural Networks with PyTorch",
        "category": "Artificial Intelligence",
        "skills": ["Python", "PyTorch", "Deep Learning", "Machine Learning", "Computer Vision"],
        "level": "Advanced",
        "duration_hours": 48.0,
        "rating": 4.9,
        "description": "Hands-on deep dive into convolutional networks, transformers, and recurrent architectures using PyTorch."
    },
    {
        "title": "Practical Machine Learning for Beginners",
        "category": "Artificial Intelligence",
        "skills": ["Python", "Scikit-Learn", "Machine Learning", "Data Analysis"],
        "level": "Beginner",
        "duration_hours": 28.0,
        "rating": 4.6,
        "description": "Intuitive, beginner-friendly introduction to regression, classification, clustering, and model validation."
    },
    # Web Development
    {
        "title": "Full-Stack Web Development with React & Node.js",
        "category": "Web Development",
        "skills": ["JavaScript", "React", "Node.js", "Express", "HTML", "CSS"],
        "level": "Intermediate",
        "duration_hours": 50.0,
        "rating": 4.7,
        "description": "Build modern responsive full-stack applications with component-driven React frontends and Node.js REST APIs."
    },
    {
        "title": "Modern Frontend Fundamentals: HTML, CSS & Modern JS",
        "category": "Web Development",
        "skills": ["HTML", "CSS", "JavaScript", "Responsive Design"],
        "level": "Beginner",
        "duration_hours": 18.0,
        "rating": 4.4,
        "description": "Master modern responsive design, semantic HTML5, Flexbox, CSS Grid, and modern ES6+ JavaScript."
    },
    # Database Systems
    {
        "title": "Intelligent NoSQL Databases: MongoDB & PyMongo",
        "category": "Database Systems",
        "skills": ["MongoDB", "PyMongo", "NoSQL", "Data Modeling", "Aggregation"],
        "level": "Intermediate",
        "duration_hours": 32.0,
        "rating": 4.9,
        "description": "In-depth course on MongoDB document modeling, indexing strategies, validation schemas, and complex aggregation pipelines."
    },
    {
        "title": "Relational Database Design & High-Performance SQL",
        "category": "Database Systems",
        "skills": ["SQL", "Data Modeling", "Database Design", "Normalization", "PostgreSQL"],
        "level": "Intermediate",
        "duration_hours": 25.0,
        "rating": 4.5,
        "description": "Comprehensive study of relational database normalization, ACID transactions, complex queries, and index tuning."
    },
    {
        "title": "Distributed Systems & Advanced Database Internals",
        "category": "Database Systems",
        "skills": ["Distributed Systems", "Data Modeling", "Database Design", "Replication", "Sharding"],
        "level": "Advanced",
        "duration_hours": 42.0,
        "rating": 4.8,
        "description": "Explore replication, sharding, consensus protocols, consistency models, and transaction management in distributed stores."
    },
    # Cloud Computing
    {
        "title": "Cloud Architecture & Microservices on AWS",
        "category": "Cloud Computing",
        "skills": ["AWS", "Docker", "Microservices", "Cloud Architecture"],
        "level": "Advanced",
        "duration_hours": 40.0,
        "rating": 4.8,
        "description": "Design resilient, scalable cloud architectures using AWS Lambda, ECS, API Gateway, and managed databases."
    },
    {
        "title": "Containerization & DevOps with Docker and Kubernetes",
        "category": "Cloud Computing",
        "skills": ["Docker", "Kubernetes", "Linux", "DevOps", "CI/CD"],
        "level": "Intermediate",
        "duration_hours": 30.0,
        "rating": 4.7,
        "description": "Production container workflows: Docker multi-stage builds, Kubernetes deployments, services, and ingress controllers."
    },
    {
        "title": "Introduction to Cloud Computing Essentials",
        "category": "Cloud Computing",
        "skills": ["Cloud Architecture", "Linux", "Networking", "AWS"],
        "level": "Beginner",
        "duration_hours": 16.0,
        "rating": 4.3,
        "description": "Fundamental concepts of cloud computing, IaaS vs PaaS vs SaaS, virtual networks, and storage buckets."
    },
    # Cybersecurity
    {
        "title": "Hands-On Ethical Hacking & Network Defense",
        "category": "Cybersecurity",
        "skills": ["Networking", "Linux", "Ethical Hacking", "Wireshark", "Penetration Testing"],
        "level": "Intermediate",
        "duration_hours": 35.0,
        "rating": 4.7,
        "description": "Network packet inspection, vulnerability scanning, penetration testing techniques, and defense strategies."
    },
    {
        "title": "Applied Cryptography and Secure System Design",
        "category": "Cybersecurity",
        "skills": ["Cryptography", "Security Protocols", "Python", "Secure Coding"],
        "level": "Advanced",
        "duration_hours": 34.0,
        "rating": 4.6,
        "description": "Mathematical principles of symmetric and asymmetric encryption, digital signatures, PKI, and secure session management."
    }
]


def seed_database(db) -> Dict[str, Any]:
    """
    Populate seed students, courses, enrollments, and reviews idempotently.
    Uses natural keys (email for students, title for courses) to prevent duplication.
    """
    now = datetime.now(timezone.utc)
    summary = {"students": 0, "courses": 0, "enrollments": 0, "reviews": 0}

    # 1. Upsert Students
    student_id_map: Dict[str, ObjectId] = {}
    for s_data in SEED_STUDENTS:
        email = s_data["email"]
        update_doc = {
            "$set": {
                "name": s_data["name"],
                "email": email,
                "skills": s_data["skills"],
                "interests": s_data["interests"],
                "level": s_data["level"],
            },
            "$setOnInsert": {
                "created_at": now
            }
        }
        res = db["students"].update_one({"email": email}, update_doc, upsert=True)
        # Fetch the document to record its ObjectId
        doc = db["students"].find_one({"email": email}, {"_id": 1})
        if doc:
            student_id_map[email] = doc["_id"]
        if res.upserted_id or res.modified_count:
            summary["students"] += 1

    # 2. Upsert Courses
    course_id_map: Dict[str, ObjectId] = {}
    for c_data in SEED_COURSES:
        title = c_data["title"]
        update_doc = {
            "$set": {
                "title": title,
                "category": c_data["category"],
                "skills": c_data["skills"],
                "level": c_data["level"],
                "duration_hours": float(c_data["duration_hours"]),
                "rating": float(c_data["rating"]),
                "description": c_data["description"],
            },
            "$setOnInsert": {
                "created_at": now
            }
        }
        res = db["courses"].update_one({"title": title}, update_doc, upsert=True)
        doc = db["courses"].find_one({"title": title}, {"_id": 1})
        if doc:
            course_id_map[title] = doc["_id"]
        if res.upserted_id or res.modified_count:
            summary["courses"] += 1

    # 3. Seed Enrollments (at least 20 realistic enrollments)
    # Mapping of (student_email, course_title) -> (progress, status)
    # Completed enrollments MUST have progress=100.0
    enrollments_plan = [
        ("aarav.sharma@example.com", "Mastering Data Science with Python & Pandas", 100.0, "Completed"),
        ("aarav.sharma@example.com", "Intelligent NoSQL Databases: MongoDB & PyMongo", 65.0, "In Progress"),
        ("aarav.sharma@example.com", "Foundations of Applied Statistics & Probability", 100.0, "Completed"),
        ("priya.patel@example.com", "Full-Stack Web Development with React & Node.js", 100.0, "Completed"),
        ("priya.patel@example.com", "Modern Frontend Fundamentals: HTML, CSS & Modern JS", 100.0, "Completed"),
        ("priya.patel@example.com", "Cloud Architecture & Microservices on AWS", 30.0, "In Progress"),
        ("rohan.verma@example.com", "Deep Learning & Neural Networks with PyTorch", 100.0, "Completed"),
        ("rohan.verma@example.com", "Practical Machine Learning for Beginners", 100.0, "Completed"),
        ("rohan.verma@example.com", "Containerization & DevOps with Docker and Kubernetes", 75.0, "In Progress"),
        ("ananya.iyer@example.com", "Intelligent NoSQL Databases: MongoDB & PyMongo", 100.0, "Completed"),
        ("ananya.iyer@example.com", "Relational Database Design & High-Performance SQL", 100.0, "Completed"),
        ("ananya.iyer@example.com", "Distributed Systems & Advanced Database Internals", 45.0, "In Progress"),
        ("vikram.singh@example.com", "Hands-On Ethical Hacking & Network Defense", 50.0, "In Progress"),
        ("vikram.singh@example.com", "Introduction to Cloud Computing Essentials", 0.0, "Not Started"),
        ("neha.gupta@example.com", "Foundations of Applied Statistics & Probability", 80.0, "In Progress"),
        ("neha.gupta@example.com", "Mastering Data Science with Python & Pandas", 0.0, "Not Started"),
        ("aditya.k@example.com", "Cloud Architecture & Microservices on AWS", 100.0, "Completed"),
        ("aditya.k@example.com", "Containerization & DevOps with Docker and Kubernetes", 100.0, "Completed"),
        ("aditya.k@example.com", "Applied Cryptography and Secure System Design", 25.0, "In Progress"),
        ("sneha.roy@example.com", "Full-Stack Web Development with React & Node.js", 85.0, "In Progress"),
        ("sneha.roy@example.com", "Intelligent NoSQL Databases: MongoDB & PyMongo", 100.0, "Completed"),
        ("karan.m@example.com", "Practical Machine Learning for Beginners", 40.0, "In Progress"),
        ("divya.n@example.com", "Hands-On Ethical Hacking & Network Defense", 100.0, "Completed"),
        ("divya.n@example.com", "Applied Cryptography and Secure System Design", 60.0, "In Progress")
    ]

    for email, title, prog, stat in enrollments_plan:
        s_id = student_id_map.get(email)
        c_id = course_id_map.get(title)
        if not s_id or not c_id:
            continue
        
        # Consistent status and progress check
        if stat == "Completed":
            prog = 100.0
        elif stat == "Not Started":
            prog = 0.0

        update_doc = {
            "$set": {
                "student_id": s_id,
                "course_id": c_id,
                "progress": float(prog),
                "status": stat,
            },
            "$setOnInsert": {
                "enrolled_at": now
            }
        }
        res = db["enrollments"].update_one(
            {"student_id": s_id, "course_id": c_id},
            update_doc,
            upsert=True
        )
        if res.upserted_id or res.modified_count:
            summary["enrollments"] += 1

    # 4. Seed Reviews (at least 12 realistic reviews)
    reviews_plan = [
        ("aarav.sharma@example.com", "Mastering Data Science with Python & Pandas", 5, "Outstanding curriculum! Clear explanations and great practical exercises with real datasets."),
        ("aarav.sharma@example.com", "Foundations of Applied Statistics & Probability", 4, "Solid mathematical foundation. Helped me truly understand probability distributions."),
        ("priya.patel@example.com", "Full-Stack Web Development with React & Node.js", 5, "The full-stack projects were very industry-relevant. Loved the backend architecture modules."),
        ("priya.patel@example.com", "Modern Frontend Fundamentals: HTML, CSS & Modern JS", 4, "Very helpful CSS Grid and Flexbox breakdowns. Great for leveling up frontend styling."),
        ("rohan.verma@example.com", "Deep Learning & Neural Networks with PyTorch", 5, "Superb coverage of Transformers and attention mechanisms. Code quality is top-notch."),
        ("rohan.verma@example.com", "Practical Machine Learning for Beginners", 4, "Clear explanations of core algorithms without getting bogged down in unnecessary math."),
        ("ananya.iyer@example.com", "Intelligent NoSQL Databases: MongoDB & PyMongo", 5, "Best MongoDB course available! The aggregation pipeline breakdowns and indexing demos are fantastic."),
        ("ananya.iyer@example.com", "Relational Database Design & High-Performance SQL", 4, "Deep dive into query execution plans and index selectivity. Highly recommended for DB admins."),
        ("aditya.k@example.com", "Cloud Architecture & Microservices on AWS", 5, "Well-architected microservices hands-on labs with ECS, IAM policies, and load balancing."),
        ("aditya.k@example.com", "Containerization & DevOps with Docker and Kubernetes", 5, "From Docker basics to multi-node Kubernetes deployments with Helm charts. Super practical!"),
        ("sneha.roy@example.com", "Intelligent NoSQL Databases: MongoDB & PyMongo", 5, "The schema validation and PyMongo CRUD patterns helped me build my web app backends seamlessly."),
        ("divya.n@example.com", "Hands-On Ethical Hacking & Network Defense", 5, "Realistic lab environments and packet analysis. Helped me prepare for cybersecurity certifications."),
        ("karan.m@example.com", "Practical Machine Learning for Beginners", 4, "Very approachable for 2nd/3rd year engineering students. Scikit-learn examples worked smoothly.")
    ]

    for email, title, rating_val, comment_text in reviews_plan:
        s_id = student_id_map.get(email)
        c_id = course_id_map.get(title)
        if not s_id or not c_id:
            continue

        update_doc = {
            "$set": {
                "student_id": s_id,
                "course_id": c_id,
                "rating": int(rating_val),
                "comment": comment_text,
            },
            "$setOnInsert": {
                "created_at": now
            }
        }
        res = db["reviews"].update_one(
            {"student_id": s_id, "course_id": c_id},
            update_doc,
            upsert=True
        )
        if res.upserted_id or res.modified_count:
            summary["reviews"] += 1

    return summary


def run_setup() -> bool:
    """Execute complete database setup with validators, indexes, and seed data."""
    is_connected, msg, meta = check_connection()
    if not is_connected:
        print(f"[ERROR] Cannot setup database: {msg}")
        return False

    db = get_db()
    print("=" * 65)
    print("SMART COURSE RECOMMENDATION SYSTEM USING MONGODB")
    print("Database Setup & Schema Initialization")
    print("=" * 65)
    print(f"Target Database : {db.name}")
    print(f"MongoDB Version : {meta.get('version', 'N/A')}")
    print(f"Server URI      : {meta.get('masked_uri')}")
    print("-" * 65)

    print("\n[1/3] Configuring JSON Schema Collection Validators...")
    validator_results = apply_validators(db)
    for coll, status in validator_results.items():
        print(f"  • {coll.ljust(14)}: {status}")

    print("\n[2/3] Establishing Performance and Integrity Indexes...")
    index_results = create_indexes(db)
    for coll, idx_list in index_results.items():
        print(f"  • {coll.ljust(14)}: {len(idx_list)} indexes -> {', '.join(idx_list)}")

    print("\n[3/3] Populating Idempotent Realistic Seed Data...")
    summary = seed_database(db)
    print(f"  • Students upserted    : {summary['students']} (Total in DB: {db['students'].count_documents({})})")
    print(f"  • Courses upserted     : {summary['courses']} (Total in DB: {db['courses'].count_documents({})})")
    print(f"  • Enrollments upserted : {summary['enrollments']} (Total in DB: {db['enrollments'].count_documents({})})")
    print(f"  • Reviews upserted     : {summary['reviews']} (Total in DB: {db['reviews'].count_documents({})})")

    print("\n" + "=" * 65)
    print("DATABASE SETUP COMPLETE AND VERIFIED!")
    print("=" * 65)
    return True


if __name__ == "__main__":
    run_setup()
