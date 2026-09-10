# tests/test_main_unittest.py
import unittest

from fastapi.testclient import TestClient

from app.main import app  # adjust import according to your project structure


class TestRootEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_status(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_root_response(self):
        response = self.client.get("/")
        self.assertEqual(response.json(), {"status": "ok", "message": "H.O.M.E. server running"})


if __name__ == "__main__":
    unittest.main()
