from datetime import datetime
from typing import List
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class UserListOut(BaseModel):
    total: int
    page: int
    limit: int
    users: List[UserOut]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
