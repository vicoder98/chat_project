from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from .websocket_protocol import ConnectionManager
import jwt

app = FastAPI()
manager = ConnectionManager()

SECRET_KEY = "vicoder_secret_key"
ALGORITHM = "HS256"

def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("username")
    except jwt.PyJWTError:
        return None

@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, token: str = None):
    username = decode_jwt(token)
    if not username:
        await websocket.close(code=1008)  # Đóng kết nối nếu không có username hợp lệ
        return

    await manager.connect(websocket, username)
    try:
        await manager.broadcast(f"{username} joined the chat")
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{username} left the chat")
