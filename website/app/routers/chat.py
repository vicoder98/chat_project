from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, Form
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, RedirectResponse
from ..database import database
from ..models import models
from .websocket_protocol import ConnectionManager
from fastapi.templating import Jinja2Templates
import jwt
# Khởi tạo router và manager cho WebSocket
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
manager = ConnectionManager()

SECRET_KEY = "vicoder_secret_key"
ALGORITHM = "HS256"

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def decode_jwt(token: str):
    if token is None:
        return None
    try:
        token = token.split(" ")[1] 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login")

    user_email = decode_jwt(token)
    if not user_email:
        return RedirectResponse(url="/login")

    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        return RedirectResponse(url="/login")

    user_rooms = db.query(models.ChatRoom).filter(models.ChatRoom.owner_id == user.id).all()
    return templates.TemplateResponse("chat.html", {"request": request, "rooms": user_rooms, "user": user})

@router.post("/create-room", response_class=HTMLResponse)
async def create_room(request: Request, room_name: str = Form(...), db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_email = decode_jwt(token)
    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    existing_room = db.query(models.ChatRoom).filter(models.ChatRoom.name == room_name).first()
    if existing_room:
        raise HTTPException(status_code=400, detail="Room already exists")

    new_room = models.ChatRoom(name=room_name, owner_id=user.id)
    db.add(new_room)
    db.commit()
    return RedirectResponse(url="/chat", status_code=303)

@router.post("/delete-room", response_class=HTMLResponse)
async def delete_room(request: Request, room_id: int = Form(...), db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_email = decode_jwt(token)
    user = db.query(models.User).filter(models.User.email == user_email).first()

    room = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id, models.ChatRoom.owner_id == user.id).first()
    if not room:
        raise HTTPException(status_code=403, detail="Not authorized to delete this room")

    db.delete(room)
    db.commit()
    return RedirectResponse(url="/chat", status_code=303)

# Chỉnh sửa chức năng tìm kiếm
@router.get("/search-rooms", response_class=HTMLResponse)
async def search_rooms(request: Request, search_query: str, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_email = decode_jwt(token)
    user = db.query(models.User).filter(models.User.email == user_email).first()

    if not user:
        return RedirectResponse(url="/login")

    # Lấy danh sách các phòng có tên chứa chuỗi tìm kiếm
    rooms = db.query(models.ChatRoom).filter(models.ChatRoom.name.contains(search_query)).all()
    return templates.TemplateResponse("chat.html", {"request": request, "rooms": rooms, "user": user, "search_query": search_query})

@router.get("/chat/{room_name}", response_class=HTMLResponse)
async def room_chat_page(request: Request, room_name: str, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_email = decode_jwt(token)
    user = db.query(models.User).filter(models.User.email == user_email).first()

    room = db.query(models.ChatRoom).filter(models.ChatRoom.name == room_name).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = db.query(models.Message).filter(models.Message.room_id == room.id).order_by(models.Message.timestamp).all()
    return templates.TemplateResponse("room_chat.html", {"request": request, "room": room, "user": user, "messages": messages})

@router.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, room_name)

    room = db.query(models.ChatRoom).filter(models.ChatRoom.name == room_name).first()
    if not room:
        await websocket.close()
        return

    token = websocket.cookies.get("access_token")
    user_email = decode_jwt(token)
    user = db.query(models.User).filter(models.User.email == user_email).first()
    
    if not user:
        await websocket.close()
        return

    username = user.username

    messages = db.query(models.Message).filter(models.Message.room_id == room.id).order_by(models.Message.timestamp).all()
    for message in messages:
        await websocket.send_text(f"{message.username}: {message.content}")

    try:
        while True:
            content = await websocket.receive_text()
            new_message = models.Message(content=content, room_id=room.id, username=username)
            db.add(new_message)
            db.commit()
            await manager.broadcast(f"{username}: {content}", room_name)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
