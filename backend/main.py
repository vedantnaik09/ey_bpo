from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uvicorn
from database import DatabaseManager
from ai_analyzer import ComplaintAnalyzer
from call_agent import resolve
import pandas as pd

app = FastAPI(title="BPO Complaint System API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and analyzer
db = DatabaseManager()
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
    priority_score: float
    status: str
    scheduled_callback: Optional[datetime]
    created_at: datetime
    # knowledge_base_solution: str

class ScheduleCallback(BaseModel):
    complaint_id: int
    callback_time: datetime
co=ComplaintAnalyzer()

@app.post("/complaints/", response_model=ComplaintResponse)
async def create_complaint(complaint: ComplaintBase):
  
    complaint_descriptions=db.get_complaint_descriptions(complaint.customer_phone_number)
    count=co.count_similar_complaints(complaint_descriptions)
    sentiment, urgency, politeness, priority = analyzer.analyze_complaint(complaint.complaint_description,count)
   
    
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000,reload=True)
