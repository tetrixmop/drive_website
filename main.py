from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import sqlite3
import os

app = FastAPI(title="Водить.РФ")

os.makedirs("database", exist_ok=True)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
app.mount("/social", StaticFiles(directory="social"), name="social")

templates = Jinja2Templates(directory="templates")

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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
