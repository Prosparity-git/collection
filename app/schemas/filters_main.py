from typing import List, Dict, Any
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


class CascadingOptionsResponse(BaseModel):
    branches: List[Dict[str, Any]]
    dealers: List[Dict[str, Any]]
    lenders: List[Dict[str, Any]]
    team_leads: List[Dict[str, Any]]
    rms: List[Dict[str, Any]]
    source_team_leads: List[Dict[str, Any]]
    source_rms: List[Dict[str, Any]]