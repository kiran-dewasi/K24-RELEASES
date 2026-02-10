from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger("workflow")

class WorkflowResult(BaseModel):
    status: str  # 'success', 'failed', 'pending_approval', 'skipped'
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class BaseWorkflow(ABC):
    """
    Abstract base class for all KITTU workflows.
    Enforces a standard execute method and error handling.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def execute(self, **kwargs) -> WorkflowResult:
        """
        Main execution logic for the workflow.
        Must be implemented by subclasses.
        """
        pass

    def run(self, **kwargs) -> WorkflowResult:
        """
        Wrapper around execute to handle logging and common errors.
        """
        logger.info(f"Starting workflow: {self.name} with params: {kwargs}")
        try:
            result = self.execute(**kwargs)
            logger.info(f"Workflow {self.name} completed with status: {result.status}")
            return result
        except Exception as e:
            logger.exception(f"Workflow {self.name} failed unexpectedly")
            return WorkflowResult(
                status="failed",
                message=f"An unexpected error occurred: {str(e)}",
                error=str(e)
            )
