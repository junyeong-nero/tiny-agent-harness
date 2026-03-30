from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tiny_agent_harness.schemas.tools import ToolInput


class HarnessInput(BaseModel):
    task: str
    session_id: str


class HarnessOutput(BaseModel):
    task: str
    session_id: str
    summary: str
