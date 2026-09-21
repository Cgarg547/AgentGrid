import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)


def test_execution_checkpoint_repository_round_trip():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    execution_id = str(uuid.uuid4())

    with SessionLocal() as session:
        repository = ExecutionCheckpointRepository(
            session
        )

        checkpoint = repository.save(
            execution_id=execution_id,
            step_name="research",
            status="completed",
            state={
                "research": {
                    "findings": [
                        "finding-1",
                        "finding-2",
                    ]
                }
            },
        )

        assert checkpoint.id is not None
        assert checkpoint.execution_id == execution_id
        assert checkpoint.step_name == "research"
        assert checkpoint.status == "completed"

        checkpoints = repository.list_by_execution(
            execution_id
        )

        assert len(checkpoints) == 1

        latest = repository.get_latest(
            execution_id
        )

        assert latest is not None
        assert latest.id == checkpoint.id

        state = repository.deserialize_state(
            latest.state
        )

        assert state == {
            "research": {
                "findings": [
                    "finding-1",
                    "finding-2",
                ]
            }
        }