"""
analytics.py
------------
MongoDB Aggregation Pipelines for Learning Analytics.
Executes real aggregation pipelines via PyMongo and exposes both
the pipeline definitions (for viva / technical inspection) and
formatted data for Plotly visualizations.
"""

from typing import Dict, Any, List
from database import get_db

# ==============================================================================
# PIPELINE DEFINITIONS (Documented for academic display & viva examination)
# ==============================================================================

POPULAR_COURSES_PIPELINE: List[Dict[str, Any]] = [
    # Stage 1: Group enrollments by course_id and count total enrollments
    {
        "$group": {
            "_id": "$course_id",
            "enrollment_count": {"$sum": 1}
        }
    },
    # Stage 2: Sort descending by enrollment volume
    {
        "$sort": {"enrollment_count": -1}
    },
    # Stage 3: Join course details from courses collection
    {
        "$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    # Stage 4: Deconstruct array of joined courses
    {
        "$unwind": "$course"
    },
    # Stage 5: Reshape output documents
    {
        "$project": {
            "_id": 0,
            "course_id": {"$toString": "$_id"},
            "title": "$course.title",
            "category": "$course.category",
            "rating": "$course.rating",
            "enrollment_count": 1
        }
    }
]

COURSE_RATINGS_PIPELINE: List[Dict[str, Any]] = [
    # Stage 1: Group reviews by course_id, compute average rating and review volume
    {
        "$group": {
            "_id": "$course_id",
            "avg_rating": {"$avg": "$rating"},
            "review_count": {"$sum": 1}
        }
    },
    # Stage 2: Join course information to get title and category
    {
        "$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    # Stage 3: Flatten course document
    {
        "$unwind": "$course"
    },
    # Stage 4: Sort descending by average review rating
    {
        "$sort": {"avg_rating": -1}
    },
    # Stage 5: Shape fields and round rating
    {
        "$project": {
            "_id": 0,
            "course_id": {"$toString": "$_id"},
            "title": "$course.title",
            "category": "$course.category",
            "avg_rating": {"$round": ["$avg_rating", 2]},
            "review_count": 1
        }
    }
]

CATEGORY_ENROLLMENTS_PIPELINE: List[Dict[str, Any]] = [
    # Stage 1: Join enrollments with courses to retrieve category
    {
        "$lookup": {
            "from": "courses",
            "localField": "course_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    # Stage 2: Flatten joined course
    {
        "$unwind": "$course"
    },
    # Stage 3: Group by course category and tally enrollments
    {
        "$group": {
            "_id": "$course.category",
            "enrollment_count": {"$sum": 1}
        }
    },
    # Stage 4: Sort descending by enrollment popularity
    {
        "$sort": {"enrollment_count": -1}
    },
    # Stage 5: Format output
    {
        "$project": {
            "_id": 0,
            "category": "$_id",
            "enrollment_count": 1
        }
    }
]

STUDENT_PROGRESS_PIPELINE: List[Dict[str, Any]] = [
    # Stage 1: Group enrollments by course_id, compute avg progress & status counts
    {
        "$group": {
            "_id": "$course_id",
            "avg_progress": {"$avg": "$progress"},
            "total_students": {"$sum": 1},
            "completed_count": {
                "$sum": {
                    "$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]
                }
            },
            "in_progress_count": {
                "$sum": {
                    "$cond": [{"$eq": ["$status", "In Progress"]}, 1, 0]
                }
            },
            "not_started_count": {
                "$sum": {
                    "$cond": [{"$eq": ["$status", "Not Started"]}, 1, 0]
                }
            }
        }
    },
    # Stage 2: Join course title and category
    {
        "$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    # Stage 3: Unwind course array
    {
        "$unwind": "$course"
    },
    # Stage 4: Sort by total student enrollments
    {
        "$sort": {"total_students": -1}
    },
    # Stage 5: Format presentation fields
    {
        "$project": {
            "_id": 0,
            "course_id": {"$toString": "$_id"},
            "title": "$course.title",
            "category": "$course.category",
            "avg_progress": {"$round": ["$avg_progress", 1]},
            "total_students": 1,
            "completed_count": 1,
            "in_progress_count": 1,
            "not_started_count": 1,
            "completion_rate": {
                "$round": [
                    {
                        "$multiply": [
                            {"$divide": ["$completed_count", "$total_students"]},
                            100
                        ]
                    },
                    1
                ]
            }
        }
    }
]


# ==============================================================================
# ANALYTICS QUERY FUNCTIONS
# ==============================================================================

def get_most_popular_courses(limit: int = 10) -> List[Dict[str, Any]]:
    """Analytics A: Most popular courses by enrollment count."""
    db = get_db()
    pipeline = list(POPULAR_COURSES_PIPELINE)
    if limit:
        pipeline.append({"$limit": limit})
    try:
        return list(db["enrollments"].aggregate(pipeline))
    except Exception as e:
        print(f"Error in popular courses pipeline: {e}")
        return []


def get_average_rating_per_course() -> List[Dict[str, Any]]:
    """Analytics B: Average review rating and review count per course."""
    db = get_db()
    try:
        return list(db["reviews"].aggregate(COURSE_RATINGS_PIPELINE))
    except Exception as e:
        print(f"Error in course ratings pipeline: {e}")
        return []


def get_category_wise_enrollments() -> List[Dict[str, Any]]:
    """Analytics C: Category-wise enrollment distribution."""
    db = get_db()
    try:
        return list(db["enrollments"].aggregate(CATEGORY_ENROLLMENTS_PIPELINE))
    except Exception as e:
        print(f"Error in category enrollments pipeline: {e}")
        return []


def get_student_learning_progress() -> List[Dict[str, Any]]:
    """Analytics D: Course-level completion rates and average learning progress."""
    db = get_db()
    try:
        return list(db["enrollments"].aggregate(STUDENT_PROGRESS_PIPELINE))
    except Exception as e:
        print(f"Error in student progress pipeline: {e}")
        return []


def get_overall_statistics() -> Dict[str, Any]:
    """
    Analytics E: High-level KPI metrics across all collections.
    Calculates live counts, average review rating, and completion percentage.
    """
    db = get_db()
    try:
        total_students = db["students"].count_documents({})
        total_courses = db["courses"].count_documents({})
        total_enrollments = db["enrollments"].count_documents({})
        total_reviews = db["reviews"].count_documents({})

        # Average rating across all reviews via aggregation
        avg_rating_res = list(db["reviews"].aggregate([
            {"$group": {"_id": None, "global_avg": {"$avg": "$rating"}}}
        ]))
        avg_rating = round(avg_rating_res[0]["global_avg"], 2) if avg_rating_res else 0.0

        # Completion rate across all enrollments
        completed_enrollments = db["enrollments"].count_documents({"status": "Completed"})
        completion_rate = (
            round((completed_enrollments / total_enrollments) * 100, 1)
            if total_enrollments > 0
            else 0.0
        )

        return {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_enrollments": total_enrollments,
            "total_reviews": total_reviews,
            "completed_enrollments": completed_enrollments,
            "avg_review_rating": avg_rating,
            "completion_rate": completion_rate,
        }
    except Exception as e:
        print(f"Error in overall statistics: {e}")
        return {
            "total_students": 0,
            "total_courses": 0,
            "total_enrollments": 0,
            "total_reviews": 0,
            "completed_enrollments": 0,
            "avg_review_rating": 0.0,
            "completion_rate": 0.0,
        }
