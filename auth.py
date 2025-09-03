from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import users_collection

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(data: LoginRequest):
    if data.username == "systemadmin" and data.password == "admin@pani@1210":
        return {"token": "admin", "role": "admin","done":"none"}

    user = users_collection.find_one({
        "username": data.username,
        "password": data.password
    })
    print(user)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    if (user["restrict"] == True):
        raise HTTPException(status_code=403, detail="User Restricted")

    return {"token": data.username, "role": "student","done":str(user["done"]),"doneTest":user["doneTest"],"department":user["department"],"year":user["Year"],"section":user["Section"],"name":user["name"],"regno":user["regno"],"mcqdone":user["mcqdone"],"codingdone":user["codingdone"],"mcqpercent":user["mcqpercent"],"codingpercent":user["codingpercent"],"totalpercent":user["totalpercent"],"mcqmalpractice":user["mcqmalpractice"],"codingmalpractice":user["codingmalpractice"]}

@router.get("/user-profile/{username}")
async def get_user_profile(username: str):
    user = users_collection.find_one({"username": username}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
