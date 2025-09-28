import os
from google.cloud import firestore
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Path to the credentials file
cred_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "service-account.json")
credentials = service_account.Credentials.from_service_account_file(cred_path)

# Initialize Firestore client
db = firestore.Client(credentials=credentials)

# Firestore collections
students_collection = db.collection("students")
results_collection = db.collection("results")
questions_collection = db.collection("questions")
