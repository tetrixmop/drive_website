import sqlite3
import hashlib
import os

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

class UserRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def hash_password(self, password: str, salt: str = None) -> str:
        if salt is None:
            salt = os.urandom(16).hex()
        hash_obj = hashlib.sha256(f"{salt}{password}".encode())
        return f"{salt}${hash_obj.hexdigest()}"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            salt, _ = hashed_password.split("$")
            return self.hash_password(plain_password, salt) == hashed_password
        except ValueError:
            return False

    def get_user_by_login(self, login: str):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM Users WHERE login = ?", (login,)).fetchone()

    def create_user(self, user_data: dict) -> int:
        hashed_pw = self.hash_password(user_data["password"])
        query = '''
            INSERT INTO Users (login, password, full_name, birth_date, phone, email)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                user_data["login"], 
                hashed_pw, 
                user_data["full_name"], 
                str(user_data["birth_date"]), 
                user_data["phone"], 
                user_data["email"]
            ))
            conn.commit()
            return cursor.lastrowid

    def ensure_admin_exists(self):
        admin = self.get_user_by_login("Admin26")
        if not admin:
            self.create_user({
                "login": "Admin26",
                "password": "Demo20",
                "full_name": "Администратор",
                "birth_date": "2000-01-01",
                "phone": "+70000000000",
                "email": "admin@drive.rf"
            })
