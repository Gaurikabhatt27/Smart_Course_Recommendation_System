"""
recommendations.py
------------------
Explainable, rule-based course recommendation engine.
Calculates ranked course recommendations using a deterministic scoring formula:
  Final Score = (0.50 * Skill Match) + (0.30 * Interest Match) + (0.20 * Rating Score)
All components are strictly normalized to 0-100.
Excludes courses the student is already enrolled in.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Tuple
from bson import ObjectId
from database import get_db, get_collection
from operations import to_object_id, serialize_doc


def calculate_skill_match_score(student_skills: List[str], course_skills: List[str]) -> Tuple[float, List[str]]:
    """
    Compute Skill Match Score (0 to 100).
    Formula: (Matching Course Skills / Total Course Skills) * 100
    Returns:
        (score, matching_skills_list)
    """
    if not course_skills:
        return 0.0, []

    s_skills_norm = {s.strip().lower() for s in student_skills if s and s.strip()}
    matched = []
    for c_skill in course_skills:
        c_clean = c_skill.strip()
        if c_clean.lower() in s_skills_norm:
            matched.append(c_clean)

    score = (len(matched) / len(course_skills)) * 100.0
    return round(score, 2), matched


def calculate_interest_match_score(
    student_interests: List[str],
    course_category: str,
    course_skills: List[str]
) -> Tuple[float, List[str]]:
    """
    Compute Interest Match Score (0 to 100).
    Deterministic rule:
    - Compare student's interests against the course category and course skills.
    - If student has no interests, score is 0.0.
    - If student's interests overlap with course category or skills, score is:
      min(100.0, (Overlap Count / Total Student Interests) * 100.0)
    Returns:
        (score, matched_interests)
    """
    if not student_interests:
        return 0.0, []

    # Normalized topic set for the course (category + all course skills)
    course_topics = {course_category.strip().lower()}
    for cs in course_skills:
        course_topics.add(cs.strip().lower())

    matched_interests = []
    for interest in student_interests:
        int_clean = interest.strip()
        int_lower = int_clean.lower()
        # Direct equality or substring match
        if int_lower in course_topics or any(int_lower in topic or topic in int_lower for topic in course_topics):
            matched_interests.append(int_clean)

    score = (len(matched_interests) / len(student_interests)) * 100.0
    return round(min(100.0, score), 2), matched_interests


def calculate_course_rating_score(rating: Optional[float]) -> float:
    """
    Normalize Course Rating (0.0 to 5.0) into a 0-100 scale.
    Formula: (Course Rating / 5.0) * 100
    """
    if rating is None or rating < 0.0:
        return 0.0
    clamped = max(0.0, min(5.0, float(rating)))
    return round((clamped / 5.0) * 100.0, 2)


def generate_explanation(
    matched_skills: List[str],
    matched_interests: List[str],
    rating: float,
    course_category: str
) -> str:
    """Produce human-readable explanation of why this course was recommended."""
    parts = []
    if matched_skills:
        parts.append(f"Builds upon your skills: {', '.join(matched_skills)}")
    else:
        parts.append("Introduces valuable new foundational skills")

    if matched_interests:
        parts.append(f"Aligns with your interests in {', '.join(matched_interests)}")
    else:
        parts.append(f"Relevant to the {course_category} domain")

    parts.append(f"High student rating: {rating:.1f}/5.0")
    return ". ".join(parts) + "."


def get_recommendations_for_student(
    student_id: Union[str, ObjectId],
    top_n: int = 5,
    save_to_log: bool = False
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Generate top N course recommendations for a student.
    - Excludes courses where student is already enrolled.
    - Calculates Skill Match (50%), Interest Match (30%), and Rating Score (20%).
    - Returns ranked list of courses with detailed breakdown.
    """
    s_oid = to_object_id(student_id)
    if not s_oid:
        return False, "Invalid Student ID.", []

    db = get_db()
    student = db["students"].find_one({"_id": s_oid})
    if not student:
        return False, "Student profile not found.", []

    # 1. Fetch IDs of already enrolled courses
    enrolled_course_ids = db["enrollments"].distinct("course_id", {"student_id": s_oid})

    # 2. Query available candidate courses (excluding enrolled)
    candidate_filter = {"_id": {"$nin": enrolled_course_ids}}
    candidate_courses = list(db["courses"].find(candidate_filter))

    if not candidate_courses:
        return True, "No candidate courses available (student has enrolled in all available courses).", []

    student_skills = student.get("skills", [])
    student_interests = student.get("interests", [])

    scored_courses = []
    for course in candidate_courses:
        c_skills = course.get("skills", [])
        c_category = course.get("category", "")
        c_rating = course.get("rating", 0.0)

        # Component scores (all 0-100)
        skill_score, matched_skills = calculate_skill_match_score(student_skills, c_skills)
        interest_score, matched_interests = calculate_interest_match_score(
            student_interests, c_category, c_skills
        )
        rating_score = calculate_course_rating_score(c_rating)

        # Weighted composite score
        final_score = (0.50 * skill_score) + (0.30 * interest_score) + (0.20 * rating_score)
        final_score = round(final_score, 2)

        explanation = generate_explanation(matched_skills, matched_interests, c_rating, c_category)

        item = serialize_doc(course)
        item["score"] = final_score
        item["skill_score"] = skill_score
        item["interest_score"] = interest_score
        item["rating_score"] = rating_score
        item["matched_skills"] = matched_skills
        item["matched_interests"] = matched_interests
        item["explanation"] = explanation
        scored_courses.append(item)

    # Sort descending by final score
    scored_courses.sort(key=lambda x: x["score"], reverse=True)
    top_recommendations = scored_courses[:top_n]

    # Optional log persistence to recommendation_logs collection
    if save_to_log and top_recommendations:
        try:
            log_doc = {
                "student_id": s_oid,
                "student_name": student.get("name"),
                "recommended_at": datetime.now(timezone.utc),
                "top_recommendations": [
                    {
                        "course_id": to_object_id(r["_id"]),
                        "title": r["title"],
                        "score": r["score"],
                        "explanation": r["explanation"]
                    }
                    for r in top_recommendations
                ]
            }
            db["recommendation_logs"].insert_one(log_doc)
        except Exception:
            pass  # Non-blocking log insertion

    return True, f"Generated {len(top_recommendations)} recommendations successfully.", top_recommendations
