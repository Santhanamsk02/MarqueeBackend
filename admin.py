from fastapi import APIRouter, HTTPException
from db import students_collection, results_collection, questions_collection
from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File, HTTPException,Form
import pandas as pd
import io
from pymongo.errors import BulkWriteError
from typing import List, Optional



class MCQModel(BaseModel):
    question: str
    options: List[str]
    correctAnswer: int

class CodingQuestionModel(BaseModel):
    question: str
    expectedOutput: str

class TestModel(BaseModel):
    Time: str
    TestName: str
    TestType: str
    TotalQuestions: str
    MCQ: Optional[List[MCQModel]] = []
    Coding: Optional[List[CodingQuestionModel]] = []

router = APIRouter(prefix="/admin")

# Student Model
class Student(BaseModel):
    name: str
    rollno: str
    username:str
    password: str
    email: str
    mobile: str
    Class: str
    Section:str
    department: str
    cgpa: float
    regno: str
    Year:int
@router.post("/students")
def add_student(student: Student):
    students_collection.insert_one(student.dict())
    return {"message": "Student added"}

@router.post("/tests")
async def create_test(test: TestModel):
    result = questions_collection.insert_one(test.dict())
    return {"message": "Test saved successfully", "id": str(result.inserted_id)}

@router.get("/tests")
async def get_test():
    return list(questions_collection.find({},{"_id":0}))

@router.get("/students")
def get_students():
    return list(students_collection.find({}, {"_id": 0}))

@router.put("/students/{username}")
def update_student(username: str, student: Student):
    result = students_collection.update_one({"username": username}, {"$set": student.dict()})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student updated"}

# Results
@router.get("/results")
def get_results():
    return list(results_collection.find({}, {"_id": 0}))


@router.post("/students/upload")
async def upload_students_file(file: UploadFile = File(...)):
    filename = file.filename
    try:
        # Read file content
        content = await file.read()

        # Determine file type and load data
        if filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        else:
            raise HTTPException(status_code=400, detail="Only CSV or Excel files are allowed")

        # Ensure required fields are present
        required_columns = {"name", "rollno", "username", "password", "email", "mobile", "Class","Section", "department", "cgpa", "regno","Year"}
        if not required_columns.issubset(set(df.columns)):
            raise HTTPException(status_code=400, detail=f"Missing columns: {required_columns - set(df.columns)}")

        # Convert DataFrame to dict and insert into DB
        students_to_insert = df.to_dict(orient="records")
        for s in students_to_insert:
            s["cgpa"] = float(s["cgpa"])
            s["done"] = 0
            s["restrict"] = False
            s["doneTest"] = None

        try:
            students_collection.insert_many(students_to_insert, ordered=False)
        except BulkWriteError as bwe:
            raise HTTPException(status_code=400, detail="Duplicate entries found in upload")
        return {"message": f"{len(students_to_insert)} students added successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Questions
class Question(BaseModel):
    id: int
    title: str
    expected_output: str

@router.post("/questions")
def add_question(q: Question):
    questions_collection.insert_one(q.dict())
    return {"message": "Question added"}

@router.get("/codingquestions")
def get_questions():
    return list(questions_collection.find({"TestType":"Coding"}, { "Coding": 1, "_id": 0 }))

@router.get("/mcqquestions")
def get_questions():
    return list(questions_collection.find({"TestType":"MCQ"}, { "MCQ": 1, "_id": 0 }))

@router.put("/questions/{id}")
def update_question(id: int, q: Question):
    result = questions_collection.update_one({"id": id}, {"$set": q.dict()})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question updated"}

@router.post("/upload-excel")
async def upload_excel(
    file: UploadFile = File(...),
    Time: str = Form(...),
    TestName: str = Form(...),
    TestType: str = Form(...),
    TotalQuestions: str = Form(...)
):
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        questions = []

        if TestType == "MCQ":
            for _, row in df.iterrows():
                questions.append({
                    "question": row["Question"],
                    "options": [row["Option1"], row["Option2"], row["Option3"], row["Option4"]],
                    "correctAnswer": int(row["CorrectAnswer"])
                })
            questions_collection.insert_one({
                "TestType": TestType,
                "TestName": TestName,
                "Time": Time,
                "TotalQuestions": TotalQuestions,
                "MCQ": questions
            })

        elif TestType == "Coding":
            for _, row in df.iterrows():
                questions.append({
                    "question": row["Question"],
                    "expectedOutput": row["ExpectedOutput"]   
                })
            questions_collection.insert_one({
                "TestType": TestType,
                "TestName": TestName,
                "Time": Time,
                "TotalQuestions": TotalQuestions,
                "Coding": questions
            })

        return {
            "message": "Questions uploaded and saved to database successfully.",
            "questions": questions,
            "total": len(questions)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
