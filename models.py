from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
import re

class UserRegister(BaseModel):
    login: str = Field(..., min_length=6, description="Логин (от 6 символов, латиница и цифры)")
    password: str = Field(..., min_length=8, description="Пароль (от 8 символов)")
    full_name: str = Field(..., description="ФИО")
    birth_date: date = Field(..., description="Дата рождения")
    phone: str = Field(..., description="Номер телефона")
    email: EmailStr = Field(..., description="E-mail адрес")

    @field_validator('login')
    @classmethod
    def validate_login(cls, v):
        if not re.match(r"^[a-zA-Z0-9]+$", v):
            raise ValueError("Логин должен содержать только латинские буквы и цифры")
        return v

class UserLogin(BaseModel):
    login: str
    password: str
