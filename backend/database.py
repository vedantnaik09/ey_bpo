
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
        
    def create_tables(self):
        """
        Creates the 'users' and 'complaints' tables if they do not exist.
        Ensures 'uuid-ossp' is enabled for UUID generation.
        """
        conn = self.connect()
        if not conn:
            print("Could not connect to DB; cannot create tables.")
            return
        try:
            with conn.cursor() as cursor:
                # Enable the uuid-ossp extension for uuid_generate_v4()
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

                # 1) Create 'users' table using UUID
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        domain VARCHAR(100) NOT NULL DEFAULT 'none',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # 2) Create 'complaints' table
                cursor.execute("""
                    CREATE TABLE complaints(
                    complaint_id SERIAL PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    customer_phone_number TEXT NOT NULL,
                    complaint_description TEXT NOT NULL,
                    complaint_category TEXT NOT NULL,
                    sentiment_score DOUBLE PRECISION,
                    urgency_score DOUBLE PRECISION,
                    priority_score DOUBLE PRECISION,
                    status TEXT,
                    scheduled_callback TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    knowledge_base_solution TEXT,
                    ticket_id TEXT,
                    politeness_score DOUBLE PRECISION,
                    past_count BIGINT
                );
                """)

            conn.commit()
            print("Tables ensured (created if not existed).")
        except Exception as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()

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
                    priority_score: float,first_similar_token:str,past_count:int,solution:str,category) -> bool:
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Insert complaint into the database
                    cursor.execute("""
                        INSERT INTO complaints 
                        (customer_name, customer_phone_number, complaint_description, 
                        sentiment_score, urgency_score, politeness_score, priority_score, status ,ticket_id,past_count,knowledge_base_solution,complaint_category)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s ,%s,%s,%s,%s)
                        RETURNING complaint_id
                    """, (name, phone, description, sentiment, urgency, politeness, priority_score, 'pending',first_similar_token,past_count,solution,category))
                    
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
                                        created_at, customer_name, customer_phone_number, complaint_id, complaint_description,
                                        sentiment_score, urgency_score, politeness_score,
                                        priority_score, scheduled_callback, status, ticket_id, past_count,
                                        knowledge_base_solution, complaint_category
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
    def upsert_user(self, email: str, role: str = "employee") -> Tuple[bool, str]:
        """
        Checks if user exists by email. If not, inserts a new user with 'role'.
        Returns (success_bool, role) tuple.
        """
        conn = self.connect()
        if not conn:
            return False, ""
        try:
            with conn.cursor() as cursor:
                # Check if user already exists
                cursor.execute("SELECT user_id, role FROM users WHERE email = %s", (email,))
                existing = cursor.fetchone()
                if not existing:
                    # Insert new user; domain will default to 'none'
                    cursor.execute("""
                        INSERT INTO users (user_id, email, role)
                        VALUES (uuid_generate_v4(), %s, %s)
                        RETURNING user_id
                    """, (email, role))
                    new_user_id = cursor.fetchone()[0]
                    print(f"Created new user with ID: {new_user_id} | Email: {email}")
                    return_role = role
                else:
                    # Return existing user's role
                    return_role = existing[1]
                    print(f"User with email {email} already exists. Skipping creation.")
                conn.commit()
                return True, return_role
        except Exception as e:
            print(f"Error upserting user: {e}")
            return False, ""
        finally:
            conn.close()
    def check_db_connection(self) -> bool:
        """Returns True if the DB connection succeeds."""
        conn = self.connect()
        if conn:
            conn.close()
            return True
        return False
    
    def get_user_by_email(self, email: str) -> pd.DataFrame:
        """
        Returns a DataFrame with the user row(s) that match the given email.
        If no row is found, the DataFrame will be empty.
        """
        conn = self.connect()
        if not conn:
            return pd.DataFrame()  # or handle error
        try:
            query = """
                SELECT user_id, email, role, domain
                FROM users
                WHERE email = %s
            """
            return pd.read_sql_query(query, conn, params=(email,))
        finally:
            conn.close()
    def get_all_users(self) -> pd.DataFrame:
        """Returns all users as a pandas DataFrame."""
        conn = self.connect()
        if conn:
            try:
                query = """
                    SELECT user_id, email, role, domain
                    FROM users
                    ORDER BY created_at DESC
                """
                return pd.read_sql_query(query, conn)
            finally:
                conn.close()
        return pd.DataFrame()
    def update_user_domain(self, email: str, new_domain: str) -> bool:
        """
        Updates the 'domain' for a given user by email.
        In your FastAPI route, ensure only admins can call this.
        """
        conn = self.connect()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                user_row = cursor.fetchone()
                if not user_row:
                    print(f"No user found with email: {email}")
                    return False
                # Update domain
                cursor.execute("""
                    UPDATE users
                    SET domain = %s
                    WHERE email = %s
                """, (new_domain, email))
            conn.commit()
            print(f"Updated domain for {email} to '{new_domain}'.")
            return True
        except Exception as e:
            print(f"Error updating user domain: {e}")
            return False
        finally:
            conn.close()


        
        
# manager=DatabaseManager()
# complaint_descriptions=manager.get_complaint_descriptions("+917769915068")
# from ai_analyzer import ComplaintAnalyzer
# co=ComplaintAnalyzer()
# count=co.count_similar_complaints(complaint_descriptions)
# print(count)