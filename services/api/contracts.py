from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class NewSession(Contract):
    state: Literal['A','B']='A'
    scenario: str='GOLDEN'

class Actor(Contract):
    role: Literal['custodian','planner','approver','receiver']='planner'
    district: Literal['D1','D2']='D1'
    expected_version: int=Field(ge=1,default=1)

class StockInput(Actor):
    batch: str
    quantity: int=Field(ge=0,le=100000)
    mode: Literal['snapshot','receipt','consume']='snapshot'
    observed_at: str
    reason: str=Field(min_length=3,max_length=300)

class PlanInput(Actor):
    product: str='MED-001'
    recipient: str='A'
    forecast_id: str | None=None

class TransferInput(Actor):
    plan_id: str
    line_index: int=Field(ge=0,le=50,default=0)

class ReceiptInput(Actor):
    quantity: int=Field(gt=0,le=100000)

class CapacityInput(Actor):
    facility_id: str
    physical_beds: int | None=Field(default=None,ge=0,le=10000)
    operational_beds: int | None=Field(default=None,ge=0,le=10000)
    occupied_beds: int | None=Field(default=None,ge=0,le=10000)
    staff_by_role: dict[str,int]=Field(default_factory=dict,max_length=12)
    footfall: int | None=Field(default=None,ge=0,le=100000)
    @model_validator(mode='after')
    def beds(self):
        p,o,c=self.physical_beds,self.operational_beds,self.occupied_beds
        if (o is not None and (p is None or o>p)) or (c is not None and (o is None or c>o)):
            raise ValueError('occupied <= operational <= physical; unknown is null')
        if any(v<0 or v>1000 for v in self.staff_by_role.values()): raise ValueError('Invalid staff count')
        return self

class CSVInput(Actor):
    csv: str=Field(max_length=50000)

class ConfirmInput(Actor):
    draft_id: str
    observations: list[StockInput]=Field(min_length=1,max_length=100)

class ExtractInput(Actor):
    evidence_id: str

class ClockInput(Actor):
    hours: int=Field(ge=1,le=48)

class ReplenishmentInput(Actor):
    batch: str
    quantity: int=Field(gt=0,le=100000)
    eta_min_days: int=Field(ge=0,le=14)
    eta_max_days: int=Field(ge=0,le=14)
    @model_validator(mode='after')
    def eta(self):
        if self.eta_max_days<self.eta_min_days:raise ValueError('ETA range is reversed')
        return self
