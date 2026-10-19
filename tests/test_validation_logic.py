"""
tests/test_validation_logic.py
------------------------------
Unit and integration tests for data validation logic.
Tests boundary conditions for ratings, durations, levels, and statuses.
When MongoDB is active, validates JSON Schema rejection.
"""

import pytest
from database import check_connection, get_db
from operations import (
    VALID_LEVELS,
    VALID_CATEGORIES,
    VALID_STATUSES,
    create_student,
    create_course
)
from validation_demo import (
    run_student_validation_demo,
    run_course_validation_demo,
    run_enrollment_validation_demo
)


class TestValidationLogicBounds:
    """Validate client and business rule boundary checks."""

    def test_allowed_levels(self):
        assert set(VALID_LEVELS) == {"Beginner", "Intermediate", "Advanced"}

    def test_allowed_categories(self):
        assert "Data Science" in VALID_CATEGORIES
        assert "Artificial Intelligence" in VALID_CATEGORIES
        assert "Web Development" in VALID_CATEGORIES
        assert "Database Systems" in VALID_CATEGORIES
        assert "Cloud Computing" in VALID_CATEGORIES
        assert "Cybersecurity" in VALID_CATEGORIES

    def test_allowed_statuses(self):
        assert set(VALID_STATUSES) == {"Not Started", "In Progress", "Completed"}

    def test_client_level_rejection(self):
        success, msg, _ = create_student(
            name="John Doe",
            email="john@example.com",
            skills=["Python"],
            interests=["AI"],
            level="Master"  # Invalid
        )
        assert success is False
        assert "Level must be one of" in msg

    def test_client_email_rejection(self):
        success, msg, _ = create_student(
            name="John Doe",
            email="invalid_email_no_at",
            skills=["Python"],
            interests=["AI"],
            level="Beginner"
        )
        assert success is False
        assert "valid email" in msg.lower()

    def test_client_course_negative_duration(self):
        success, msg, _ = create_course(
            title="Broken Course",
            category="Data Science",
            skills=["Python"],
            level="Beginner",
            duration_hours=-5.0,  # Invalid
            rating=4.5,
            description="Testing negative duration"
        )
        assert success is False
        assert "Duration must be at least" in msg


class TestMongoDBJsonSchemaIntegration:
    """Tests MongoDB JSON Schema server-side rejection when MongoDB is reachable."""

    @pytest.fixture(autouse=True)
    def check_db(self):
        is_conn, _, _ = check_connection()
        if not is_conn:
            pytest.skip("MongoDB server is not reachable; skipping schema integration tests.")

    def test_student_server_validation(self):
        demo = run_student_validation_demo()
        assert demo["valid_test"]["success"] is True
        assert demo["invalid_test"]["caught_expected_error"] is True

    def test_course_server_validation(self):
        demo = run_course_validation_demo()
        assert demo["valid_test"]["success"] is True
        assert demo["invalid_test"]["caught_expected_error"] is True

    def test_enrollment_server_validation(self):
        demo = run_enrollment_validation_demo()
        assert demo["valid_test"]["success"] is True
        assert demo["invalid_test"]["caught_expected_error"] is True
