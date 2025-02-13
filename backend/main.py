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
from call_agent import database,resolve_db

app = FastAPI(title="BPO Complaint System API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
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

# Pydantic models
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
    # knowledge_base_solution: str

class ScheduleCallback(BaseModel):
    complaint_id: int
    callback_time: datetime

# Add these new Pydantic models after the existing models
class UserUpdate(BaseModel):
    email: str
    full_name: str
    role: str
    domain: str

@app.post("/complaints/", response_model=ComplaintResponse)
async def create_complaint(complaint: ComplaintBase):
    token = db.generate_random_string()
    print("Token:", token)

    # Get complaint descriptions and ticket IDs
    complaint_list = db.get_complaint_descriptions(complaint.customer_phone_number)
    ticket_ids = db.get_ticket_id(complaint.customer_phone_number)
    print("Complaint List:", complaint_list)
    print("Ticket IDs:", ticket_ids)

    # Proceed with further processing
    past_count, first_similar_token = analyzer.count_similar_complaints_with_ticket(complaint_list, ticket_ids, token,complaint.complaint_description)
    print("Count:", past_count)
    print("First Similar Token:", first_similar_token)

    sentiment, urgency, politeness, priority = analyzer.analyze_complaint(complaint.complaint_description, past_count)
    problem_description=complaint.complaint_description
    solution=resolve_db(problem_description)
    category=analyzer.get_complaint_category(problem_description)
    
    
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

    # Get the created complaint
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
            df = df[(df['priority_score'] >= 0.4) & (df['priority_score'] < 0.7)]
        else:
            df = df[df['priority_score'] < 0.4]
    
    if search:
        df = df[
            df['customer_name'].str.contains(search, case=False) |
            df['complaint_description'].str.contains(search, case=False)
        ]
    
    return [
    {
        **row.to_dict(), 
        'complaint_id': int(row['complaint_id']),  # Explicitly convert to int
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
    
    # Call resolve function with phone number and description
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
    return callbacks.to_dict('records')

# ------------------- Auth & Users Routes ---------------------
class TokenData(BaseModel):
    token: str
@app.post("/auth")
async def auth_user(token_data: TokenData):
    """
    Verifies a Firebase ID token and upserts the user (default role='employee')
    into the database if not already present.
    Returns user email and role.
    """
    try:
        decoded_token = auth.verify_id_token(token_data.token)
        email = decoded_token.get("email")
        name = decoded_token.get("name", "")  # Get name from token
        
        success, role, domain = db.upsert_user(email, name)
        if success:
            return {"email": email, "role": role, "domain": domain}
        raise HTTPException(status_code=500, detail="Failed to create/update user")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
@app.get("/health/db")
async def health_db():
    """Check DB connectivity; returns 200 if reachable, 503 otherwise."""
    if db.check_db_connection():
        return {"message": "Database is connected successfully."}
    else:
        raise HTTPException(
            status_code=503, detail="Database is not reachable.")
class UserResponse(BaseModel):
    user_id: str  # Changed from int to str to handle UUID
    email: str
    full_name: str
    role: str
    domain: str
@app.get("/users", response_model=List[UserResponse])
async def get_users():
    """Fetch all users from the database."""
    df = db.get_all_users()
    # Convert UUID objects to strings in the DataFrame
    if 'user_id' in df.columns:
        df['user_id'] = df['user_id'].astype(str)
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

# Add this new route
@app.get("/complaints/by-category/{category}", response_model=List[ComplaintResponse])
async def get_complaints_by_category(
    category: str, 
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get complaints filtered by category. Admins can see all, employees only their domain."""
    try:
        df = db.get_complaints()
        
        # If user is not admin, they can only see complaints from their domain
        if current_user.role != "admin":
            if current_user.domain != category:
                raise HTTPException(
                    status_code=403, 
                    detail="Access forbidden for this category"
                )
            df = df[df['complaint_category'] == category]
        elif category != "all":  # Admin filtering specific category
            df = df[df['complaint_category'] == category]

        return [
            {
                **row.to_dict(),
                'complaint_id': int(row['complaint_id']),
                'scheduled_callback': row['scheduled_callback'].isoformat() 
                    if pd.notna(row['scheduled_callback']) else None
            }
            for _, row in df.iterrows()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add these new routes before the last line (if __name__ == "__main__":)

@app.put("/users/{email}", dependencies=[Depends(get_current_user)])
async def update_user(
    email: str,
    user_update: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Update user details. Only admins can update users."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update users"
        )
    print(user_update.email)
    success = db.update_user(
        email_to_update=email,
        email=user_update.email,
        role=user_update.role,
        domain=user_update.domain,
        full_name=user_update.full_name
    )
    
    if success:
        return {"message": "User updated successfully"}
    raise HTTPException(status_code=400, detail="Failed to update user")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)