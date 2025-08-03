from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
uri = "mongodb+srv://chandru:chandru123456789@cluster0.1c0n6gn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = client = MongoClient(uri, server_api=ServerApi('1'))
db = client["student"]
users_collection = db["students"]
students_collection = db["students"]
results_collection = db["results"]
questions_collection = db["questions"]

