from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str
    username: str  

class ChatRoomCreate(BaseModel):
    name: str
    owner_id: int

class ChatRoomSearch(BaseModel):
    name: str
