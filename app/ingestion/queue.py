from redis import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError


class IngestionQueue:
    def __init__(
        self,
        redis_client: Redis,
        queue_name: str,
    ) -> None:
        self.redis_client = redis_client
        self.queue_name = queue_name

    def enqueue(
        self,
        job_id: int,
    ) -> None:
        self.redis_client.rpush(
            self.queue_name,
            str(job_id),
        )

    def dequeue(
        self,
        timeout_seconds: int = 5,
    ) -> int | None:
        try:
            item = self.redis_client.blpop(
                [self.queue_name],
                timeout=timeout_seconds,
            )
        except RedisTimeoutError:
            return None

        if item is None:
            return None

        _, raw_job_id = item

        return int(raw_job_id)
