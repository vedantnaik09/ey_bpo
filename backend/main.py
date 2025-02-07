from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from firebase_admin import auth as firebase_auth
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request, status, Body
import firebase_admin
from firebase_admin import credentials, auth  # for verifying Firebase tokens

from database import DatabaseManager
from ai_analyzer import ComplaintAnalyzer
from call_agent import resolve
import pandas as pd

app = FastAPI(title="BPO Complaint System API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase Admin, if not already
if not firebase_admin._apps:
    cred = credentials.Certificate("./serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

# Initialize DB and create tables
db = DatabaseManager()
db.create_tables()  # <-- This ensures tables exist
analyzer = ComplaintAnalyzer()

# -------------- Pydantic models for complaints --------------


class ComplaintBase(BaseModel):
    customer_name: str
    customer_phone_number: str
    complaint_description: str


class ComplaintResponse(ComplaintBase):
    complaint_id: int
    sentiment_score: float
    urgency_score: float
    priority_score: float
    status: str
    scheduled_callback: Optional[datetime]
    created_at: datetime


class ScheduleCallback(BaseModel):
    complaint_id: int
    callback_time: datetime

# ------------------- Complaint Routes -----------------------


@app.post("/complaints/", response_model=ComplaintResponse)
async def create_complaint(complaint: ComplaintBase):
    # Example custom logic
    complaint_descriptions = db.get_complaint_descriptions(
        complaint.customer_phone_number)
    count = analyzer.count_similar_complaints(complaint_descriptions)
    sentiment, urgency, politeness, priority = analyzer.analyze_complaint(
        complaint.complaint_description,
        count
    )

    success = db.submit_complaint(
        complaint.customer_name,
        complaint.customer_phone_number,
        complaint.complaint_description,
        sentiment,
        urgency,
        politeness,
        priority,
    )
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to submit complaint")

    # Return the newest complaint (index 0 in the sorted DataFrame)
    complaints = db.get_complaints()
    return complaints.iloc[0].to_dict()


@app.get("/complaints/", response_model=List[ComplaintResponse])
async def get_complaints(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
):
    df = db.get_complaints()
    # Apply filters
    if status and status.lower() != "all":
        df = df[df['status'].str.lower() == status.lower()]

    if priority and priority.lower() != "all":
        if priority.lower() == "high":
            df = df[df['priority_score'] >= 0.7]
        elif priority.lower() == "medium":
            df = df[(df['priority_score'] >= 0.4) &
                    (df['priority_score'] < 0.7)]
        else:
            df = df[df['priority_score'] < 0.4]

    if search:
        df = df[
            df['customer_name'].str.contains(search, case=False)
            | df['complaint_description'].str.contains(search, case=False)
        ]

    # Convert each row to dict, fix types
    return [
        {
            **row.to_dict(),
            'complaint_id': int(row['complaint_id']),
            'scheduled_callback': row['scheduled_callback'].isoformat() if pd.notna(row['scheduled_callback']) else None
        }
        for _, row in df.iterrows()
    ]


@app.get("/dashboard/metrics/")
async def get_dashboard_metrics():
    total, pending, avg_priority = db.get_dashboard_metrics()
    return {
        "total_cases": total,
        "pending_cases": pending,
        "average_priority": avg_priority
    }


@app.post("/complaints/{complaint_id}/resolve")
async def resolve_complaint(complaint_id: int):
    complaint = db.get_complaints()
    complaint = complaint[complaint['complaint_id'] == complaint_id]
    if complaint.empty:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Example call to external 'resolve' function
    resolve(
        complaint.iloc[0]['customer_phone_number'],
        complaint.iloc[0]['complaint_description']
    )
    return {"message": "Complaint resolved successfully"}


@app.post("/complaints/{complaint_id}/toggleResolve")
async def toggle_resolve_complaint(complaint_id: int):
    complaint = db.get_complaints()
    complaint = complaint[complaint['complaint_id'] == complaint_id]
    if complaint.empty:
        raise HTTPException(status_code=404, detail="Complaint not found")

    success = db.resolve_complaint(complaint_id)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to resolve complaint")

    return {"message": "Toggled Resolve"}


@app.post("/complaints/schedule")
async def schedule_callback(schedule: ScheduleCallback):
    success = db.reschedule_callback(
        schedule.complaint_id, schedule.callback_time)
    if not success:
        raise HTTPException(status_code=400, detail="Time slot already taken")
    return {"message": "Callback scheduled successfully"}


@app.get("/complaints/schedule-all")
async def schedule_all_complaints():
    success = db.schedule_existing_complaints()
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to schedule complaints")
    return {"message": "Successfully scheduled all unscheduled complaints"}


@app.get("/callbacks/{date}")
async def get_callbacks(date: str):
    callbacks = db.get_scheduled_callbacks(date)
    return callbacks.to_dict('records')

# ------------------- Auth & Users Routes ---------------------


class TokenData(BaseModel):
    token: str


@app.post("/auth")
async def auth_user(token_data: TokenData):
    """
    Verifies a Firebase ID token and upserts the user (default role='employee')
    into the database if not already present.
    """
    try:
        decoded_token = auth.verify_id_token(token_data.token)
        email = decoded_token.get("email")
        if not email:
            raise HTTPException(
                status_code=400, detail="No email found in token")

        success = db.upsert_user(email, role="employee")
        if success:
            return {"message": "User upserted successfully", "email": email}
        else:
            raise HTTPException(
                status_code=500, detail="Could not upsert user into DB")

    except ValueError as e:
        raise HTTPException(
            status_code=401, detail=f"Token verification failed: {e}")


@app.get("/health/db")
async def health_db():
    """Check DB connectivity; returns 200 if reachable, 503 otherwise."""
    if db.check_db_connection():
        return {"message": "Database is connected successfully."}
    else:
        raise HTTPException(
            status_code=503, detail="Database is not reachable.")


class UserResponse(BaseModel):
    user_id: int
    email: str
    role: str


@app.get("/users", response_model=List[UserResponse])
async def get_users():
    """Fetch all users from the database."""
    df = db.get_all_users()
    # Convert each row to a dict
    return df.to_dict("records")


class CurrentUser(BaseModel):
    email: str
    role: str
    domain: str

def get_current_user(request: Request) -> CurrentUser:
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    print(auth_header)
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )

    token = auth_header.split("Bearer ")[1]
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        print(decoded_token)
        email = decoded_token.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No email in token"
            )

        # Fetch user from DB
        user_df = db.get_user_by_email(email)
        print(user_df)
        if user_df.empty:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in DB"
            )

        # Convert row to a Pydantic object
        row = user_df.iloc[0]
        print(row)
        return CurrentUser(
            email=row["email"],
            role=row["role"],
            domain=row["domain"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )


@app.post("/users/domain")
def change_domain( email: str = Body(...),
    new_domain: str = Body(...),
    current_user: CurrentUser = Depends(get_current_user)):
    print(f"Current user: {current_user}")
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can change domains")

    success = db.update_user_domain(email, new_domain)
    if success:
        return {"message": f"Domain updated for {email} to {new_domain}"}
    else:
        raise HTTPException(status_code=400, detail="Domain update failed")



@app.get("/")
async def root():
    return {"message": "Welcome to the BPO Complaint System API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
