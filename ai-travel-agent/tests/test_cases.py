"""
tests/test_cases.py — AI Travel Agent
=======================================

Unit tests covering the edge cases from docs/testing_cases.md.

Run with:
    python -m pytest tests/test_cases.py -v
"""

import os
import sys
import pytest

# ---------------------------------------------------------------------------
# Setup path so imports work regardless of cwd
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from backend.agents.input_agent import parse_inputs


# ═══════════════════════════════════════════════════════════════════════════
# InputAgent — Guardrail Tests (testing_cases.md §Guardrail Tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestInputAgentGuardrails:
    """Verify InputAgent rejects bad input before any LLM call."""

    def test_duration_zero_rejected(self):
        """Duration: 0 days → error returned, no LLM call made."""
        with pytest.raises(ValueError, match="duration"):
            parse_inputs({
                "origin_city": "Mumbai",
                "budget": "medium",
                "duration": 0,
                "travel_style": "cultural",
                "weather_preference": "warm",
            })

    def test_empty_city_rejected(self):
        """City of origin: empty → error returned immediately."""
        with pytest.raises(ValueError, match="origin_city"):
            parse_inputs({
                "origin_city": "",
                "budget": "medium",
                "duration": 5,
                "travel_style": "cultural",
                "weather_preference": "warm",
            })

    def test_whitespace_only_city_rejected(self):
        """City of origin: whitespace only → error returned."""
        with pytest.raises(ValueError, match="origin_city"):
            parse_inputs({
                "origin_city": "   ",
                "budget": "medium",
                "duration": 5,
                "travel_style": "cultural",
                "weather_preference": "warm",
            })

    def test_negative_budget_normalised_to_low(self):
        """Budget: negative/unknown → normalised to 'low'."""
        result = parse_inputs({
            "origin_city": "Mumbai",
            "budget": "negative",
            "duration": 5,
            "travel_style": "cultural",
            "weather_preference": "warm",
        })
        assert result["budget"] == "low"

    def test_invalid_budget_normalised_to_low(self):
        """Budget: invalid string → normalised to 'low'."""
        result = parse_inputs({
            "origin_city": "Mumbai",
            "budget": "super-expensive",
            "duration": 3,
            "travel_style": "adventure",
            "weather_preference": "cold",
        })
        assert result["budget"] == "low"


# ═══════════════════════════════════════════════════════════════════════════
# InputAgent — Normalisation (testing_cases.md §Agent Unit Tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestInputAgentNormalisation:
    """Test normalisation of budget/style/weather variants."""

    def test_happy_path(self):
        """Happy path: valid input returns all fields correctly."""
        result = parse_inputs({
            "origin_city": "Mumbai",
            "budget": "medium",
            "duration": 5,
            "travel_style": "cultural",
            "weather_preference": "warm",
        })
        assert result["origin_city"] == "Mumbai"
        assert result["budget"] == "medium"
        assert result["duration"] == 5
        assert result["travel_style"] == "cultural"
        assert result["weather_preference"] == "warm"

    def test_budget_case_insensitive(self):
        """Budget values should be case-insensitive."""
        result = parse_inputs({
            "origin_city": "Delhi",
            "budget": "HIGH",
            "duration": 3,
            "travel_style": "adventure",
            "weather_preference": "cold",
        })
        assert result["budget"] == "high"

    def test_travel_style_defaults_to_balanced(self):
        """Travel style not provided → defaults to 'balanced'."""
        result = parse_inputs({
            "origin_city": "Mumbai",
            "budget": "low",
            "duration": 1,
            "travel_style": "",
            "weather_preference": "any",
        })
        assert result["travel_style"] == "balanced"

    def test_duration_1_day_accepted(self):
        """Duration: 1 day → should be accepted."""
        result = parse_inputs({
            "origin_city": "Mumbai",
            "budget": "low",
            "duration": 1,
            "travel_style": "balanced",
            "weather_preference": "any",
        })
        assert result["duration"] == 1

    def test_duration_30_days_accepted(self):
        """Duration: 30 days → maximum, should be accepted."""
        result = parse_inputs({
            "origin_city": "Mumbai",
            "budget": "high",
            "duration": 30,
            "travel_style": "relaxation",
            "weather_preference": "tropical",
        })
        assert result["duration"] == 30

    def test_duration_31_rejected(self):
        """Duration: 31 days → exceeds max, should be rejected."""
        with pytest.raises(ValueError, match="duration"):
            parse_inputs({
                "origin_city": "Mumbai",
                "budget": "medium",
                "duration": 31,
                "travel_style": "cultural",
                "weather_preference": "warm",
            })

    def test_origin_city_whitespace_stripped(self):
        """Origin city whitespace should be stripped."""
        result = parse_inputs({
            "origin_city": "  New Delhi  ",
            "budget": "medium",
            "duration": 5,
            "travel_style": "cultural",
            "weather_preference": "warm",
        })
        assert result["origin_city"] == "New Delhi"

    def test_all_valid_budgets(self):
        """All valid budget values should be accepted."""
        for budget in ("low", "medium", "high"):
            result = parse_inputs({
                "origin_city": "Delhi",
                "budget": budget,
                "duration": 5,
                "travel_style": "balanced",
                "weather_preference": "any",
            })
            assert result["budget"] == budget

    def test_all_valid_travel_styles(self):
        """All valid travel style values should be accepted."""
        for style in ("adventure", "cultural", "relaxation", "balanced"):
            result = parse_inputs({
                "origin_city": "Delhi",
                "budget": "medium",
                "duration": 5,
                "travel_style": style,
                "weather_preference": "any",
            })
            assert result["travel_style"] == style

    def test_all_valid_weather_prefs(self):
        """All valid weather preference values should be accepted."""
        for pref in ("cold", "warm", "tropical", "any"):
            result = parse_inputs({
                "origin_city": "Delhi",
                "budget": "medium",
                "duration": 5,
                "travel_style": "balanced",
                "weather_preference": pref,
            })
            assert result["weather_preference"] == pref


# ═══════════════════════════════════════════════════════════════════════════
# WeatherTool — Graceful Degradation
# ═══════════════════════════════════════════════════════════════════════════

class TestWeatherToolFallback:
    """Weather API failure → fallback with score=5, no crash."""

    def test_missing_api_key_returns_fallback(self):
        """No WEATHER_API_KEY → returns fallback dict, no exception."""
        from unittest.mock import patch, MagicMock
        import backend.tools.weather_tool as wt

        # Mock os.environ.get to return "" for WEATHER_API_KEY
        original_get = os.environ.get
        def mock_get(key, default=""):
            if key == "WEATHER_API_KEY":
                return ""
            return original_get(key, default)

        with patch.object(os.environ, 'get', side_effect=mock_get):
            # Also ensure the config import fails so it doesn't load the key
            with patch.dict('sys.modules', {'backend.config': MagicMock(WEATHER_API_KEY="")}):
                result = wt.get_weather_score("Paris", "warm")
                assert result["weather_score"] == 5
                assert result["destination"] == "Paris"
                assert "error" in result

    def test_fallback_has_correct_shape(self):
        """Fallback dict has all required keys."""
        from backend.tools.weather_tool import _fallback
        result = _fallback("Tokyo", "test reason")
        assert "destination" in result
        assert "temp_celsius" in result
        assert "condition" in result
        assert "weather_score" in result
        assert result["destination"] == "Tokyo"
        assert result["weather_score"] == 5


# ═══════════════════════════════════════════════════════════════════════════
# Prompt Modules — Smoke tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPromptModules:
    """Verify prompt modules produce non-empty, well-formed prompts."""

    def test_recommendation_prompt_builds(self):
        from backend.prompts.recommendation_prompt import build_user_prompt
        prompt = build_user_prompt(
            {"origin_city": "Mumbai", "budget": "medium", "duration": 5,
             "travel_style": "cultural", "weather_preference": "warm"},
            {},
        )
        assert "Mumbai" in prompt
        assert "EXACTLY 5" in prompt
        assert "JSON" in prompt

    def test_itinerary_prompt_builds(self):
        from backend.prompts.itinerary_prompt import build_user_prompt
        prompt = build_user_prompt(
            "Bali",
            {"country": "Indonesia", "budget": "medium", "duration": 3,
             "travel_style": "relaxation"},
        )
        assert "Bali" in prompt
        assert "Indonesia" in prompt
        assert "Day 1" in prompt
        assert "Day 3" in prompt

    def test_itinerary_retry_prompt_is_stricter(self):
        from backend.prompts.itinerary_prompt import build_user_prompt, build_retry_prompt
        base = build_user_prompt(
            "Bali",
            {"country": "Indonesia", "budget": "medium", "duration": 2,
             "travel_style": "cultural"},
        )
        retry = build_retry_prompt(
            "Bali",
            {"country": "Indonesia", "budget": "medium", "duration": 2,
             "travel_style": "cultural"},
        )
        assert "CRITICAL" in retry
        assert len(retry) > len(base)


# ═══════════════════════════════════════════════════════════════════════════
# Recommendation Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestRecommendationValidation:
    """Verify _validate_recommendations catches schema issues."""

    def test_empty_list_rejected(self):
        from backend.agents.recommendation_agent import _validate_recommendations
        with pytest.raises(ValueError):
            _validate_recommendations([])

    def test_fewer_than_5_rejected(self):
        from backend.agents.recommendation_agent import _validate_recommendations
        recs = [
            {"rank": i, "destination": f"City{i}", "country": "C",
             "reason": "A good reason with enough words here", "weather_score": 5, "budget_fit": "low"}
            for i in range(1, 4)
        ]
        with pytest.raises(ValueError, match="Expected exactly 5"):
            _validate_recommendations(recs)

    def test_more_than_5_truncated(self):
        from backend.agents.recommendation_agent import _validate_recommendations
        recs = [
            {"rank": i, "destination": f"City{i}", "country": "C",
             "reason": "A good reason with enough words here", "weather_score": 5, "budget_fit": "low"}
            for i in range(1, 8)
        ]
        result = _validate_recommendations(recs)
        assert len(result) == 5

    def test_missing_keys_rejected(self):
        from backend.agents.recommendation_agent import _validate_recommendations
        recs = [
            {"rank": i, "destination": f"City{i}"}  # missing country, reason, etc.
            for i in range(1, 6)
        ]
        with pytest.raises(ValueError, match="missing keys"):
            _validate_recommendations(recs)

    def test_weather_score_clamped(self):
        from backend.agents.recommendation_agent import _validate_recommendations
        recs = [
            {"rank": i, "destination": f"City{i}", "country": "C",
             "reason": "A good reason with enough words here",
             "weather_score": 15 if i == 1 else -3 if i == 2 else 7,
             "budget_fit": "medium"}
            for i in range(1, 6)
        ]
        result = _validate_recommendations(recs)
        assert result[0]["weather_score"] == 10  # clamped from 15
        assert result[1]["weather_score"] == 0   # clamped from -3
        assert result[2]["weather_score"] == 7   # unchanged
