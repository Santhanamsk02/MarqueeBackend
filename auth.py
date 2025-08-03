from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import users_collection

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(data: LoginRequest):
    if data.username == "admin" and data.password == "admin@123":
        return {"token": "admin", "role": "admin"}

    user = users_collection.find_one({
        "username": data.username,
        "password": data.password
    })

    if not user:
        raise HTTPException(status_code=401, detail="Invalid Credentials")

    return {"token": data.username, "role": "student"}

@router.get("/user-profile/{username}")
async def get_user_profile(username: str):
    user = users_collection.find_one({"username": username}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
