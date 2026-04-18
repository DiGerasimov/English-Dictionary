from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    active_slots: int = 5
    daily_new_limit: int = 10
    voice_mode: bool = False
    is_admin: bool = False

    model_config = {"from_attributes": True}


class UserSettingsIn(BaseModel):
    active_slots: int = Field(ge=1, le=50)
    daily_new_limit: int = Field(ge=1, le=100)
    voice_mode: bool = False
