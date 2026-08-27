from dataclasses import dataclass

from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    healthy: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    status: str
    dependencies: list[DependencyStatus]

    @property
    def ready(self) -> bool:
        return all(
            dependency.healthy
            for dependency in self.dependencies
        )


class ReadinessChecker:
    def __init__(
        self,
        db: Session,
        redis_url: str,
    ) -> None:
        self.db = db
        self.redis_url = redis_url

    def check(self) -> ReadinessReport:
        dependencies = [
            self._check_database(),
            self._check_pgvector(),
            self._check_redis(),
        ]

        return ReadinessReport(
            status=(
                "ready"
                if all(
                    dependency.healthy
                    for dependency in dependencies
                )
                else "not_ready"
            ),
            dependencies=dependencies,
        )

    def _check_database(self) -> DependencyStatus:
        try:
            self.db.execute(text("SELECT 1"))
        except Exception as error:
            return DependencyStatus(
                name="database",
                healthy=False,
                detail=str(error),
            )

        return DependencyStatus(
            name="database",
            healthy=True,
            detail="ok",
        )

    def _check_pgvector(self) -> DependencyStatus:
        try:
            installed = self.db.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_extension "
                    "WHERE extname = 'vector'"
                    ")"
                )
            ).scalar_one()
        except Exception as error:
            return DependencyStatus(
                name="pgvector",
                healthy=False,
                detail=str(error),
            )

        return DependencyStatus(
            name="pgvector",
            healthy=bool(installed),
            detail=(
                "installed"
                if installed
                else "extension missing"
            ),
        )

    def _check_redis(self) -> DependencyStatus:
        redis_client = Redis.from_url(
            self.redis_url,
            decode_responses=True,
        )

        try:
            redis_client.ping()
        except Exception as error:
            return DependencyStatus(
                name="redis",
                healthy=False,
                detail=str(error),
            )
        finally:
            redis_client.close()

        return DependencyStatus(
            name="redis",
            healthy=True,
            detail="ok",
        )
