from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str
    security_question: str
    security_answer: str
    dob: str # Format: YYYY-MM-DD

class UserPublic(UserBase):
    id: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class PasswordResetVerify(BaseModel):
    email: EmailStr
    answer: Optional[str] = None
    dob: Optional[str] = None

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str
