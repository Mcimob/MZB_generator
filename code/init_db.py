from db.database import db
from db.models import User
from server import app


def main():
    with app.app_context():
        db.create_all()
        init_admin_user()


def init_admin_user():
    user = User(
        email="burckhardttim@gmail.com",
        name="Tim",
        password="sha256$kjPyB33NFhiSmjO4$ba0a68d788bf03562b8bed430cfc8eeecf67e6586affd6e380b590f432567a3b",
        admin=True,
    )
    db.session.add(user)
    db.session.commit()


if __name__ == "__main__":
    main()
