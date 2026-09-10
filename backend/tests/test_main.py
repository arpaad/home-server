"""The application starts and answers its liveness probe."""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_status(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)

    def test_health_response(self):
        response = self.client.get("/health")

        self.assertEqual(
            response.json(),
            {"status": "ok", "message": "H.O.M.E. server running"},
        )

    def test_the_replaced_prototype_route_is_gone(self):
        # The prototype exposed /shopping-items with no stores and no timing.
        self.assertEqual(self.client.get("/shopping-items").status_code, 404)


if __name__ == "__main__":
    unittest.main()
