import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

class DatabaseManager:
    def __init__(self):
        # Load environment variables from .env.local
        load_dotenv(".env.local")
        
        # Retrieve database connection parameters from environment
        self.connection_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }

    def connect(self) -> Optional[psycopg2.extensions.connection]:
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None
        
    def submit_complaint(self, name: str, phone: str, description: str, 
                        sentiment: float, urgency: float, politeness: float, 
                        priority_score: float) -> bool:
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Insert complaint
                    cursor.execute("""
                        INSERT INTO complaints 
                        (customer_name, customer_phone_number, complaint_description, 
                         sentiment_score, urgency_score, priority_score, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING complaint_id
                        """, (name, phone, description, sentiment, urgency, 
                              priority_score, 'pending'))
                    
                    complaint_id = cursor.fetchone()[0]
                    
                    # Auto-schedule callback based on priority
                    self._auto_schedule_callback(cursor, complaint_id, priority_score)
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error submitting complaint: {e}")
                return False
            finally:
                conn.close()
        return False

    def _auto_schedule_callback(self, cursor, complaint_id: int, priority_score: float):
        """Automatically schedule callback based on priority and availability"""
        from datetime import datetime, timedelta

        # Get start and end dates based on priority
        start_date = datetime.now()

        if priority_score >= 0.7:  # High priority
            max_delay = timedelta(days=1)  # Within 24 hours
        elif priority_score >= 0.4:  # Medium priority
            max_delay = timedelta(days=2)  # Within 48 hours
        else:  # Low priority
            max_delay = timedelta(days=5)  # Within 5 days

        end_date = start_date + max_delay

        # Generate business hours time slots manually
        time_slots = []
        current = start_date
        while current <= end_date:
            if current.weekday() not in [5, 6] and 9 <= current.hour < 17:  # Exclude weekends and outside business hours
                time_slots.append(current)
            current += timedelta(minutes=30)  # 30-minute intervals

        # Find first available slot
        for slot in time_slots:
            cursor.execute("""
                SELECT 1
                FROM complaints
                WHERE scheduled_callback = %s
            """, (slot,))
            if cursor.fetchone() is None:  # Slot is available
                # Schedule the complaint
                cursor.execute("""
                    UPDATE complaints
                    SET scheduled_callback = %s
                    WHERE complaint_id = %s
                """, (slot, complaint_id))
                return  # Exit after scheduling

        print("No available slots found within the specified time frame.")


    def reschedule_callback(self, complaint_id: int, new_time: datetime) -> bool:
        """Manually reschedule a callback"""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Check if slot is available
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM complaints 
                        WHERE scheduled_callback = %s 
                        AND complaint_id != %s
                    """, (new_time, complaint_id))
                    
                    if cursor.fetchone()[0] > 0:
                        return False  # Slot already taken
                    
                    cursor.execute("""
                        UPDATE complaints
                        SET scheduled_callback = %s
                        WHERE complaint_id = %s
                    """, (new_time, complaint_id))
                    
                conn.commit()
                return True
            except Exception as e:
                print(f"Error rescheduling callback: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_scheduled_callbacks(self, date: str = None) -> pd.DataFrame:
        """Get all scheduled callbacks for a specific date"""
        conn = self.connect()
        if conn:
            try:
                query = """
                    SELECT 
                        complaint_id, customer_name, customer_phone_number,
                        complaint_description, scheduled_callback,
                        priority_score, status
                    FROM complaints 
                    WHERE scheduled_callback IS NOT NULL
                """
                if date:
                    query += " AND DATE(scheduled_callback) = %s"
                    return pd.read_sql_query(query, conn, params=(date,))
                return pd.read_sql_query(query, conn)
            finally:
                conn.close()
        return pd.DataFrame()

    def get_complaints(self) -> pd.DataFrame:
        conn = self.connect()
        if conn:
            try:
                query = """
                    SELECT 
                        complaint_id, customer_name, customer_phone_number,
                        complaint_description, sentiment_score, urgency_score,
                        priority_score, status, scheduled_callback,
                        created_at, knowledge_base_solution
                    FROM complaints 
                    ORDER BY priority_score DESC, created_at DESC
                """
                return pd.read_sql_query(query, conn)
            finally:
                conn.close()
        return pd.DataFrame()

    def get_dashboard_metrics(self) -> Tuple[int, int, float]:
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM complaints")
                    total = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'pending'")
                    pending = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT AVG(priority_score) FROM complaints")
                    avg_priority = cursor.fetchone()[0] or 0.0
                    
                    return total, pending, avg_priority
            finally:
                conn.close()
        return 0, 0, 0.0

    def resolve_complaint(self, complaint_id: int) -> bool:
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Fetch the current status of the complaint
                    cursor.execute("""
                        SELECT status
                        FROM complaints
                        WHERE complaint_id = %s
                    """, (complaint_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        print(f"No complaint found with ID {complaint_id}")
                        return False
                    
                    current_status = result[0]
                    # Determine the new status
                    new_status = 'pending' if current_status == 'resolved' else 'resolved'
                    
                    # Update the status
                    cursor.execute("""
                        UPDATE complaints
                        SET status = %s
                        WHERE complaint_id = %s
                    """, (new_status, complaint_id))
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error resolving complaint: {e}")
                return False
            finally:
                conn.close()
        return False
    
    def schedule_existing_complaints(self) -> bool:
        """Schedule all unscheduled complaints based on their priority"""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Get all unscheduled complaints
                    cursor.execute("""
                        SELECT complaint_id, priority_score 
                        FROM complaints 
                        WHERE scheduled_callback IS NULL 
                        AND status = 'pending'
                        ORDER BY priority_score DESC, created_at ASC
                    """)
                    
                    complaints = cursor.fetchall()
                    
                    for complaint_id, priority_score in complaints:
                        self._auto_schedule_callback(cursor, complaint_id, priority_score)
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error scheduling existing complaints: {e}")
                return False
            finally:
                conn.close()
        return False
    
    def upload_solution(self,num,solution):
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""UPDATE complaints SET knowledge_base_solution = %s WHERE customer_phone_number = %s"""
                       , (solution, num))
                    conn.commit()
                                            
                    print("Solution updated successfully.")
            except Exception  as e:
                print(f"Error uploading solution: {e}")
            return True