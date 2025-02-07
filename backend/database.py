
import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import random,string

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
            print(f"Error connecting to database in database.py: {e}")
            return None
    def get_complaint_descriptions(self, complaint_phone: str) -> dict:
        conn = self.connect()
        if conn:
            try:
                # Query to fetch unresolved complaints for the user
                query = """
                    SELECT complaint_description
                    FROM complaints
                    WHERE status != 'resolved'
                    AND customer_phone_number = %s
                """
                # Execute the query and convert the result to a DataFrame
                df = pd.read_sql_query(query, conn, params=[complaint_phone])

                # Debug: Print DataFrame content
                print("Query result DataFrame:", df)

                # Ensure DataFrame has the required columns
                if "complaint_description" not in df:
                    print("Required columns not found in the DataFrame!")
                    return {"complaint_descriptions": []}

                # Convert the DataFrame column to a list and return as JSON
                return {"complaint_descriptions": df["complaint_description"].tolist()}
            except Exception as e:
                print("Error during database query:", e)
                return {"complaint_descriptions": []}  # Return an empty structure in case of an error
            finally:
                conn.close()
                
    def get_ticket_id(self, complaint_phone: str) -> dict:
        conn = self.connect()
        if conn:
            try:
                # Query to fetch unresolved complaints for the user
                query = """
                    SELECT ticket_id
                    FROM complaints
                    WHERE status != 'resolved'
                    AND customer_phone_number = %s
                """
                # Execute the query and convert the result to a DataFrame
                df = pd.read_sql_query(query, conn, params=[complaint_phone])

                # Debug: Print DataFrame content
                print("Query result DataFrame:", df)

                # Ensure DataFrame has the required columns
                if "ticket_id" not in df:
                    print("Required columns not found in the DataFrame!")
                    return {"ticket_id": []}

                # Convert the DataFrame column to a list and return as JSON
                return {"ticket_id": df["ticket_id"].tolist()}
            except Exception as e:
                print("Error during database query:", e)
                return {"ticket_id": []}  # Return an empty structure in case of an error
            finally:
                conn.close()

    def submit_complaint(self, name: str, phone: str, description: str, 
                    sentiment: float, urgency: float, politeness: float, 
                    priority_score: float,first_similar_token:str,past_count:int) -> bool:
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Insert complaint into the database
                    cursor.execute("""
                        INSERT INTO complaints 
                        (customer_name, customer_phone_number, complaint_description, 
                        sentiment_score, urgency_score, politeness_score, priority_score, status ,ticket_id,past_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s ,%s,%s)
                        RETURNING complaint_id
                    """, (name, phone, description, sentiment, urgency, politeness, priority_score, 'pending',first_similar_token,past_count))
                    
                    complaint_id = cursor.fetchone()[0]
                    
                    # Auto-schedule callback
                    print('before calling suto schedule')
                    scheduled = self._auto_schedule_callback(cursor, complaint_id, priority_score)
                    print('schedule part',scheduled)
                    
                    if not scheduled:
                        print(f"Could not schedule a callback for complaint ID {complaint_id}.")
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error submitting complaint: {e}")
                return False
            finally:
                conn.close()
        return False

    def _auto_schedule_callback(self, cursor, complaint_id: int, priority_score: float) -> bool:
        """Automatically schedule callback based on complaint time, priority, and availability."""
        from datetime import datetime, timedelta

        # Get the complaint submission time (current time in this case)
        now = datetime.now()

        # Start scheduling from the time of complaint submission
        start_date = now

        # Determine scheduling window based on priority
        if priority_score >= 0.7:  # High priority
            max_delay = timedelta(hours=48)  # Callback within 4 hours
        elif priority_score >= 0.4:  # Medium priority
            max_delay = timedelta(hours=72)  # Callback within 12 hours
        else:  # Low priority
            max_delay = timedelta(days=3)  # Callback within 1 day

        # Calculate the latest possible callback time
        end_date = start_date + max_delay

        # Log for debugging
        print(f"Start Date: {start_date}, End Date: {end_date}, Max Delay: {max_delay}")

        # Generate time slots (30-minute intervals within business hours)
        time_slots = []
        current = start_date
        while current <= end_date:
            # Check if the time falls within business hours (9 AM - 5 PM) and weekdays (Monday to Friday)
            if current.weekday() < 5 and 9 <= current.hour < 17:
                time_slots.append(current)
            current += timedelta(minutes=30)

        # Log time slots for debugging
        print(f"Available Time Slots: {time_slots}")

        # If no slots were generated within the available time window, return False
        if not time_slots:
            print("No available time slots.")
            return False

        # Attempt to schedule the earliest available slot
        for slot in time_slots:
            cursor.execute("""
                SELECT 1
                FROM complaints
                WHERE scheduled_callback = %s
            """, (slot,))
            if cursor.fetchone() is None:  # Slot is available
                cursor.execute("""
                    UPDATE complaints
                    SET scheduled_callback = %s
                    WHERE complaint_id = %s
                """, (slot, complaint_id))
                print(f"Scheduled callback for complaint ID {complaint_id} at {slot}")
                return True  # Successfully scheduled

        print("No available slot found for scheduling.")
        return False  # No slots available




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
                        created_at, knowledge_base_solution,ticket_id,past_count
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
        


    def generate_random_string(self, length=72):
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(length))
        return random_string
    
    def update_token_for_complaint(self, complaint_id: int) -> Optional[str]:
        """ 
        Update or generate a unique token for a specific complaint.
        
        :param complaint_id: The ID of the complaint to update the token for.
        :return: The generated token if successful, None otherwise.
        """
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Generate a unique token
                    token = ''.join(random.choices(string.ascii_letters + string.digits, k=72))
                    
                    # Update the token for the given complaint
                    cursor.execute("""
                        UPDATE complaints
                        SET token = %s
                        WHERE customer_phone_number = %s
                        RETURNING token
                    """, (token, complaint_id))
                    
                    # Fetch the updated token
                    updated_token = cursor.fetchone()
                    
                    if updated_token:
                        conn.commit()
                        print(f"Token updated successfully for complaint ID {complaint_id}.")
                        return updated_token[0]
                    else:
                        print(f"Complaint ID {complaint_id} not found.")
                        return None
            except Exception as e:
                print(f"Error updating token for complaint ID {complaint_id}: {e}")
                return None
            finally:
                conn.close()
        return None


        
        
# manager=DatabaseManager()
# complaint_descriptions=manager.get_complaint_descriptions("+917769915068")
# from ai_analyzer import ComplaintAnalyzer
# co=ComplaintAnalyzer()
# count=co.count_similar_complaints(complaint_descriptions)
# print(count)