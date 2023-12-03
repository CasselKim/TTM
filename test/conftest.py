import pytest

from common.base_orm import Base
from common.database import engine


@pytest.fixture(scope="module")
def setup_database() -> None:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
