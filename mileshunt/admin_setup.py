"""Create the initial admin user. Run once after deployment."""

import sys
from mileshunt.db import create_user, init_db


def main():
    init_db()

    email = input("Admin email: ").strip()
    name = input("Admin name: ").strip()
    password = input("Admin password: ").strip()

    if not email or not name or not password:
        print("All fields required.")
        sys.exit(1)

    try:
        user_id = create_user(email, name, password, is_admin=True)
        print(f"Admin user created (id={user_id}): {email}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
