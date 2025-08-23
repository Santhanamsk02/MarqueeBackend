# backend/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from run_code import run_code
import datetime
from auth import router as auth_router
from db import results_collection
from db import students_collection
from admin import router as admin_router
import cloudinary.uploader
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)

@app.post("/compile")
async def compile_code(data: Request):
    body = await data.json()
    
    code = body.get("code")
    lang = body.get("language")
    expected_output = body.get("expected_output")
    

    result = run_code(lang, code,expected_output)
    output = result.get("stdout", "").strip()
    correct = output == str(expected_output).strip()

    return {
        "output": output,
        "success": correct,
        "error": result.get("stderr") if not correct else None
    }

cloudinary.config( 
  cloud_name = "dcfnjebbu", 
  api_key = "952332849418642", 
  api_secret = "ZcDgFv3qKFbLjlNVd-m0-qnjd-U",
  secure = True
)
@app.post("/submit")
async def submit_exam(data: Request):
    body = await data.json()
    results = body.get("results", [])
    username = body.get("username", "unknown_user")
    test_type = body.get("test_type", "Unknown_Test")
    malpractice = body.get("malpractice")
    total_marks = body.get("totalMarks")
    done = body.get("done")
    restrict = body.get("restrict")
    doneTest = body.get("doneTest", "None")
    screenshot = body.get("screenshot")  # base64 string

    screenshot_url = None
    if screenshot:
        try:
            # ✅ Upload optimized screenshot directly
            upload_response = cloudinary.uploader.upload(
                f"data:image/png;base64,{screenshot}",
                folder="exam_screenshots",
                public_id=f"{username}_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                overwrite=True,
                transformation=[
                    {"quality": "auto", "fetch_format": "auto", "width": 800, "crop": "scale"}
                ]
            )
            screenshot_url = upload_response.get("secure_url")
        except Exception as e:
            screenshot_url = f"Error uploading screenshot: {str(e)}"

    result_doc = {
        "username": username,
        "total_marks": total_marks,
        "details": results,
        "test_type": test_type,
        "malpractice": malpractice,
        "screenshot_url": screenshot_url,  # optimized URL stored
        "submitted_at": datetime.datetime.utcnow()
    }

    results_collection.insert_one(result_doc)
    students_collection.update_one(
        {"username": username},
        {"$set": {"done": done, "restrict": restrict, "doneTest": doneTest}}
    )
    return {"message": f"Result saved for {username}"}


