from fastapi import FastAPI, HTTPException, Response, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request
import sqlite3
import os
import uuid
from typing import Optional

from models import UserRegister, UserLogin
from database_manager import DatabaseManager, UserRepository
import os

app = FastAPI(title="Водить.РФ")

os.makedirs("database", exist_ok=True)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
app.mount("/social", StaticFiles(directory="social"), name="social")

templates = Jinja2Templates(directory="templates")

db_manager = DatabaseManager("database/drive.db")
user_repo = UserRepository(db_manager)

# session_id -> user_id
active_sessions: dict[str, int] = {}

@app.on_event("startup")
def startup():
    with sqlite3.connect("database/drive.db") as conn:
        with open("database/schema.sql", "r", encoding="utf-8") as f:
            conn.executescript(f.read())
            
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Transport")
        if cursor.fetchone()[0] == 0:
            cursor.executescript('''
                INSERT INTO Transport (name, image_path) VALUES 
                ('Катер', 'assets/64536aafe5a415045ada8c4a.jpg'),
                ('Круизный лайнер', 'assets/658aad453358fbce48a7b97f.jpg'),
                ('Яхта', 'assets/5946dd94900ba9b56b0d52c88fff9d0d.jpg');
            ''')
        conn.commit()

    # Админ существует?
    user_repo.ensure_admin_exists()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/api/register")
async def register(user: UserRegister):
    existing_user = user_repo.get_user_by_login(user.login)
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует.")
    
    try:
        user_repo.create_user(user.model_dump())
        return {"status": "success", "message": "Пользователь успешно зарегистрирован!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при регистрации сервера.")

@app.post("/api/login")
async def login(credentials: UserLogin, response: Response):
    user = user_repo.get_user_by_login(credentials.login)
    
    if not user or not user_repo.verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # Создание сессии
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = user["id"]
    
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return {"status": "success", "message": "Успешный вход"}

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in active_sessions:
        return RedirectResponse(url="/", status_code=303)
        
    user_id = active_sessions[session_id]
    user = None
    with db_manager.get_connection() as conn:
        user = conn.execute("SELECT * FROM Users WHERE id = ?", (user_id,)).fetchone()
        
    if not user or user["login"] != "Admin26":
        return HTMLResponse(content="<h1>Доступ запрещен</h1><p>Только для администраторов.</p>", status_code=403)
        
    return HTMLResponse(content=f"<h1>Добро пожаловать в Панель Администратора, {user['full_name']}!</h1><p>Здесь вы можете управлять порталом.</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
