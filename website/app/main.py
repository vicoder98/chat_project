from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from .routers import auth, chat
from .database.database import engine, Base

app = FastAPI()

# Khởi tạo bảng trong cơ sở dữ liệu
Base.metadata.create_all(bind=engine)

# Đăng ký các router
app.include_router(auth.router)
app.include_router(chat.router)

# Route cho trang chủ

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return RedirectResponse(url="/login", status_code=303)
