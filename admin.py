from fastapi import APIRouter, HTTPException, Query, Request
from db import students_collection, results_collection, questions_collection
from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File, HTTPException, Form
import pandas as pd
import io
from google.cloud import firestore
from typing import List, Optional
import random
from datetime import datetime
import json


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
    # Convert to dict and add the "completed" field
    data = student.dict()
    data["completed"] = []  # initialize empty list
    students_collection.document(student.username).set(data)
    return {"message": "Student added"}


@router.post("/tests")
async def create_test(test: TestModel):
    doc_ref = questions_collection.document()
    result = doc_ref.set(test.dict())
    return {"message": "Test saved successfully", "id": doc_ref.id}


@router.get("/gettests")
async def get_test():
    docs = questions_collection.stream()
    tests = []
    for doc in docs:
        test_data = doc.to_dict()
        test_data['id'] = doc.id  # Include Firestore document ID
        tests.append(test_data)
    return tests


@router.get("/students")
def get_students(rollno: str = Query(None)):
    if rollno:
        # Filter by rollno (case-insensitive search)
        docs = students_collection.where('rollno', '>=', rollno).where('rollno', '<=', rollno + '\uf8ff').stream()
        students_list = []
        for doc in docs:
            student_data = doc.to_dict()
            student_data['id'] = doc.id
            students_list.append(student_data)
        
        # For total count, we need to query again
        total_docs = students_collection.where('rollno', '>=', rollno).where('rollno', '<=', rollno + '\uf8ff').stream()
        total_count = len(list(total_docs))
    else:
        # Return only the first 50 students when rollno not mentioned
        docs = students_collection.limit(50).stream()
        students_list = []
        for doc in docs:
            student_data = doc.to_dict()
            student_data['id'] = doc.id
            students_list.append(student_data)
        
        # Get total count (note: this might be expensive for large collections)
        total_count = len(list(students_collection.stream()))

    return {
        "total": total_count,
        "students": students_list,
    }


@router.get("/getallstudents")
def get_students():
    docs = students_collection.stream()
    students_list = []
    for doc in docs:
        student_data = doc.to_dict()
        student_data['id'] = doc.id
        students_list.append(student_data)
    return students_list
@router.get("/results")
def get_results(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    testType: str = Query(..., description="Test type (e.g., MCQ, Coding)")
):
    try:
        docs = results_collection.where("test_type", "==", testType).stream()
        results_list = []
        

        for doc in docs:
            result_data = doc.to_dict()
            result_data["id"] = doc.id

            # Extract date part from ISO string
            stored_date = result_data.get("testdate")
            if stored_date and stored_date[:10] == date:  # "2025-09-23" from "2025-09-23T16:15"
                results_list.append(result_data)

        return results_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.put("/students/{username}")
async def update_student(username: str, request: Request):
    try:
        data = await request.json()

        # Ensure at least one field is sent
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")

        doc_ref = students_collection.document(username)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Student not found")

        doc_ref.update(data)
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
        
        batch = students_collection.firestore.batch()
        successful_inserts = 0
        
        for s in students_to_insert:
            try:
                # Handle date formatting
                if isinstance(s.get('dob'), pd.Timestamp):
                    s['dob'] = s['dob'].strftime("%d-%m-%Y")
                if isinstance(s.get('password'), pd.Timestamp):
                    s['password'] = s['password'].strftime("%d-%m-%Y")
                else:
                    try:
                        if s.get('password'):
                            s['password'] = pd.to_datetime(s['password']).strftime("%d-%m-%Y")
                        if s.get('dob'):
                            s['dob'] = pd.to_datetime(s['dob']).strftime("%d-%m-%Y")
                    except:
                        pass
                
                s['completed'] = []
                
                doc_ref = students_collection.document(s["username"])
                batch.set(doc_ref, s)
                successful_inserts += 1
                
            except Exception as e:
                print(f"Error processing student {s.get('username', 'unknown')}: {e}")
                continue
        
        # Commit the batch
        if successful_inserts > 0:
            batch.commit()
            return {"message": f"{successful_inserts} students added successfully"}
        else:
            raise HTTPException(status_code=400, detail="No students were added")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Questions
class Question(BaseModel):
    id: str  # Changed to string for Firestore document ID
    title: str
    expected_output: str


@router.post("/questions")
def add_question(q: Question):
    doc_ref = questions_collection.document()
    q.id = doc_ref.id  # Set the ID to the Firestore document ID
    doc_ref.set(q.dict())
    return {"message": "Question added"}


@router.put("/questions/{id}")
def update_question(id: str, q: Question):  # Changed to string ID
    doc_ref = questions_collection.document(id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Question not found")
    
    doc_ref.update(q.dict())
    return {"message": "Question updated"}


@router.post("/upload-excel")
async def upload_excel(
    file: UploadFile = File(...),
    Time: str = Form(...),
    TestName: str = Form(...),
    TestType: str = Form(...),
    TotalQuestions: str = Form(...),
    StartTime: str = Form(...),
    category: str = Form(...),
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
                    required_columns = [
                        "Question",
                        "Option1",
                        "Option2",
                        "Option3",
                        "Option4",
                        "CorrectAnswer",
                    ]
                    for col in required_columns:
                        if col not in df.columns:
                            raise KeyError(f"Missing column: {col}")

                    if (
                        pd.isna(row["Question"])
                        or pd.isna(row["Option1"])
                        or pd.isna(row["Option2"])
                        or pd.isna(row["Option3"])
                        or pd.isna(row["Option4"])
                        or pd.isna(row["CorrectAnswer"])
                    ):
                        raise ValueError("One or more required fields are empty")

                    try:
                        correct_answer = int(float(str(row["CorrectAnswer"]).strip()))
                    except (ValueError, TypeError):
                        raise ValueError(
                            f"Invalid CorrectAnswer format: {row['CorrectAnswer']}"
                        )

                    if correct_answer not in [0, 1, 2, 3]:
                        raise ValueError(
                            f"CorrectAnswer must be between 0-3, got: {correct_answer}"
                        )

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
                    failed_questions.append(
                        {
                            "row_index": index,
                            "question_text": str(row.get("Question", "N/A"))[:100],
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }
                    )
                    print(f"Skipping row {index} due to error: {e}")
                    continue

            if successful_questions:
                test_document = {
                    "TestType": TestType,
                    "StartTime": StartTime,
                    "TestName": TestName,
                    "category": category,
                    "Time": Time,
                    "TotalQuestions": TotalQuestions,
                    "MCQ": successful_questions,
                }


                questions_collection.document(test_document["TestName"]).set(test_document)

                print(f"✅ Successfully processed {len(successful_questions)} questions")
                print(f"❌ Skipped {len(failed_questions)} questions due to errors")

            else:
                raise ValueError(
                    "No valid questions could be processed from the provided data"
                )

        elif TestType == "Coding":
            codingquestions = []
            for index, row in df.iterrows():
                try:
                    if (
                        pd.isna(row["Question"])
                        or pd.isna(row["Function Name"])
                        or pd.isna(row["TestCases"])
                    ):
                        raise ValueError("One or more required fields are empty")

                    # Parse TestCases JSON
                    try:
                        testcases = row["TestCases"]
                    except Exception as e:
                        raise ValueError(
                            f"Invalid TestCases JSON format at row {index}: {e}"
                        )

                    codingquestions.append(
                        {
                            "question": str(row["Question"]).strip(),
                            "functionName": str(row["Function Name"]).strip(),
                            "testCases": testcases,
                        }
                    )
                    test_document={
                        "TestType": TestType,
                        "TestName": TestName,
                        "StartTime": StartTime,
                        "Time": Time,
                        "category": category,
                        "TotalQuestions": TotalQuestions,
                        "Coding": codingquestions,
                    }
                    questions_collection.document(test_document["TestName"]).set(test_document)
            

                except Exception as e:
                    print(f"⚠️ Skipping row {index} due to error: {e}")
                    continue


        return {
            "message": "Questions uploaded and saved to database successfully.",
            "questions": questions,
            "total": len(questions),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{rollno}")
def get_results_by_rollno(rollno: str):
    """Fetch results for a specific student using roll number"""
    docs = results_collection.where("regno", "==", rollno).stream()
    results = []
    
    for doc in docs:
        result_data = doc.to_dict()
        result_data['id'] = doc.id
        results.append(result_data)
    
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this roll number")
    
    return results