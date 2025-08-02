import os
import json
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # <<< YEH NAYI LINE HAI
from pydantic import BaseModel

# FastAPI app instance
app = FastAPI()

# <<< YEH NAYA CODE BLOCK HAI >>>
# CORS (Cross-Origin Resource Sharing) ko allow karna
# Yeh browser security ko batata hai ki hamara frontend (Streamlit) backend se baat kar sakta hai.
# api.py ke andar

# YEH BILKUL CORRECT HAI
origins = [
    "https://vote4cr2.streamlit.app",  # Aapka naya Streamlit URL
    "http://localhost",
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Sirf in websites se request allow karo
    allow_credentials=True,
    allow_methods=["*"], # Sabhi methods (GET, POST, etc.) allow karo
    allow_headers=["*"], # Sabhi headers allow karo
)
# <<< NAYA CODE BLOCK KHATAM >>>


# File paths for deployment
#DATA_DIR = "/var/data"
# Naya Code (Railway ke liye)
DATA_DIR = "/data"
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
VOTED_STUDENTS_FILE = os.path.join(DATA_DIR, "voted_students.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


# Pydantic Models for data validation
class CandidateCreate(BaseModel):
    name: str
    stream: str
    division: str
    gender: str

class Candidate(CandidateCreate):
    id: str
    votes: int

class VotePayload(BaseModel):
    candidate_id: str
    student_roll_no: Optional[str] = None

class AppSettings(BaseModel):
    election_status: str
    roll_number_rule: str
    show_vote_counts_to_students: bool

# Helper Functions to read/write data
def read_data(file_path, default_data=None):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if default_data is not None:
            write_data(file_path, default_data)
            return default_data
        return []
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_data if default_data is not None else []

def write_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the S.M. Shetty College CR Election API! (CORS Enabled)"}

@app.get("/settings", response_model=AppSettings)
def get_settings():
    default_settings = {"election_status": "Closed", "roll_number_rule": "Optional", "show_vote_counts_to_students": False}
    return read_data(SETTINGS_FILE, default_data=default_settings)

@app.post("/settings", response_model=AppSettings)
def update_settings(settings: AppSettings):
    write_data(SETTINGS_FILE, settings.dict())
    return settings

@app.get("/candidates", response_model=List[Candidate])
def get_candidates():
    return read_data(CANDIDATES_FILE, default_data=[])

@app.post("/candidates", response_model=Candidate, status_code=201)
def add_candidate(candidate: CandidateCreate):
    candidates = read_data(CANDIDATES_FILE, default_data=[])
    new_candidate = {**candidate.dict(), "id": str(uuid.uuid4()), "votes": 0}
    candidates.append(new_candidate)
    write_data(CANDIDATES_FILE, candidates)
    return new_candidate

@app.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: str):
    candidates = read_data(CANDIDATES_FILE, default_data=[])
    original_len = len(candidates)
    candidates = [c for c in candidates if c["id"] != candidate_id]
    if len(candidates) == original_len:
        raise HTTPException(404, "Candidate not found")
    write_data(CANDIDATES_FILE, candidates)
    return {"message": "Candidate deleted successfully"}

@app.post("/vote", response_model=Candidate)
def vote_for_candidate(payload: VotePayload):
    settings = get_settings()
    if settings['election_status'] == "Closed":
        raise HTTPException(status_code=403, detail="Voting is currently closed by the admin.")
    if settings['roll_number_rule'] == "Mandatory" and not payload.student_roll_no:
        raise HTTPException(status_code=400, detail="Roll Number is mandatory for voting.")

    candidates = read_data(CANDIDATES_FILE, default_data=[])
    candidate_to_vote = next((c for c in candidates if c["id"] == payload.candidate_id), None)
    if not candidate_to_vote:
        raise HTTPException(404, "Candidate not found")

    if payload.student_roll_no:
        voted_students = read_data(VOTED_STUDENTS_FILE, default_data=[])
        gender = candidate_to_vote['gender']
        if any(s['roll_no'] == payload.student_roll_no and s['voted_for'] == gender for s in voted_students):
            raise HTTPException(403, f"This Roll Number has already voted for a {gender} CR.")
        voted_students.append({"roll_no": payload.student_roll_no, "voted_for": gender})
        write_data(VOTED_STUDENTS_FILE, voted_students)

    for cand in candidates:
        if cand["id"] == payload.candidate_id:
            cand["votes"] += 1
            write_data(CANDIDATES_FILE, candidates)
            return cand
    raise HTTPException(500, "Could not cast vote.")

@app.get("/votestatus/{roll_no}")
def get_vote_status(roll_no: str):
    voted_students = read_data(VOTED_STUDENTS_FILE, default_data=[])
    status = {"Boy": False, "Girl": False}
    for student in voted_students:
        if student['roll_no'] == roll_no:
            status[student['voted_for']] = True
    return status

@app.get("/voter-stats")
def get_voter_stats():
    voted_students = read_data(VOTED_STUDENTS_FILE, default_data=[])
    unique_voters = {s['roll_no'] for s in voted_students}
    total_votes = sum(c['votes'] for c in read_data(CANDIDATES_FILE, default_data=[]))
    return {"unique_voter_count": len(unique_voters), "total_vote_count": total_votes}


