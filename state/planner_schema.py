# state/planner_schema.py

from pydantic import BaseModel
from typing import List, Optional


class PlannerOutput(BaseModel):

    tables: List[str]

    metrics: List[str]

    filters: List[str]

    group_by: List[str]

    aggregations: List[str]

    sort_by: Optional[str] = None

    limit: Optional[int] = None

    reasoning: str
    