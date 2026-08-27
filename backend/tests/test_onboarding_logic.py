import unittest
from unittest.mock import patch, MagicMock
from fastapi import BackgroundTasks
from starlette.requests import Request
from app.api.endpoints.onboarding import (
    get_calibration_levels,
    start_onboarding,
    submit_onboarding,
    get_calibration_text,
    OnboardingStartRequest,
    OnboardingSubmitRequest,
    RatingItem,
    _CALIBRATION_CACHE
)

def _mock_request():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/onboarding",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope=scope)

class TestOnboardingRollingPipeline(unittest.IsolatedAsyncioTestCase):
    def test_calibration_levels_a1(self):
        self.assertEqual(get_calibration_levels("A1"), ["A1", "A1", "A2"])

    def test_calibration_levels_a2(self):
        self.assertEqual(get_calibration_levels("A2"), ["A1", "A2", "B1"])

    def test_calibration_levels_b1(self):
        self.assertEqual(get_calibration_levels("B1"), ["A2", "B1", "B2"])

    def test_calibration_levels_b2(self):
        self.assertEqual(get_calibration_levels("B2"), ["B1", "B2", "C1"])

    def test_calibration_levels_c1(self):
        self.assertEqual(get_calibration_levels("C1"), ["B2", "C1", "C1"])

    def test_calibration_levels_fallback_on_invalid(self):
        self.assertEqual(get_calibration_levels("UNKNOWN"), ["A1", "A2", "B1"])
        self.assertEqual(get_calibration_levels(""), ["A1", "A2", "B1"])

    @patch("app.api.endpoints.onboarding._generate_single_calibration_text")
    async def test_start_onboarding_returns_only_first_text(self, mock_gen):
        """Proves start_onboarding produces ONLY text 1 (single generation) and returns immediately."""
        mock_gen.return_value = {
            "id": 1,
            "step": 1,
            "level": "A2",
            "content": "First calibration text content",
            "target_word": {"id": 1, "lemma": "lernen"},
            "anchors": [],
            "status": "ready"
        }
        
        req = _mock_request()
        payload = OnboardingStartRequest(
            user_id="user-rolling-1",
            current_level="B1",
            target_level="B2",
            domain="HEALTH"
        )
        
        res = await start_onboarding(req, payload)
        
        # Only 1 text is generated and returned
        self.assertEqual(len(res["calibration_texts"]), 1)
        self.assertEqual(res["calibration_texts"][0]["step"], 1)
        self.assertEqual(res["calibration_texts"][0]["content"], "First calibration text content")
        self.assertEqual(res["current_step"], 1)
        self.assertEqual(res["total_steps"], 3)
        mock_gen.assert_called_once_with(
            user_id="user-rolling-1",
            domain_tag="HEALTH",
            subdomain=None,
            level="A2",
            step=1
        )

    @patch("app.api.endpoints.onboarding._generate_single_calibration_text")
    async def test_submit_rating1_triggers_text2_background_task(self, mock_gen):
        """Proves submitting rating 1 schedules BackgroundTask to generate Text 2."""
        user_id = "user-rolling-2"
        _CALIBRATION_CACHE[user_id] = {
            "session": {"levels": ["A2", "B1", "B2"], "domain": "IT", "current_level": "B1", "target_level": "B2"},
            "texts": {1: {"id": 1, "step": 1, "status": "ready"}}
        }
        
        bg_tasks = MagicMock(spec=BackgroundTasks)
        req = _mock_request()
        payload = OnboardingSubmitRequest(
            user_id=user_id,
            current_level="B1",
            target_level="B2",
            domain="IT",
            ratings=[RatingItem(text_id=1, rating=4, difficulty="Genau richtig")]
        )
        
        res = await submit_onboarding(req, payload, bg_tasks)
        
        # Returns pending status for step 2
        self.assertEqual(res["status"], "pending")
        self.assertFalse(res["ready"])
        self.assertEqual(res["step"], 2)
        
        # Background task scheduled specifically for text 2
        bg_tasks.add_task.assert_called_once()
        args = bg_tasks.add_task.call_args[0]
        # args: (_generate_single_calibration_text, user_id, domain_tag, subdomain, level, step)
        self.assertEqual(args[1], user_id)
        self.assertEqual(args[4], "B1")  # level 2
        self.assertEqual(args[5], 2)     # step 2

    @patch("app.api.endpoints.onboarding._generate_single_calibration_text")
    async def test_submit_rating2_triggers_text3_background_task(self, mock_gen):
        """Proves submitting rating 2 schedules BackgroundTask to generate Text 3."""
        user_id = "user-rolling-3"
        _CALIBRATION_CACHE[user_id] = {
            "session": {"levels": ["A2", "B1", "B2"], "domain": "IT", "current_level": "B1", "target_level": "B2"},
            "texts": {
                1: {"id": 1, "step": 1, "status": "ready"},
                2: {"id": 2, "step": 2, "status": "ready"}
            }
        }
        
        bg_tasks = MagicMock(spec=BackgroundTasks)
        req = _mock_request()
        payload = OnboardingSubmitRequest(
            user_id=user_id,
            current_level="B1",
            target_level="B2",
            domain="IT",
            ratings=[
                RatingItem(text_id=1, rating=4, difficulty="Genau richtig"),
                RatingItem(text_id=2, rating=3, difficulty="Zu schwer")
            ]
        )
        
        res = await submit_onboarding(req, payload, bg_tasks)
        
        # Returns pending status for step 3
        self.assertEqual(res["status"], "pending")
        self.assertFalse(res["ready"])
        self.assertEqual(res["step"], 3)
        
        # Background task scheduled specifically for text 3
        bg_tasks.add_task.assert_called_once()
        args = bg_tasks.add_task.call_args[0]
        self.assertEqual(args[1], user_id)
        self.assertEqual(args[4], "B2")  # level 3
        self.assertEqual(args[5], 3)     # step 3

    async def test_polling_endpoint_returns_status(self):
        """Proves get_calibration_text polling endpoint accurately reports pending vs ready."""
        user_id = "user-polling-test"
        _CALIBRATION_CACHE[user_id] = {
            "texts": {
                2: {"id": 2, "step": 2, "level": "B1", "content": "Text 2 ready", "status": "ready"}
            }
        }
        
        res_ready = await get_calibration_text(user_id=user_id, step=2)
        self.assertTrue(res_ready["ready"])
        self.assertEqual(res_ready["text"]["content"], "Text 2 ready")
        
        res_pending = await get_calibration_text(user_id=user_id, step=3)
        self.assertFalse(res_pending["ready"])
        self.assertEqual(res_pending["message"], "Text wird vorbereitet...")

    @patch("app.api.endpoints.onboarding.supabase_admin")
    async def test_final_submit_completes_registration_without_extra_generations(self, mock_supabase):
        """Proves 3rd rating finalizes profile, initializes word state, and schedules no more background tasks."""
        user_id = "user-final-submit"
        _CALIBRATION_CACHE[user_id] = {
            "session": {"levels": ["A2", "B1", "B2"], "domain": "HEALTH"},
            "texts": {1: {}, 2: {}, 3: {}}
        }
        bg_tasks = MagicMock(spec=BackgroundTasks)
        req = _mock_request()
        payload = OnboardingSubmitRequest(
            user_id=user_id,
            current_level="B1",
            target_level="B2",
            domain="HEALTH",
            full_name="Dr. Max",
            email="max@krankenhaus.de",
            ratings=[
                RatingItem(text_id=1, rating=4, difficulty="Zu einfach"),
                RatingItem(text_id=2, rating=5, difficulty="Zu einfach"),
                RatingItem(text_id=3, rating=4, difficulty="Genau richtig")
            ]
        )
        
        res = await submit_onboarding(req, payload, bg_tasks)
        
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["step"], "done")
        self.assertEqual(res["calibrated_mastery"], 0.75)
        # No background tasks scheduled on final submit
        bg_tasks.add_task.assert_not_called()
        # Session cache cleaned up
        self.assertNotIn(user_id, _CALIBRATION_CACHE)


if __name__ == '__main__':
    unittest.main()
