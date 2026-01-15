"""Tests for scoring skill matching utilities."""


class TestNormalizeSkill:
    """Test normalize_skill."""

    def test_normalize_skill_lowercases(self):
        """normalize_skill should lowercase skill names."""
        from src.scoring.matchers import normalize_skill

        assert normalize_skill("Python") == "python"

    def test_normalize_skill_strips_whitespace(self):
        """normalize_skill should strip surrounding whitespace."""
        from src.scoring.matchers import normalize_skill

        assert normalize_skill("  Python  ") == "python"

    def test_normalize_skill_handles_special_characters(self):
        """normalize_skill should preserve common special characters."""
        from src.scoring.matchers import normalize_skill

        assert normalize_skill("C++") == "c++"
        assert normalize_skill("Node.js") == "node.js"


class TestSkillsMatchExact:
    """Test skills_match in exact mode."""

    def test_skills_match_exact_is_case_insensitive(self):
        """Exact match should be case-insensitive."""
        from src.scoring.matchers import skills_match

        assert skills_match("Python", "python", fuzzy=False) is True

    def test_skills_match_exact_common_variations(self):
        """Exact match should handle common variations."""
        from src.scoring.matchers import skills_match

        assert skills_match("JavaScript", "JS", fuzzy=False) is True
        assert skills_match("Python", "Python3", fuzzy=False) is True

    def test_skills_match_exact_no_match_returns_false(self):
        """Exact match should return False when skills don't match."""
        from src.scoring.matchers import skills_match

        assert skills_match("python", "java", fuzzy=False) is False


class TestSkillsMatchFuzzy:
    """Test skills_match in fuzzy mode."""

    def test_skills_match_fuzzy_matches_similar_skills_above_threshold(self):
        """Fuzzy matching should match similar strings above the threshold."""
        from src.scoring.matchers import skills_match

        assert (
            skills_match("postgres", "postgresql", fuzzy=True, threshold=0.85) is True
        )

    def test_skills_match_fuzzy_does_not_match_dissimilar_skills(self):
        """Fuzzy matching should not match dissimilar strings."""
        from src.scoring.matchers import skills_match

        assert skills_match("python", "java", fuzzy=True, threshold=0.85) is False

    def test_skills_match_fuzzy_threshold_configuration(self):
        """Fuzzy matching should respect the configured threshold."""
        from src.scoring.matchers import skills_match

        assert (
            skills_match("postgres", "postgresql", fuzzy=True, threshold=0.95) is False
        )


class TestFindMatchingSkills:
    """Test find_matching_skills."""

    def test_find_matching_skills_returns_matched_and_missing(self):
        """Should return matched and missing required skills."""
        from src.scoring.matchers import find_matching_skills

        matched, missing = find_matching_skills(
            required=["python", "sql"], available=["Python", "aws"], fuzzy=False
        )

        assert matched == ["python"]
        assert missing == ["sql"]

    def test_find_matching_skills_with_multiple_skills(self):
        """Should handle multiple skills."""
        from src.scoring.matchers import find_matching_skills

        matched, missing = find_matching_skills(
            required=["python", "sql", "docker"],
            available=["python", "sql"],
            fuzzy=False,
        )

        assert matched == ["python", "sql"]
        assert missing == ["docker"]

    def test_find_matching_skills_empty_lists(self):
        """Should handle empty required and available lists."""
        from src.scoring.matchers import find_matching_skills

        matched, missing = find_matching_skills(required=[], available=[], fuzzy=False)

        assert matched == []
        assert missing == []

    def test_find_matching_skills_respects_fuzzy_toggle(self):
        """Should respect fuzzy matching enabled/disabled."""
        from src.scoring.matchers import find_matching_skills

        matched_fuzzy, missing_fuzzy = find_matching_skills(
            required=["postgresql"], available=["postgres"], fuzzy=True
        )
        matched_exact, missing_exact = find_matching_skills(
            required=["postgresql"], available=["postgres"], fuzzy=False
        )

        assert matched_fuzzy == ["postgresql"]
        assert missing_fuzzy == []

        assert matched_exact == []
        assert missing_exact == ["postgresql"]
