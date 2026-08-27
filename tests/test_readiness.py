import unittest
from unittest.mock import Mock, patch

from app.core.readiness import ReadinessChecker


class ReadinessCheckerTests(unittest.TestCase):
    def test_reports_ready_when_database_vector_and_redis_are_healthy(self):
        db = Mock()
        db.execute.side_effect = [
            Mock(),
            ScalarResultStub(True),
        ]

        with patch(
            "app.core.readiness.Redis"
        ) as redis_class:
            redis_client = Mock()
            redis_class.from_url.return_value = redis_client

            report = ReadinessChecker(
                db=db,
                redis_url="redis://localhost:6379/0",
            ).check()

        self.assertTrue(report.ready)
        self.assertEqual(report.status, "ready")
        redis_client.ping.assert_called_once()
        redis_client.close.assert_called_once()

    def test_reports_not_ready_when_pgvector_is_missing(self):
        db = Mock()
        db.execute.side_effect = [
            Mock(),
            ScalarResultStub(False),
        ]

        with patch(
            "app.core.readiness.Redis"
        ) as redis_class:
            redis_client = Mock()
            redis_class.from_url.return_value = redis_client

            report = ReadinessChecker(
                db=db,
                redis_url="redis://localhost:6379/0",
            ).check()

        self.assertFalse(report.ready)
        self.assertEqual(report.status, "not_ready")
        self.assertFalse(report.dependencies[1].healthy)


class ScalarResultStub:
    def __init__(
        self,
        value,
    ) -> None:
        self.value = value

    def scalar_one(self):
        return self.value


if __name__ == "__main__":
    unittest.main()
