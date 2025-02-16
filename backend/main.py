from fastapi import FastAPI, HTTPException, Depends, Request, status, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uvicorn
import pandas as pd
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from firebase_admin import auth  # for verifying Firebase tokens

from database import DatabaseManager
from ai_analyzer import ComplaintAnalyzer
from call_agent import resolve, resolve_db

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

# -------------------
# Pydantic models
# -------------------
class ComplaintBase(BaseModel):
    customer_name: str
    customer_phone_number: str
    complaint_description: str

class ComplaintResponse(ComplaintBase):
    complaint_id: int
    sentiment_score: float
    urgency_score: float
    politeness_score: float
    priority_score: float
    status: str
    scheduled_callback: Optional[datetime]
    created_at: datetime
    ticket_id: Optional[str]
    past_count: Optional[int]
    knowledge_base_solution: Optional[str]
    complaint_category: Optional[str]

class ScheduleCallback(BaseModel):
    complaint_id: int
    callback_time: datetime

class UserUpdate(BaseModel):
    email: str
    # full_name: str
    role: str
    domain: str

# -------------------
# Complaint Routes
# -------------------
@app.post("/complaints/", response_model=ComplaintResponse)
async def create_complaint(complaint: ComplaintBase):
    token = db.generate_random_string()
    print("Token:", token)

    # Get complaint descriptions and ticket IDs
    complaint_list = db.get_complaint_descriptions(complaint.customer_phone_number)
    ticket_ids = db.get_ticket_id(complaint.customer_phone_number)
    print("Complaint List:", complaint_list)
    print("Ticket IDs:", ticket_ids)

    # Analyze
    past_count, first_similar_token = analyzer.count_similar_complaints_with_ticket(
        complaint_list, ticket_ids, token, complaint.complaint_description
    )
    print("Count:", past_count)
    print("First Similar Token:", first_similar_token)

    sentiment, urgency, politeness, priority = analyzer.analyze_complaint(
        complaint.complaint_description, past_count
    )
    problem_description = complaint.complaint_description
    solution = resolve_db(problem_description)
    category = analyzer.get_complaint_category(problem_description)

    success = db.submit_complaint(
        complaint.customer_name,
        complaint.customer_phone_number,
        complaint.complaint_description,
        sentiment,
        urgency,
        politeness,
        priority,
        first_similar_token,
        past_count,
        solution,
        category
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to submit complaint")

    # Return the newest complaint
    complaints = db.get_complaints()
    return complaints.iloc[0].to_dict()

@app.get("/complaints/", response_model=List[ComplaintResponse])
async def get_complaints(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
):
    df = db.get_complaints()
    print("knowledge base part in get complaint",df)

    # Apply filters
    if status and status.lower() != "all":
        df = df[df["status"].str.lower() == status.lower()]

    if priority and priority.lower() != "all":
        if priority.lower() == "high":
            df = df[df["priority_score"] >= 0.7]
        elif priority.lower() == "medium":
            df = df[(df["priority_score"] >= 0.4) & (df["priority_score"] < 0.7)]
        else:
            df = df[df["priority_score"] < 0.4]

    if search:
        df = df[
            df["customer_name"].str.contains(search, case=False)
            | df["complaint_description"].str.contains(search, case=False)
        ]

    return [
        {
            **row.to_dict(),
            "complaint_id": int(row["complaint_id"]),
            "scheduled_callback": row["scheduled_callback"].isoformat() if pd.notna(row["scheduled_callback"]) else None,
        }
        for _, row in df.iterrows()
    ]

@app.get("/dashboard/metrics/")
async def get_dashboard_metrics():
    total, pending, avg_priority = db.get_dashboard_metrics()
    return {
        "total_cases": total,
        "pending_cases": pending,
        "average_priority": avg_priority,
    }

@app.post("/complaints/{complaint_id}/resolve")
async def resolve_complaint(complaint_id: int):
    df = db.get_complaints()
    complaint = df[df["complaint_id"] == complaint_id]
    if complaint.empty:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Resolve
    resolve(
        complaint.iloc[0]["customer_phone_number"],
        complaint.iloc[0]["complaint_description"],
    )
    return {"message": "Complaint resolved successfully"}

@app.post("/complaints/{complaint_id}/toggleResolve")
async def toggle_resolve_complaint(complaint_id: int):
    df = db.get_complaints()
    complaint = df[df["complaint_id"] == complaint_id]
    if complaint.empty:
        raise HTTPException(status_code=404, detail="Complaint not found")

    success = db.resolve_complaint(complaint_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to resolve complaint")

    return {"message": "Toggled Resolve"}

@app.post("/complaints/schedule")
async def schedule_callback(schedule: ScheduleCallback):
    success = db.reschedule_callback(schedule.complaint_id, schedule.callback_time)
    if not success:
        raise HTTPException(status_code=400, detail="Time slot already taken")
    return {"message": "Callback scheduled successfully"}

@app.get("/complaints/schedule-all")
async def schedule_all_complaints():
    success = db.schedule_existing_complaints()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to schedule complaints")
    return {"message": "Successfully scheduled all unscheduled complaints"}

@app.get("/callbacks/{date}")
async def get_callbacks(date: str):
    callbacks = db.get_scheduled_callbacks(date)
    return callbacks.to_dict("records")

# -------------------
# Auth & Users Routes
# -------------------
class TokenData(BaseModel):
    token: str

@app.post("/auth")
async def auth_user(token_data: TokenData):
    """
    Verifies a Firebase ID token and upserts the user (default role='employee')
    into the database if not already present.
    Then returns the actual role from the DB (e.g. 'admin').
    """
    try:
        decoded_token = auth.verify_id_token(token_data.token)
        email = decoded_token.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="No email found in token")

        # Upsert user with default role 'employee' if new
        success = db.upsert_user(email, role="employee")
        if not success:
            raise HTTPException(status_code=500, detail="Could not upsert user into DB")

        # Now fetch user from DB to get actual role
        user_df = db.get_user_by_email(email)
        if user_df.empty:
            raise HTTPException(status_code=500, detail="User was upserted but not found in DB")

        row = user_df.iloc[0]
        return {
            "message": "User upserted successfully",
            "email": row["email"],
            "role": row["role"],
            "domain": row["domain"],
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {e}")

@app.get("/health/db")
async def health_db():
    """Check DB connectivity; returns 200 if reachable, 503 otherwise."""
    if db.check_db_connection():
        return {"message": "Database is connected successfully."}
    else:
        raise HTTPException(status_code=503, detail="Database is not reachable.")

class UserResponse(BaseModel):
    user_id: str  # for UUID
    email: str
    full_name: Optional[str] = None  # if not stored
    role: str
    domain: str

@app.get("/users", response_model=List[UserResponse])
async def get_users():
    """Fetch all users from the database."""
    df = db.get_all_users()
    # Convert user_id from UUID to string
    if "user_id" in df.columns:
        df["user_id"] = df["user_id"].astype(str)
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
def change_domain(
    email: str = Body(...),
    new_domain: str = Body(...),
    current_user: CurrentUser = Depends(get_current_user)
):
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

@app.get("/complaints/by-category/{category}", response_model=List[ComplaintResponse])
async def get_complaints_by_category(
    category: str, 
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get complaints filtered by category. Any user can see complaints from any category."""
    try:
        df = db.get_complaints()
        print("in by category df response", df)
        print("df types",df.dtypes)
        print("df heades",df.head())

        # Filter complaints by category if it's not "all"
        if category != "all":
            df = df[df['complaint_category'] == category]

        return [
            {
                "complaint_id": int(row["complaint_id"]),
                "sentiment_score": float(row["sentiment_score"]),
                "urgency_score": float(row["urgency_score"]),
                "politeness_score": float(row["politeness_score"]),
                "priority_score": float(row["priority_score"]),
                "status": str(row["status"]),
                "scheduled_callback": row["scheduled_callback"].isoformat() 
                    if pd.notna(row["scheduled_callback"]) else None,
                "created_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
                "ticket_id": str(row["ticket_id"]) if pd.notna(row["ticket_id"]) else None,
                "past_count": int(row["past_count"]) if pd.notna(row["past_count"]) else None,
                "knowledge_base_solution": str(row["knowledge_base_solution"]) if pd.notna(row["knowledge_base_solution"]) else None,
                "complaint_category": str(row["complaint_category"]) if pd.notna(row["complaint_category"]) else None,
                "customer_name": str(row["customer_name"]),
                "customer_phone_number": str(row["customer_phone_number"]),
                "complaint_description": str(row["complaint_description"]),
            }
            for _, row in df.iterrows()
        ]

    except Exception as e:
        print("error in by cateegory exception",e)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/users/{email}", dependencies=[Depends(get_current_user)])
async def update_user(
    email: str,
    user_update: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Update user details. Only admins can update users."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")

    print(f"Updating user: {email}")
    print(f"Received data: {user_update.dict()}")  # Debugging

    success = db.update_user(
        email_to_update=email,
        email=user_update.email,
        role=user_update.role,
        domain=user_update.domain,
        # full_name=user_update.full_name
    )

    if success:
        print("User updated successfully")
        return {"message": "User updated successfully"}

    print("Update failed")
    raise HTTPException (status_code=400, detail="Failed to update user")


@app.get("/calls")
async def get_calls(current_user: CurrentUser = Depends(get_current_user)):
    calls_df = db.get_calls_with_messages()
    return calls_df.to_dict(orient="records")

@app.post("/calls")
async def create_call(call: dict, current_user: CurrentUser = Depends(get_current_user)):
    call_id = db.add_call(call["caller"], call["receiver"])
    if not call_id:
        raise HTTPException(status_code=500, detail="Failed to create call")
    return {"call_id": call_id}

@app.put("/calls/{call_id}/end")
async def end_call(call_id: str, current_user: CurrentUser = Depends(get_current_user)):
    success = db.update_call_end(call_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update call")
    return {"success": True}

@app.post("/calls/{call_id}/messages")
async def add_message(
    call_id: str,
    message: dict,
    current_user: CurrentUser = Depends(get_current_user)
):
    success = db.add_message(call_id, message["sender"], message["message"])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add message")
    return {"success": True}

# -------------------
# Graph Endpoints
# -------------------
class ComplaintTrendResponse(BaseModel):
    date: str
    count: int

class ComplaintCategoryResponse(BaseModel):
    category: str
    count: int

class StatusDistributionResponse(BaseModel):
    status: str
    count: int

class PastUrgencyResponse(BaseModel):
    past_count: int
    priority_score: float

class PriorityResolutionResponse(BaseModel):
    priority_score: float
    scheduling_time: Optional[float]  # in hours

@app.get("/complaints/trends")
def get_complaint_trends():
    """Fetch complaint trends over time."""
    try:
        result = db.get_complaint_trends()
        if result is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching complaint trends: {str(e)}")

@app.get("/complaints/categories", response_model=List[ComplaintCategoryResponse])
def get_complaint_categories():
    """Fetch complaint category distribution."""
    try:
        return db.get_complaint_categories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching complaint categories: {str(e)}")

@app.get("/complaints/resolution_time")
def get_resolution_time():
    """Fetch complaint resolution times."""
    try:
        result = db.get_resolution_time()
        if result is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resolution times: {str(e)}")

@app.get("/complaints/priority_vs_resolution", response_model=List[PriorityResolutionResponse])
def get_priority_vs_resolution_speed():
    """Fetch priority score vs resolution speed analysis."""
    try:
        return db.get_priority_vs_resolution_speed()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching priority vs resolution speed: {str(e)}")

@app.get("/complaints/status_distribution", response_model=List[StatusDistributionResponse])
def get_status_distribution():
    """Fetch complaint status distribution."""
    try:
        return db.get_status_distribution()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching status distribution: {str(e)}")

@app.get("/complaints/past_vs_urgency", response_model=List[PastUrgencyResponse])
def get_past_complaints_vs_urgency():
    """Fetch past complaints vs urgency for bubble chart."""
    try:
        return db.get_past_complaints_vs_urgency()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching past complaints vs urgency: {str(e)}")

@app.get("/transcripts")
def get_transcripts():
    """Fetch call transcripts."""
    try:
        return db.get_transcripts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transcripts: {str(e)}")

# -------------------
# Main
# -------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
