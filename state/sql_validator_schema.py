from pydantic import BaseModel


class SQLValidatorOutput(BaseModel):

    is_valid: bool

    corrected_sql: str

    issues: list[str]

    reasoning: str