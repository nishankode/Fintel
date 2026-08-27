import unittest

from redis.exceptions import TimeoutError as RedisTimeoutError

from app.ingestion.queue import IngestionQueue


class IngestionQueueTests(unittest.TestCase):
    def test_enqueue_pushes_job_id_to_configured_queue(self):
        redis_client = RedisStub()
        queue = IngestionQueue(
            redis_client=redis_client,
            queue_name="jobs",
        )

        queue.enqueue(123)

        self.assertEqual(
            redis_client.pushed,
            [("jobs", "123")],
        )

    def test_dequeue_returns_none_when_queue_is_empty(self):
        redis_client = RedisStub()
        queue = IngestionQueue(
            redis_client=redis_client,
            queue_name="jobs",
        )

        self.assertIsNone(
            queue.dequeue(timeout_seconds=1)
        )

    def test_dequeue_returns_none_when_redis_times_out(self):
        redis_client = RedisStub(
            raises=RedisTimeoutError("idle timeout"),
        )
        queue = IngestionQueue(
            redis_client=redis_client,
            queue_name="jobs",
        )

        self.assertIsNone(
            queue.dequeue(timeout_seconds=1)
        )

    def test_dequeue_converts_job_id_to_int(self):
        redis_client = RedisStub(
            popped=("jobs", "456"),
        )
        queue = IngestionQueue(
            redis_client=redis_client,
            queue_name="jobs",
        )

        self.assertEqual(
            queue.dequeue(timeout_seconds=1),
            456,
        )


class RedisStub:
    def __init__(
        self,
        popped=None,
        raises=None,
    ) -> None:
        self.popped = popped
        self.raises = raises
        self.pushed = []

    def rpush(
        self,
        queue_name,
        value,
    ):
        self.pushed.append(
            (queue_name, value)
        )

    def blpop(
        self,
        queue_names,
        timeout,
    ):
        if self.raises:
            raise self.raises

        return self.popped


if __name__ == "__main__":
    unittest.main()
