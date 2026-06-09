from pydantic import BaseModel


class OutputAgentResponse(BaseModel):

    answer: str

    reasoning: str