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
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import shutil
import os
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
@app.post("/upload-video")
async def upload_video(video: UploadFile = File(...)):
    try:
        # Save temporarily
        temp_file = f"temp_{video.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        # Upload to Cloudinary with transformation (low quality)
        upload_result = cloudinary.uploader.upload(
            temp_file,
            resource_type="video",
            folder="proctoring_uploads",
            public_id=os.path.splitext(video.filename)[0],
            eager=[{"quality": "auto:low"}],  # ✅ lower video quality
            eager_async=True  # run transformation async
        )
        print("Video uploaded successfully")
        # Remove temp file
        os.remove(temp_file)

        return JSONResponse(
            content={
                "message": "Video uploaded successfully",
                "cloudinary_url": upload_result["secure_url"]
            }
        )

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
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
    screenshot = body.get("screenshot")
    department=body.get("department")
    year=body.get("year")
    section=body.get("section")
    name=body.get("name")
    regno=body.get("regno")
    mcqdone=body.get("mcqdone")
    codingdone=body.get("codingdone")
    mcqpercent=body.get("mcqpercent")
    codingpercent=body.get("codingpercent")
    totalpercent=body.get("totalpercent")
    mcqmalpractice=body.get("mcqmalpractice")
    codingmalpractice=body.get("codingmalpractice")

    screenshot_url = None
    if screenshot:
        img_data = screenshot
        if not screenshot.startswith("data:image"):
            img_data = f"data:image/png;base64,{screenshot}"
        try:
            upload_response = cloudinary.uploader.upload(
                img_data,
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
        "screenshot_url": screenshot_url,
         "department":department,
         "year":year,
         "section":section,
         "name":name,
         "regno":regno,
        "submitted_at": datetime.datetime.utcnow()
    }

    results_collection.insert_one(result_doc)
    students_collection.update_one(
        {"username": username},
        {"$set": {"done": done, "restrict": restrict, "doneTest": doneTest,"mcqdone":mcqdone,"codingdone":codingdone,"mcqpercent":mcqpercent,"codingpercent":codingpercent,"totalpercent":totalpercent,"mcqmalpractice":mcqmalpractice,"codingmalpractice":codingmalpractice}}
    )
    return {"message": f"Result saved for {username}"}


