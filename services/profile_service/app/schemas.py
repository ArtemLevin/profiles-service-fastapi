from pydantic import BaseModel, Field
from typing import Optional

class ProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str
    marketing_opt_in: bool = False

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone: Optional[str] = None
    marketing_opt_in: Optional[bool] = None

class ProfileOut(BaseModel):
    id: str
    user_id: int
    full_name: str
    phone: str
    marketing_opt_in: bool
    twofa_phone_verified: bool
