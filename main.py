# backend/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from run_code import run_code
import datetime
from auth import router as auth_router
from db import results_collection
from admin import router as admin_router


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
    

    result = run_code(lang, code)
    output = result.get("stdout", "").strip()
    correct = output == str(expected_output).strip()

    return {
        "output": output,
        "success": correct,
        "error": result.get("stderr") if not correct else None
    }


@app.post("/submit")
async def submit_exam(data: Request):
    body = await data.json()
    results = body.get("results", [])
    username = body.get("username", "unknown_user")
    test_type=body.get("test_type","Unknown_Test")
    malpractice=body.get("malpractice")
    total_marks = body.get("totalMarks")

    result_doc = {
        "username": username,
        "total_marks": total_marks,
        "details": results,
        "test_type":test_type,
        "malpractice":malpractice,
        "submitted_at": datetime.datetime.utcnow()
    }
    results_collection.insert_one(result_doc)
    return {"message": f"Result saved for {username}"}


