# auth_cli.py
from core.auth.session import generate_token
from core.auth.users import authenticate_user, init_db, register_user


def register():
    user = input("Username: ")
    pw = input("Password: ")
    if register_user(user, pw):
        print(f"[OK] Registered user '{user}'")
    else:
        print("[ERROR] User already exists.")


def login():
    user = input("Username: ")
    pw = input("Password: ")
    if authenticate_user(user, pw):
        token = generate_token(user)
        print(f"[OK] Login successful. Token:\n{token}")
    else:
        print("[ERROR] Invalid credentials.")


def main():
    init_db()
    print("1. Register")
    print("2. Login")
    choice = input("Select> ")
    if choice == "1":
        register()
    elif choice == "2":
        login()


if __name__ == "__main__":
    main()
