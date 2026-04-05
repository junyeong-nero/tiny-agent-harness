from pydantic import BaseModel, ConfigDict, Field


class ReplaceInFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    old_text: str = Field(min_length=1)
    new_text: str
    expected_occurrences: int = Field(default=1, ge=1)
