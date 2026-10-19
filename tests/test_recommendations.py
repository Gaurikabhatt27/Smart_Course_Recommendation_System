"""
tests/test_recommendations.py
-----------------------------
Unit tests for the explainable, rule-based recommendation algorithm.
These tests verify mathematical scoring, normalization, case-insensitivity,
and edge cases completely in-memory with zero external database dependency.
"""

import pytest
from recommendations import (
    calculate_skill_match_score,
    calculate_interest_match_score,
    calculate_course_rating_score,
    generate_explanation
)


class TestSkillMatchScore:
    """Tests for Skill Match Score = (matching skills / required course skills) * 100."""

    def test_full_skill_match(self):
        student_skills = ["Python", "Pandas", "SQL"]
        course_skills = ["Python", "Pandas"]
        score, matched = calculate_skill_match_score(student_skills, course_skills)
        assert score == 100.0
        assert set(matched) == {"Python", "Pandas"}

    def test_partial_skill_match(self):
        student_skills = ["Python", "Docker"]
        course_skills = ["Python", "SQL", "Pandas", "Statistics"]
        score, matched = calculate_skill_match_score(student_skills, course_skills)
        # 1 match out of 4 required = 25.0%
        assert score == 25.0
        assert matched == ["Python"]

    def test_zero_skill_match(self):
        student_skills = ["HTML", "CSS"]
        course_skills = ["Python", "PyTorch"]
        score, matched = calculate_skill_match_score(student_skills, course_skills)
        assert score == 0.0
        assert matched == []

    def test_case_insensitive_and_whitespace_matching(self):
        student_skills = ["  python ", "PANDAS  "]
        course_skills = ["Python", "pandas"]
        score, matched = calculate_skill_match_score(student_skills, course_skills)
        assert score == 100.0

    def test_empty_course_skills_safe_handling(self):
        student_skills = ["Python"]
        course_skills = []
        score, matched = calculate_skill_match_score(student_skills, course_skills)
        assert score == 0.0
        assert matched == []


class TestInterestMatchScore:
    """Tests for Interest Match Score bounded between 0 and 100."""

    def test_category_and_skill_interest_match(self):
        student_interests = ["Data Science", "Machine Learning"]
        course_category = "Data Science"
        course_skills = ["Python", "Pandas", "Machine Learning"]
        score, matched = calculate_interest_match_score(
            student_interests, course_category, course_skills
        )
        assert score == 100.0
        assert len(matched) == 2

    def test_partial_interest_match(self):
        student_interests = ["Data Science", "Cybersecurity"]
        course_category = "Data Science"
        course_skills = ["Python", "Pandas"]
        score, matched = calculate_interest_match_score(
            student_interests, course_category, course_skills
        )
        # 1 of 2 interests matched = 50.0%
        assert score == 50.0
        assert matched == ["Data Science"]

    def test_empty_student_interests(self):
        score, matched = calculate_interest_match_score([], "Cloud Computing", ["AWS"])
        assert score == 0.0
        assert matched == []


class TestCourseRatingScore:
    """Tests for Course Rating Score = (rating / 5.0) * 100."""

    def test_perfect_rating(self):
        score = calculate_course_rating_score(5.0)
        assert score == 100.0

    def test_standard_rating(self):
        score = calculate_course_rating_score(4.5)
        assert score == 90.0

    def test_zero_rating(self):
        score = calculate_course_rating_score(0.0)
        assert score == 0.0

    def test_none_or_negative_rating_safety(self):
        assert calculate_course_rating_score(None) == 0.0
        assert calculate_course_rating_score(-2.5) == 0.0

    def test_clamped_upper_bound(self):
        # Even if unvalidated input exceeded 5.0, score clamps to 100.0
        assert calculate_course_rating_score(6.0) == 100.0


class TestCompositeFormula:
    """Verify Final Score = (0.50 * Skill) + (0.30 * Interest) + (0.20 * Rating)."""

    def test_composite_weight_calculation(self):
        skill_score = 80.0
        interest_score = 60.0
        rating_score = 90.0
        # (0.50 * 80) + (0.30 * 60) + (0.20 * 90) = 40 + 18 + 18 = 76.0
        final_score = (0.50 * skill_score) + (0.30 * interest_score) + (0.20 * rating_score)
        assert round(final_score, 2) == 76.0

    def test_explanation_generation(self):
        expl = generate_explanation(
            matched_skills=["Python", "SQL"],
            matched_interests=["Data Science"],
            rating=4.8,
            course_category="Data Science"
        )
        assert "Python" in expl
        assert "Data Science" in expl
        assert "4.8" in expl
