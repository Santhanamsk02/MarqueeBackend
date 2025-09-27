import os
import json
from google.cloud import firestore
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Load Firebase credentials from environment variable
cred_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
credentials = service_account.Credentials.from_service_account_info(cred_info)

# Initialize Firestore client
db = firestore.Client(credentials=credentials)

# Firestore collections
students_collection = db.collection("students")
results_collection = db.collection("results")
questions_collection = db.collection("questions")
