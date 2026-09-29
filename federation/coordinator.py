"""Coordinator accepts only parameter messages. It has no database or history imports."""
import hashlib,json
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Update(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    state: str
    schema: str
    coefficients: list[float]=Field(min_length=3,max_length=3)
    sample_count: int=Field(ge=1,le=5000)
    validation_mae: float=Field(ge=0)
    @model_validator(mode='after')
    def shape(self):
        if self.schema!='count-v1:intercept,weekend,log-footfall' or self.state not in ['A','B']: raise ValueError('Contract mismatch')
        if any(abs(x)>20 for x in self.coefficients): raise ValueError('Unbounded update')
        return self

def aggregate(messages):
    updates=[Update.model_validate(m) for m in messages]
    if {m.state for m in updates}!={'A','B'} or len(updates)!=2: raise ValueError('One update from each state required')
    weights=np.array([m.sample_count for m in updates]); coef=np.average([m.coefficients for m in updates],axis=0,weights=weights)
    return {'schema':updates[0].schema,'coefficients':coef.tolist(),'update_hashes':[hashlib.sha256(json.dumps(m.model_dump(),sort_keys=True).encode()).hexdigest() for m in updates]}
