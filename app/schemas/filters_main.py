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
    source_rms: List[str] 
    source_team_leads: List[str]
    demand_num: List[str]
    dpd_buckets: List[str]