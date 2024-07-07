from app.domain.models.user import User
from common.database import session_scope


def test_db_session_decorator(setup_database) -> None:
    # insert
    with session_scope() as session:
        new_user = User(id=1, name="Test User", email="testemail.com")
        session.add(new_user)

    # select
    with session_scope() as session:
        user = session.query(User).filter_by(name="Test User").first()
        assert user is not None
        assert user.name == "Test User"
