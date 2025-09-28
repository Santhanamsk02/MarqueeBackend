from fastapi import FastAPI, Request, APIRouter, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import datetime
from auth import router as auth_router
from db import results_collection, students_collection
from admin import router as admin_router
import cloudinary.uploader
import base64
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import shutil
import os
import uvicorn
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
import warnings
warnings.filterwarnings("ignore")

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

        # Upload to ImageKit
        result = imagekit.upload_file(
            file=open(temp_file, "rb"),
            file_name=f"{video.filename}.webM",
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
    try:
        body = await data.json()
        results = body.get("results", [])
        username = body.get("username", "unknown_user")
        test_type = body.get("test_type", "Unknown_Test")
        malpractice = body.get("malpractice")
        total_marks = body.get("totalMarks")
        screenshot = body.get("screenshot")
        department = body.get("department")
        year = body.get("year")
        section = body.get("section")
        name = body.get("name")
        regno = body.get("regno")
        percentage = body.get("percentage")
        completed = body.get("completed", [])
        testname = body.get("testname", "")
        starttime = body.get("StartTime")

        screenshot_url = None

        result_doc = {
            "username": username,
            "total_marks": total_marks,
            "details": results,
            "test_type": test_type,
            "malpractice": malpractice,
            "screenshot_url": screenshot_url,
            "department": department,
            "year": year,
            "section": section,
            "name": name,
            "regno": regno,
            "testname": testname,
            "testdate": starttime,
            "percentage": percentage,
            "submitted_at": datetime.datetime.utcnow().isoformat(),  # Convert to string for Firestore
        }

        # Add to Firestore results collection
        results_collection.document(result_doc["username"]+result_doc["testname"]).set(result_doc)
        
        # Update student's completed tests
        # First find the student document by username
        students_query = students_collection.where("username", "==", username).limit(1).stream()
        student_doc = None
        for doc in students_query:
            student_doc = doc
            break
        
        if student_doc:
            students_collection.document(student_doc.id).update({"completed": completed})
        else:
            print(f"Warning: Student with username {username} not found for update")

        return {"message": f"Result saved for {username}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting exam: {str(e)}")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "santhanakrishnan9344@gmail.com"
EMAIL_PASSWORD = "rvwa fnjo qcga gcva"  # use App Password if Gmail

@app.post("/send-mail-to-all")
async def send_mail_to_all(request: Request, message: str = Body(..., embed=True)):
    try:
        # Fetch all emails from Firestore
        students_docs = students_collection.stream()
        emails = []
        
        for doc in students_docs:
            student_data = doc.to_dict()
            if "email" in student_data and student_data["email"]:
                emails.append(student_data["email"])

        if not emails:
            raise HTTPException(status_code=404, detail="No emails found in database.")

        # Setup SMTP connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)

        # Send mail to each email
        success_count = 0
        failed_emails = []
        
        for email in emails:
            try:
                msg = MIMEMultipart()
                msg["From"] = EMAIL_SENDER
                msg["To"] = email
                msg["Subject"] = "Important Update"
                msg.attach(MIMEText(message, "plain"))

                server.sendmail(EMAIL_SENDER, email, msg.as_string())
                success_count += 1
            except Exception as e:
                failed_emails.append({"email": email, "error": str(e)})
                print(f"Failed to send email to {email}: {e}")

        server.quit()

        response = {
            "status": "success", 
            "sent_to": success_count,
            "total_emails": len(emails)
        }
        
        if failed_emails:
            response["failed_emails"] = failed_emails
            response["status"] = "partial_success"

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoint to get all results with pagination
@app.get("/results")
async def get_all_results(limit: int = 100, offset: int = 0):
    try:
        # Firestore doesn't have built-in offset, so we use pagination with start_after
        docs = results_collection.order_by("submitted_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        results_list = []
        for doc in docs:
            result_data = doc.to_dict()
            result_data['id'] = doc.id
            results_list.append(result_data)
            
        return {
            "results": results_list,
            "total": len(results_list),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")

# Endpoint to get results by username
@app.get("/results/{username}")
async def get_results_by_username(username: str):
    try:
        docs = results_collection.where("username", "==", username)\
                                .order_by("submitted_at", direction=firestore.Query.DESCENDING)\
                                .stream()
        
        results_list = []
        for doc in docs:
            result_data = doc.to_dict()
            result_data['id'] = doc.id
            results_list.append(result_data)
            
        return {
            "username": username,
            "results": results_list,
            "total": len(results_list)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results for {username}: {str(e)}")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "FastAPI with Firestore is running!"}

# Health check for database
@app.get("/health")
async def health_check():
    try:
        # Test Firestore connection by trying to count students
        docs = students_collection.limit(1).stream()
        count = len(list(docs))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)