import re

from pydantic import BaseModel, EmailStr, Field, field_validator

_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-zА-Яа-я])(?=.*\d).+$")


def _validate_password(value: str) -> str:
    """Пароль должен содержать хотя бы одну букву и одну цифру."""
    if not _PASSWORD_RE.match(value):
        raise ValueError("Пароль должен содержать буквы и цифры")
    return value


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


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


class PasswordConfirmIn(BaseModel):
    """Вход для подтверждающих действий — повторный ввод пароля."""
    password: str = Field(min_length=1, max_length=128)
