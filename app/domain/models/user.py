# mypy: ignore-errors
from sqlalchemy import VARCHAR, Column, Integer

from common.base_orm import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(VARCHAR(30), index=True)
    email = Column(VARCHAR(30), unique=True, index=True)
