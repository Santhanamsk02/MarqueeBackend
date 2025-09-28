from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import students_collection as users_collection
from db import results_collection

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str
    
class VerifyUserRequest(BaseModel):
    email: str
    rollno: str
    regno: str
    dob: str
    

class ResetPasswordRequest(BaseModel):
    regno: str
    new_password: str


# Step 1: Verify user
@router.post("/forgot-password-verify")
async def forgot_password_verify(data: VerifyUserRequest):
    try:
        # Convert regno to integer for query
        regno_int = int(data.regno)
        
        # Query Firestore for matching user
        users_query = users_collection.where("email", "==", data.email)\
                                      .where("rollno", "==", data.rollno)\
                                      .where("regno", "==", regno_int)\
                                      .where("dob", "==", data.dob)\
                                      .limit(1).stream()
        
        user = None
        for doc in users_query:
            user = doc.to_dict()
            user['id'] = doc.id
            break
        
        print(data)

        if not user:
            raise HTTPException(status_code=404, detail="User not found or details incorrect")

        return {"message": "User verified. Proceed to reset password."}
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid registration number format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying user: {str(e)}")


# Step 2: Reset password
@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    try:
        # Convert regno to integer for query
        regno_int = int(data.regno)
        
        # Find the user document
        users_query = users_collection.where("regno", "==", regno_int).limit(1).stream()
        
        user_doc = None
        for doc in users_query:
            user_doc = doc
            break
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update the password
        users_collection.document(user_doc.id).update({"password": data.new_password})
        
        return {"message": "Password updated successfully"}
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid registration number format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting password: {str(e)}")


@router.post("/login")
async def login(data: LoginRequest):
    try:
        # Admin login check
        if data.username == "systemadmin" and data.password == "admin@pani@1210":
            return {
                "token": "admin", 
                "role": "admin",
                "done": "none"
            }

        # Student login - query Firestore
        users_query = users_collection.where("username", "==", data.username)\
                                     .where("password", "==", data.password)\
                                     .limit(1).stream()
        
        user = None
        for doc in users_query:
            user = doc.to_dict()
            user['id'] = doc.id
            break

        print(user)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid Credentials")

        return {
            "token": data.username, 
            "role": "student",
            "department": user.get("department", ""),
            "year": user.get("Year", ""),
            "section": user.get("Section", ""),
            "name": user.get("name", ""),
            "regno": user.get("regno", ""),
            "completed": user.get("completed", [])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@router.get("/user-profile/{username}")
async def get_user_profile(username: str):
    try:
        # Query Firestore for user by username
        users_query = users_collection.where("username", "==", username).limit(1).stream()
        
        user = None
        for doc in users_query:
            user_data = doc.to_dict()
            # Remove password field and add document ID
            if 'password' in user_data:
                del user_data['password']
            user_data['id'] = doc.id
            user = user_data
            break
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user profile: {str(e)}")


# Additional endpoint to get user by registration number (if needed)
@router.get("/user-by-regno/{regno}")
async def get_user_by_regno(regno: str):
    try:
        regno_int = int(regno)
        users_query = users_collection.where("regno", "==", regno_int).limit(1).stream()
        
        user = None
        for doc in users_query:
            user_data = doc.to_dict()
            if 'password' in user_data:
                del user_data['password']
            user_data['id'] = doc.id
            user = user_data
            break
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid registration number format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")


# Endpoint to update user profile
class UpdateProfileRequest(BaseModel):
    username: str
    email: str
    mobile: str

@router.put("/update-profile")
async def update_profile(data: UpdateProfileRequest):
    try:
        # Find the user document
        users_query = users_collection.where("username", "==", data.username).limit(1).stream()
        
        user_doc = None
        for doc in users_query:
            user_doc = doc
            break
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update the user profile
        update_data = {}
        if data.email:
            update_data['email'] = data.email
        if data.mobile:
            update_data['mobile'] = data.mobile
        
        users_collection.document(user_doc.id).update(update_data)
        
        return {"message": "Profile updated successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")