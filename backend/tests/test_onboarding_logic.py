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

class TestOnboardingLogic(unittest.IsolatedAsyncioTestCase):
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
    async def test_start_onboarding_returns_only_first_text_and_schedules_second(self, mock_gen):
        mock_gen.return_value = {
            "id": 1,
            "step": 1,
            "level": "A2",
            "content": "Text 1 content",
            "target_word": {"id": 1, "lemma": "lernen"},
            "anchors": [],
            "status": "ready"
        }
        
        bg_tasks = MagicMock(spec=BackgroundTasks)
        req = _mock_request()
        payload = OnboardingStartRequest(
            user_id="test-user-123",
            current_level="B1",
            target_level="B2",
            domain="HEALTH"
        )
        
        res = await start_onboarding(req, payload, bg_tasks)
        
        # Only 1 text returned in calibration_texts
        self.assertEqual(len(res["calibration_texts"]), 1)
        self.assertEqual(res["calibration_texts"][0]["step"], 1)
        self.assertEqual(res["current_step"], 1)
        self.assertEqual(res["total_steps"], 3)
        
        # Background task scheduled for text 2
        bg_tasks.add_task.assert_called_once()

    @patch("app.api.endpoints.onboarding._generate_single_calibration_text")
    async def test_intermediate_submit_returns_pregenerated_text(self, mock_gen):
        user_id = "test-user-456"
        _CALIBRATION_CACHE[user_id] = {
            "session": {"levels": ["A2", "B1", "B2"], "domain": "IT"},
            "texts": {
                2: {"id": 2, "step": 2, "level": "B1", "content": "Text 2", "status": "ready"}
            }
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
        self.assertEqual(res["status"], "next")
        self.assertTrue(res["ready"])
        self.assertEqual(res["step"], 2)
        self.assertEqual(res["text"]["content"], "Text 2")
        
        # Background task scheduled for text 3
        bg_tasks.add_task.assert_called_once()

    async def test_polling_endpoint_returns_status(self):
        user_id = "test-user-789"
        _CALIBRATION_CACHE[user_id] = {
            "texts": {
                2: {"id": 2, "step": 2, "level": "B1", "content": "Text 2 ready", "status": "ready"}
            }
        }
        
        res = await get_calibration_text(user_id=user_id, step=2)
        self.assertTrue(res["ready"])
        self.assertEqual(res["text"]["content"], "Text 2 ready")
        
        res_pending = await get_calibration_text(user_id=user_id, step=3)
        self.assertFalse(res_pending["ready"])
        self.assertEqual(res_pending["message"], "Text wird vorbereitet...")

    @patch("app.api.endpoints.onboarding.supabase_admin")
    async def test_final_submit_completes_registration(self, mock_supabase):
        user_id = "test-user-final"
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


if __name__ == '__main__':
    unittest.main()
