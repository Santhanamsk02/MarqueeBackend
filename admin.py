from fastapi import APIRouter, HTTPException, Query, Request
from db import students_collection, results_collection, questions_collection
from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File, HTTPException, Form
import pandas as pd
import io
from pymongo.errors import BulkWriteError
from typing import List, Optional
import random
from bson import ObjectId


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
    username: str
    password: str
    email: str
    mobile: str
    Class: str
    Section: str
    department: str
    regno: str
    Year: int
    dob: str


@router.post("/students")
def add_student(student: Student):
    students_collection.insert_one(student.dict())
    return {"message": "Student added"}


@router.post("/tests")
async def create_test(test: TestModel):
    result = questions_collection.insert_one(test.dict())
    return {"message": "Test saved successfully", "id": str(result.inserted_id)}


@router.get("/gettests")
async def get_test():
    return list(questions_collection.find({}, {"_id": 0}))


@router.get("/students")
def get_students(rollno: str = Query(None)):
    if rollno:
        # Filter by rollno (case-insensitive search)
        docs = list(
            students_collection.find(
                {"rollno": {"$regex": rollno, "$options": "i"}}, {"_id": 0}
            )
        )
        total_count = students_collection.count_documents(
            {"rollno": {"$regex": rollno, "$options": "i"}}
        )
    else:
        # Return only the first 50 students when rollno not mentioned
        docs = list(students_collection.find({}, {"_id": 0}).limit(50))
        total_count = students_collection.count_documents({})

    return {
        "total": total_count,  # total number of matching students
        "students": docs,  # student data (limited to 50 if rollno not provided)
    }


@router.get("/getallstudents")
def get_students():
    return list(students_collection.find({}, {"_id": 0}))


@router.get("/results")
def get_results():
    return list(results_collection.find({}, {"_id": 0}))


@router.put("/students/{username}")
async def update_student(username: str, request: Request):
    try:
        data = await request.json()  # 👈 directly get the full body (all 15 fields)

        # Ensure at least one field is sent
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")

        result = students_collection.update_one({"username": username}, {"$set": data})

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")

        return {"message": "Student updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(
                status_code=400, detail="Only CSV or Excel files are allowed"
            )

        # Ensure required fields are present
        required_columns = {
            "name",
            "rollno",
            "username",
            "password",
            "email",
            "mobile",
            "Class",
            "Section",
            "department",
            "regno",
            "Year",
            "dob",
        }
        if not required_columns.issubset(set(df.columns)):
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {required_columns - set(df.columns)}",
            )

        # Convert DataFrame to dict and insert into DB
        students_to_insert = df.to_dict(orient="records")
        for s in students_to_insert:
            if isinstance(s["dob"] and s["password"], pd.Timestamp):
                s["password"] = s["password"].strftime("%d-%m-%Y")
                s["dob"] = s["dob"].strftime("%d-%m-%Y")
            else:
                try:
                    s["password"] = pd.to_datetime(s["password"]).strftime("%d-%m-%Y")
                    s["dob"] = pd.to_datetime(s["dob"]).strftime("%d-%m-%Y")
                except:
                    pass

            s["done"] = 0
            s["restrict"] = False
            s["doneTest"] = None
            s["mcqdone"] = False
            s["codingdone"] = False
            s["mcqpercent"] = 0
            s["codingpercent"] = 0
            s["mcqmalpractice"] = False
            s["codingmalpractice"] = False
            s["totalpercent"] = 0

        try:
            students_collection.insert_many(students_to_insert, ordered=False)
        except BulkWriteError as bwe:
            raise HTTPException(
                status_code=400, detail="Duplicate entries found in upload"
            )
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
    docs = questions_collection.find({"TestType": "Coding"}, {"Coding": 1, "_id": 0})
    all_questions = []
    ques = list(
        questions_collection.find({"TestType": "Coding"}, {"TotalQuestions": 1, "_id": 0})
    )[0]
    for doc in docs:
        all_questions.extend(doc["Coding"])

    random_questions = random.sample(all_questions, int(ques["TotalQuestions"]))

    return [{"Coding": random_questions}]


@router.get("/mcqquestions")
def get_questions():
    docs = list(questions_collection.find({"TestType": "MCQ"}, {"MCQ": 1, "_id": 0}))
    print(docs)
    ques = list(
        questions_collection.find({"TestType": "MCQ"}, {"TotalQuestions": 1, "_id": 0})
    )[0]

    all_questions = []
    for doc in docs:
        all_questions.extend(doc["MCQ"])
    random_questions = random.sample(all_questions, int(ques["TotalQuestions"]))
    return [{"MCQ": random_questions}]


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
    TotalQuestions: str = Form(...),
    StartTime: str = Form(...),
):
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        questions = []

        if TestType == "MCQ":
            successful_questions = []
            failed_questions = []

            for index, row in df.iterrows():
                try:
                    # Check if all required columns exist
                    required_columns = [
                        "Question",
                        "Option1",
                        "Option2",
                        "Option3",
                        "Option4",
                        "CorrectAnswer",
                    ]
                    for col in required_columns:
                        if col not in row:
                            raise KeyError(f"Missing column: {col}")

                    # Validate that all required fields are not null/empty
                    if (
                        pd.isna(row["Question"])
                        or pd.isna(row["Option1"])
                        or pd.isna(row["Option2"])
                        or pd.isna(row["Option3"])
                        or pd.isna(row["Option4"])
                        or pd.isna(row["CorrectAnswer"])
                    ):
                        raise ValueError("One or more required fields are empty")

                    # Convert and validate correct answer
                    try:
                        correct_answer = int(
                            float(str(row["CorrectAnswer"]).strip())
                        )
                    except (ValueError, TypeError):
                        raise ValueError(
                            f"Invalid CorrectAnswer format: {row['CorrectAnswer']}"
                        )

                    if correct_answer not in [1, 2, 3, 4]:
                        raise ValueError(
                            f"CorrectAnswer must be between 1-4, got: {correct_answer}"
                        )

                    # Create question data
                    question_data = {
                        "question": str(row["Question"]).strip(),
                        "options": [
                            str(row["Option1"]).strip(),
                            str(row["Option2"]).strip(),
                            str(row["Option3"]).strip(),
                            str(row["Option4"]).strip(),
                        ],
                        "correctAnswer": correct_answer,
                    }

                    successful_questions.append(question_data)

                except Exception as e:
                    # Catch any exception and skip the problematic question
                    failed_questions.append(
                        {
                            "row_index": index,
                            "question_text": str(row.get("Question", "N/A"))[
                                :100
                            ],  # First 100 chars
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }
                    )
                    print(f"Skipping row {index} due to error: {e}")
                    continue

            # Insert the valid questions
            if successful_questions:
                test_document = {
                    "TestType": TestType,
                    "StartTime": StartTime,
                    "TestName": TestName,
                    "Time": Time,
                    "TotalQuestions": TotalQuestions,
                    "MCQ": successful_questions,
                    "metadata": {
                        "original_row_count": len(df),
                        "successful_questions": len(successful_questions),
                        "failed_questions": len(failed_questions),
                        "processing_date": pd.Timestamp.now().isoformat(),
                    },
                }

                # Optional: Add failed questions info if you want to keep track
                if failed_questions:
                    test_document["metadata"]["failed_questions_samples"] = (
                        failed_questions[:5]
                    )  # First 5 errors

                questions_collection.insert_one(test_document)

                print(f"✅ Successfully processed {len(successful_questions)} questions")
                print(f"❌ Skipped {len(failed_questions)} questions due to errors")

            else:
                raise ValueError(
                    "No valid questions could be processed from the provided data"
                )

        elif TestType == "Coding":
            for _, row in df.iterrows():
                questions.append(
                    {
                        "question": row["Question"],
                        "expectedOutput": row["ExpectedOutput"],
                    }
                )
            questions_collection.insert_one(
                {
                    "TestType": TestType,
                    "TestName": TestName,
                    "StartTime": StartTime,
                    "Time": Time,
                    "TotalQuestions": TotalQuestions,
                    "Coding": questions,
                }
            )

        return {
            "message": "Questions uploaded and saved to database successfully.",
            "questions": questions,
            "total": len(questions),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{rollno}")
def get_results_by_rollno(rollno: str):
    """Fetch results for a specific student using roll number"""
    result = list(results_collection.find({"regno": rollno}, {"_id": 0}))
    
    if not result:
        raise HTTPException(status_code=404, detail="No results found for this roll number")
    
    return result
