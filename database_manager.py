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
            
    def get_user_by_id(self, user_id: int):
        with self.db.get_connection() as conn:
            return conn.execute("SELECT * FROM Users WHERE id = ?", (user_id,)).fetchone()

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

    def get_transports(self):
        with self.db.get_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM Transport").fetchall()]

    def create_application(self, user_id: int, transport_id: int, start_date: str, payment_method: str):
        query = '''
            INSERT INTO Applications (user_id, transport_id, start_date, payment_method, status)
            VALUES (?, ?, ?, ?, 'Новая')
        '''
        with self.db.get_connection() as conn:
            conn.execute(query, (user_id, transport_id, start_date, payment_method))
            conn.commit()

    def get_user_applications(self, user_id: int):
        query = '''
            SELECT a.id, a.start_date, a.payment_method, a.status, t.name as transport_name
            FROM Applications a
            JOIN Transport t ON a.transport_id = t.id
            WHERE a.user_id = ?
            ORDER BY a.id DESC
        '''
        with self.db.get_connection() as conn:
            return [dict(row) for row in conn.execute(query, (user_id,)).fetchall()]
            
    def create_review(self, user_id: int, text: str, rating: int):
        query = "INSERT INTO Reviews (user_id, text, rating) VALUES (?, ?, ?)"
        with self.db.get_connection() as conn:
            conn.execute(query, (user_id, text, rating))
            conn.commit()
