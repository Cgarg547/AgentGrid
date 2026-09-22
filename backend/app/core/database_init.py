from app.core.database import engine
from app.models.database import Base
from app.models.execution_checkpoint import ExecutionCheckpoint
from app.models.execution_event import ExecutionEvent
from app.models.workflow_schedule import WorkflowSchedule
from app.models.api_key import APIKey

def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()