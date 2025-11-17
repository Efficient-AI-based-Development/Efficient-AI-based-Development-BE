from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    user_id: str
    user_password: str


class UserCreate(BaseModel):
    user_id: str
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class UserRead(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
