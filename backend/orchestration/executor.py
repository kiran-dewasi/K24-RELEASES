"""
Task Executor for KITTU Workflows
Provides basic task execution and orchestration using Prefect
"""
from prefect import flow, task
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@task(name="hello_world_task")
def hello_world() -> str:
    """Simple test task"""
    logger.info("Hello from KITTU orchestration!")
    return "Task executed successfully"


@flow(name="test_workflow")
def test_workflow() -> Dict[str, Any]:
    """
    Simple test workflow to verify Prefect is working
    """
    result = hello_world()
    return {
        "status": "success",
        "message": result,
        "workflow": "test_workflow"
    }


if __name__ == "__main__":
    # Test the workflow
    result = test_workflow()
    print(f"Workflow result: {result}")
