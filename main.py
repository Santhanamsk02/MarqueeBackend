# backend/main.py
from fastapi import FastAPI, Request,APIRouter,HTTPException,Request,Body
from fastapi.middleware.cors import CORSMiddleware

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
import base64
import uvicorn
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from imagekitio import ImageKit

from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

# Initialize ImageKit with environment variables


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)


imagekit = ImageKit(
    private_key="private_i/4+I6CivNKk3MK1NOsUxe/p18g=",
    public_key="public_wyMUIeVq6wyoVLDl6RwkLvcxirA=",
    url_endpoint="https://ik.imagekit.io/1drwoyyw8"
)


@app.post("/upload-video")
async def upload_video(video: UploadFile = File(...)):
    try:
        # Save temporarily
        temp_file = f"temp_{video.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        # Upload to Cloudinary with transformation (low quality)
        result = imagekit.upload_file(
        file=open(temp_file, "rb"),
        file_name=f"{video.filename}.mp4",
        options=UploadFileRequestOptions(
        folder="/Video-Proof/",
        )
        
    )
        print("Video uploaded successfully")
        # Remove temp file
        os.remove(temp_file)

        return JSONResponse(
            content={
                "message": "Video uploaded successfully",
                "video_url": result.response_metadata.raw["url"]
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
            img_data = base64.b64decode(screenshot.split(",")[1])
        else:
            img_data = base64.b64decode(screenshot)
        try:
            upload_response = imagekit.upload_file(
        file=open(img_data, "rb"),
        file_name=f"{name}_{username}.jpg",
        options=UploadFileRequestOptions(
        transformation= {"quality": "20"},
        folder="/ImageProof/",
        
        )
    )
            screenshot_url = upload_response.response_metadata.raw["url"]
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
        "submitted_at": datetime.datetime.utcnow(),
        "done": done, 
         "doneTest": doneTest,
         "totalpercent":totalpercent,
    }

    results_collection.insert_one(result_doc)
    students_collection.update_one(
        {"username": username},
        {"$set": {"done": done, "restrict": restrict, "doneTest": doneTest,"mcqdone":mcqdone,"codingdone":codingdone,"mcqpercent":mcqpercent,"codingpercent":codingpercent,"totalpercent":totalpercent,"mcqmalpractice":mcqmalpractice,"codingmalpractice":codingmalpractice}}
    )
    return {"message": f"Result saved for {username}"}

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "santhanakrishnan9344@gmail.com"
EMAIL_PASSWORD = "rvwa fnjo qcga gcva"  # use App Password if Gmail


@app.post("/send-mail-to-all")
async def send_mail_to_all(request: Request, message: str = Body(..., embed=True)):
    try:
        # Fetch all emails from DB
        students = list(students_collection.find({}, {"email": 1, "_id": 0}))
        emails = [student["email"] for student in students if "email" in student]

        if not emails:
            raise HTTPException(status_code=404, detail="No emails found in database.")

        # Setup SMTP connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)

        # Send mail to each email
        for email in emails:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_SENDER
            msg["To"] = email
            msg["Subject"] = "Important Update"
            msg.attach(MIMEText(message, "plain"))

            server.sendmail(EMAIL_SENDER, email, msg.as_string())

        server.quit()

        return {"status": "success", "sent_to": len(emails)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

