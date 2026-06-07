from pydantic import BaseModel


class SQLGeneratorOutput(BaseModel):

    sql_query: str

    reasoning: str