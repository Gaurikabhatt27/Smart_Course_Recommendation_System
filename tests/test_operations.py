"""
tests/test_operations.py
------------------------
Integration tests for CRUD operations, referential integrity checks,
duplicate enrollment prevention, and progress consistency.
Executes against an isolated test database ('course_recommendation_test')
which is automatically created and dropped by pytest fixtures.
"""

import pytest
import os
from bson import ObjectId
from database import get_client, check_connection
from setup_db import apply_validators, create_indexes
import operations

TEST_DB_NAME = "course_recommendation_test"


@pytest.fixture(scope="module")
def setup_test_db():
    """Setup and teardown isolated test database."""
    is_conn, msg, _ = check_connection()
    if not is_conn:
        pytest.skip(f"MongoDB server is not reachable: {msg}")

    # Set environment to use test database
    orig_db = os.environ.get("MONGODB_DB_NAME")
    os.environ["MONGODB_DB_NAME"] = TEST_DB_NAME

    client = get_client()
    test_db = client[TEST_DB_NAME]
    # Drop in case of previous failed runs
    client.drop_database(TEST_DB_NAME)

    # Initialize validators and indexes
    apply_validators(test_db)
    create_indexes(test_db)

    yield test_db

    # Clean up test database
    client.drop_database(TEST_DB_NAME)
    if orig_db:
        os.environ["MONGODB_DB_NAME"] = orig_db


def test_student_crud(setup_test_db):
    """Test student creation, retrieval, update, and safe deletion."""
    # 1. Create
    ok, msg, student_id = operations.create_student(
        name="Test Student",
        email="test.student@example.com",
        skills=["Python", "SQL"],
        interests=["Data Science"],
        level="Intermediate"
    )
    assert ok is True
    assert student_id is not None

    # 2. Duplicate email check
    dup_ok, dup_msg, _ = operations.create_student(
        name="Duplicate Student",
        email="test.student@example.com",
        skills=["C++"],
        interests=["AI"],
        level="Beginner"
    )
    assert dup_ok is False
    assert "already exists" in dup_msg.lower()

    # 3. Retrieve
    student = operations.get_student_by_id(student_id)
    assert student is not None
    assert student["name"] == "Test Student"

    # 4. Update
    up_ok, up_msg = operations.update_student(
        student_id,
        name="Updated Student Name",
        level="Advanced"
    )
    assert up_ok is True
    updated = operations.get_student_by_id(student_id)
    assert updated["name"] == "Updated Student Name"
    assert updated["level"] == "Advanced"

    # 5. Delete
    del_ok, del_msg = operations.delete_student(student_id, cascade=True)
    assert del_ok is True
    assert operations.get_student_by_id(student_id) is None


def test_course_crud(setup_test_db):
    """Test course creation, retrieval, and updating."""
    ok, msg, course_id = operations.create_course(
        title="Test Advanced PyMongo Course",
        category="Database Systems",
        skills=["MongoDB", "PyMongo"],
        level="Intermediate",
        duration_hours=20.0,
        rating=4.8,
        description="A rigorous test course."
    )
    assert ok is True
    assert course_id is not None

    course = operations.get_course_by_id(course_id)
    assert course is not None
    assert course["category"] == "Database Systems"

    up_ok, _ = operations.update_course(course_id, rating=4.9)
    assert up_ok is True
    assert operations.get_course_by_id(course_id)["rating"] == 4.9


def test_enrollment_referential_integrity_and_duplicates(setup_test_db):
    """Test referential integrity and duplicate enrollment prevention."""
    # Create valid student and course
    _, _, s_id = operations.create_student(
        name="Enrollment Tester",
        email="enroller@example.com",
        skills=["Python"],
        interests=["Database Systems"],
        level="Beginner"
    )
    _, _, c_id = operations.create_course(
        title="Test Enrollment Catalog Course",
        category="Database Systems",
        skills=["MongoDB"],
        level="Beginner",
        duration_hours=15.0,
        rating=4.5,
        description="Enrollment validation test."
    )

    # 1. Invalid student ID referential check
    fake_id = str(ObjectId())
    bad_s_ok, bad_s_msg, _ = operations.enroll_student(fake_id, c_id)
    assert bad_s_ok is False
    assert "Student does not exist" in bad_s_msg

    # 2. Invalid course ID referential check
    bad_c_ok, bad_c_msg, _ = operations.enroll_student(s_id, fake_id)
    assert bad_c_ok is False
    assert "Course does not exist" in bad_c_msg

    # 3. Valid enrollment
    enr_ok, _, enr_id = operations.enroll_student(s_id, c_id, progress=50.0)
    assert enr_ok is True
    assert enr_id is not None

    # 4. Duplicate enrollment rejection
    dup_enr_ok, dup_enr_msg, _ = operations.enroll_student(s_id, c_id)
    assert dup_enr_ok is False
    assert "already enrolled" in dup_enr_msg.lower() or "duplicate" in dup_enr_msg.lower()

    # 5. Progress update and status consistency
    prog_ok, _ = operations.update_enrollment_progress(enr_id, 100.0)
    assert prog_ok is True

    # Verify status transitioned to Completed
    enrs = operations.get_student_enrollments(s_id)
    assert len(enrs) == 1
    assert enrs[0]["status"] == "Completed"
    assert enrs[0]["progress"] == 100.0


def test_reviews_crud(setup_test_db):
    """Test review creation with foreign key checks and rating validation."""
    _, _, s_id = operations.create_student(
        name="Reviewer Student",
        email="reviewer@example.com",
        skills=["Python"],
        interests=["Data Science"],
        level="Intermediate"
    )
    _, _, c_id = operations.create_course(
        title="Test Review Course",
        category="Data Science",
        skills=["Python", "Pandas"],
        level="Intermediate",
        duration_hours=25.0,
        rating=4.7,
        description="Review test course."
    )

    # Invalid rating (> 5)
    bad_r_ok, bad_r_msg, _ = operations.add_review(s_id, c_id, rating=6, comment="Superb")
    assert bad_r_ok is False

    # Valid review
    r_ok, _, r_id = operations.add_review(s_id, c_id, rating=5, comment="Excellent materials and clear labs.")
    assert r_ok is True
    assert r_id is not None

    reviews = operations.get_course_reviews(c_id)
    assert len(reviews) == 1
    assert reviews[0]["rating"] == 5

    del_ok, _ = operations.delete_review(r_id)
    assert del_ok is True
    assert len(operations.get_course_reviews(c_id)) == 0
