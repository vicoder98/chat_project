from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ..database import  database
from ..models import models
from datetime import datetime, timedelta
import jwt

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

SECRET_KEY = "vicoder_secret_key"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.get("/register", response_class=HTMLResponse)
async def get_register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Kiểm tra xem email hoặc tên người dùng đã tồn tại chưa
    db_user_email = db.query(models.User).filter(models.User.email == email).first()
    db_user_username = db.query(models.User).filter(models.User.username == username).first()
    if db_user_email or db_user_username:
        raise HTTPException(status_code=400, detail="Email or username already registered")

    # Hash mật khẩu và lưu vào cơ sở dữ liệu
    hashed_password = pwd_context.hash(password)
    db_user = models.User(email=email, hashed_password=hashed_password, username=username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Trả về thông báo thành công và chuyển hướng
    
    return RedirectResponse(url="/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Tìm người dùng theo email
    db_user = db.query(models.User).filter(models.User.email == email).first()
    
    # Xác minh mật khẩu
    if not db_user or not pwd_context.verify(password, db_user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error_message": "Invalid email or password. Please try again."
        })

    # Tạo mã JWT
    access_token = create_access_token(data={"sub": db_user.email, "username": db_user.username})
    
    # Thiết lập mã JWT trong cookie
    response = RedirectResponse(url="/chat", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response