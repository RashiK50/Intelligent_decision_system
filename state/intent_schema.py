from pydantic import BaseModel


class IntentOutput(BaseModel):

    intent: str

    sub_intent: str

    reasoning: str