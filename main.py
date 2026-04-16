from fastapi import FastAPI, HTTPException, Response, Cookie, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request
import sqlite3
import os
import uuid
from typing import Optional

from models import UserRegister, UserLogin, ApplicationCreate, ReviewCreate, AppStatusUpdate
from database_manager import DatabaseManager, UserRepository

app = FastAPI(title="Водить.РФ")

os.makedirs("database", exist_ok=True)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
app.mount("/social", StaticFiles(directory="social"), name="social")

templates = Jinja2Templates(directory="templates")

db_manager = DatabaseManager("database/drive.db")
user_repo = UserRepository(db_manager)

active_sessions: dict[str, int] = {}

def get_current_user(session_id: str):
    if session_id and session_id in active_sessions:
        return user_repo.get_user_by_id(active_sessions[session_id])
    return None

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

    user_repo.ensure_admin_exists()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if user: return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"user": user})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if user: return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="register.html", context={"user": user})

@app.get("/application", response_class=HTMLResponse)
async def application_page(request: Request, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request=request, name="application.html", context={"user": user})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if not user:
        return RedirectResponse("/login", status_code=303)
    applications = user_repo.get_user_applications(user["id"])
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "applications": applications})

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if not user or user["login"] != "Admin26":
        return RedirectResponse(url="/", status_code=303)
        
    all_apps = user_repo.get_all_applications()
    return templates.TemplateResponse(request=request, name="admin.html", context={"user": user, "applications": all_apps})

@app.get("/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    if session_id in active_sessions:
        del active_sessions[session_id]
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response

@app.post("/api/register")
async def register(user: UserRegister):
    existing_user = user_repo.get_user_by_login(user.login)
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует.")
    try:
        user_repo.create_user(user.model_dump())
        return {"status": "success", "message": "Пользователь успешно зарегистрирован!"}
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при регистрации сервера.")

@app.post("/api/login")
async def loginAPI(credentials: UserLogin, response: Response):
    user = user_repo.get_user_by_login(credentials.login)
    if not user or not user_repo.verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = user["id"]
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return {"status": "success"}

@app.get("/api/transports")
async def get_transportsAPI():
    return user_repo.get_transports()

@app.post("/api/apply")
async def applyAPI(app_data: ApplicationCreate, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Авторизуйтесь")
    try:
        user_repo.create_application(user["id"], app_data.transport_id, str(app_data.start_date), app_data.payment_method)
        return {"status": "success"}
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка оформления")

@app.post("/api/review")
async def reviewAPI(review_data: ReviewCreate, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Авторизуйтесь")
    try:
        user_repo.create_review(user["id"], review_data.text, review_data.rating)
        return {"status": "success"}
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка сохранения")

@app.put("/api/application/{app_id}/status")
async def update_status_api(app_id: int, payload: AppStatusUpdate, session_id: Optional[str] = Cookie(None)):
    user = get_current_user(session_id)
    if not user or user["login"] != "Admin26":
        raise HTTPException(status_code=403, detail="Действие запрещено")
        
    valid_statuses = ("Новая", "Идет обучение", "Обучение завершено")
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Неверный статус")
        
    try:
        user_repo.update_application_status(app_id, payload.status)
        return {"status": "success"}
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка БД")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
