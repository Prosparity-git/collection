from typing import List
from pydantic import BaseModel

class FiltersOptionsResponse(BaseModel):
    emi_months: List[str]
    branches: List[str]
    dealers: List[str]
    lenders: List[str]
    statuses: List[str]
    ptpDateOptions: List[str]
    vehicle_statuses: List[str]
    team_leads: List[str]
    rms: List[str]
    demand_nums: List[str]