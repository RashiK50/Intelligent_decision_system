from pydantic import BaseModel


class GuardrailOutput(BaseModel):

    is_allowed: bool

    reason: str