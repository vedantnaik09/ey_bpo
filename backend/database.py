import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, List , Dict
import random,string
from psycopg2.extras import RealDictCursor
load_dotenv(".env.local")

class DatabaseManager:
    def __init__(self):
        # Load environment variables from .env.local
        
        # Retrieve database connection parameters from environment
        self.connection_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        print("Database connection parameters:", {k: v for k, v in self.connection_params.items() if k != "password"})

    def connect(self) -> Optional[psycopg2.extensions.connection]:
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            print(f"Error connecting to database in database.py: {e}")
            return None
        
    def create_tables(self):
        """
        Creates all necessary tables if they do not exist.
        Ensures 'uuid-ossp' is enabled for UUID generation.
        """
        conn = self.connect()
        if not conn:
            print("Could not connect to DB; cannot create tables.")
            return
        try:
            with conn.cursor() as cursor:
                # Enable required extensions
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

                # 1) Create 'users' table using UUID
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        full_name VARCHAR(255) NOT NULL DEFAULT '',
                        email VARCHAR(255) UNIQUE NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        domain VARCHAR(100) NOT NULL DEFAULT 'none',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # 2) Create 'complaints' table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS complaints(
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

                # 3) Create 'calls' table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS calls (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        caller VARCHAR(255) NOT NULL,
                        receiver VARCHAR(255) NOT NULL,
                        start_time TIMESTAMP NOT NULL DEFAULT NOW(),
                        end_time TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # 4) Create 'messages' table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
                        sender VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                """)

            conn.commit()
            print("All tables ensured (created if not existed).")
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
    def upsert_user(self, email: str, full_name: str = "", role: str = "employee") -> Tuple[bool, str, str]:
        """
        Checks if user exists by email. If not, inserts a new user with 'role'.
        Returns (success_bool, role, domain) tuple.
        """
        conn = self.connect()
        if not conn:
            return False, "", ""
        try:
            with conn.cursor() as cursor:
                # Check if user already exists
                cursor.execute("SELECT user_id, role, domain FROM users WHERE email = %s", (email,))
                existing = cursor.fetchone()
                if not existing:
                    # Insert new user
                    cursor.execute("""
                        INSERT INTO users (user_id, email, role, full_name)
                        VALUES (uuid_generate_v4(), %s, %s, %s)
                        RETURNING user_id
                    """, (email, role, full_name))
                    new_user_id = cursor.fetchone()[0]
                    return_role = role
                    return_domain = 'none'
                else:
                    # Update existing user's name if provided
                    if full_name:
                        cursor.execute("""
                            UPDATE users 
                            SET full_name = %s 
                            WHERE email = %s
                        """, (full_name, email))
                    # Return existing user's role and domain
                    return_role = existing[1]
                    return_domain = existing[2]
                conn.commit()
                return True, return_role, return_domain
        except Exception as e:
            print(f"Error upserting user: {e}")
            return False, "", ""
        finally:
            conn.close()

    def get_all_users(self) -> pd.DataFrame:
        """Returns all users as a pandas DataFrame."""
        conn = self.connect()
        if conn:
            try:
                query = """
                    SELECT 
                        user_id::text,
                        email,
                        full_name,
                        role,
                        domain
                    FROM users
                    ORDER BY created_at DESC
                """
                return pd.read_sql_query(query, conn)
            finally:
                conn.close()
        return pd.DataFrame()

    def update_user(self, email_to_update: str, email: str, role: str, domain: str, full_name: str) -> bool:
        """Update user details."""
        conn = self.connect()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                query = """
                UPDATE users 
                SET role = %s, domain = %s, full_name = %s , email = %s
                WHERE email = %s
                """
                cursor.execute(query, (role, domain, full_name, email, email_to_update))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
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
        
    def get_calls_with_messages(self) -> pd.DataFrame:
        """Get all calls with their associated messages/transcripts"""
        conn = self.connect()
        if conn:
            try:
                query = """
                    SELECT 
                        c.id as call_id,
                        c.caller,
                        c.receiver,
                        c.start_time,
                        c.end_time,
                        c.created_at,
                        json_agg(json_build_object(
                            'message_id', m.id,
                            'message', m.message,
                            'sender', m.sender,
                            'timestamp', m.timestamp
                        )) as messages
                    FROM calls c
                    LEFT JOIN messages m ON c.id = m.call_id
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                """
                return pd.read_sql_query(query, conn)
            finally:
                conn.close()
        return pd.DataFrame()

    def add_call(self, caller: str, receiver: str) -> Optional[str]:
        """Add a new call and return its ID"""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO calls (caller, receiver)
                        VALUES (%s, %s)
                        RETURNING id
                    """, (caller, receiver))
                    call_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(call_id)
            except Exception as e:
                print(f"Error adding call: {e}")
                return None   
            finally:
                conn.close()
        return None

    def update_call_end(self, call_id: str) -> bool:
        """Update call end time"""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE calls
                        SET end_time = NOW()
                        WHERE id = %s
                    """, (call_id,))
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error updating call end: {e}")
                return False
            finally:
                conn.close()
        return False

    def add_message(self, call_id: str, sender: str, message: str) -> bool:
        """Add a message/transcript to a call"""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO messages (call_id, sender, message)
                        VALUES (%s, %s, %s)
                    """, (call_id, sender, message))
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error adding message: {e}")
                return False
            finally:
                conn.close()
        return False
    
    
    #graphs part

    def get_complaint_trends(self) -> Optional[List[Dict]]:
        """Fetches complaint trends over time (daily complaint count)."""
        conn = self.connect()  # Establish a new connection
        if not conn:
            return None
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT DATE(created_at) AS date, COUNT(*) AS count
                    FROM complaints
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC;
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching complaint trends: {e}")
            return None
        finally:
            conn.close()  # Close the connection properly

    def get_complaint_categories(self) -> Optional[List[Dict]]:
        """Fetches complaint category distribution."""
        conn = self.connect()  # Establish a new connection
        if not conn:
            return None
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT complaint_category AS category, COUNT(*) AS count
                    FROM complaints
                    GROUP BY complaint_category
                    ORDER BY count DESC;
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching complaint categories: {e}")
            return None
        finally:
            conn.close()  # Ensure connection is closed


    # def get_urgency_priority(self) -> List[Dict]:
    #     """Fetches urgency vs priority scores."""
    #     conn = self.connect()  # ✅ Call the connection method correctly
    #     if not conn:
    #         return []  # ✅ Return an empty list instead of None

    #     try:
    #         with conn.cursor(cursor_factory=RealDictCursor) as cursor:  # ✅ Use `conn` instead of `self.conn`
    #             cursor.execute("""
    #                 SELECT urgency_score, priority_score
    #                 FROM complaints;
    #             """)
    #             results = cursor.fetchall()
    #             return results if results else []  # ✅ Ensure a list is always returned
    #     except Exception as e:
    #         print(f"Error fetching urgency vs priority: {e}")
    #         return []  # ✅ Return an empty list on error
    #     finally:
    #         conn.close()  # ✅ Close the connection


    def get_resolution_time(self) -> List[Dict]:
        """Fetches complaint resolution time along with created_at and scheduled_callback timestamps."""
        conn = self.connect()
        if not conn:
            return []  # Ensure an empty list is returned if connection fails

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        created_at, 
                        scheduled_callback, 
                        EXTRACT(EPOCH FROM (scheduled_callback - created_at)) / 3600 AS resolution_time
                    FROM complaints
                    WHERE scheduled_callback IS NOT NULL;
                """)
                results = cursor.fetchall()

                # Convert datetime fields to ISO 8601 strings
                for row in results:
                    row["created_at"] = row["created_at"].isoformat()
                    row["scheduled_callback"] = row["scheduled_callback"].isoformat()

                return results if results else []  # Ensure we always return a list
        except Exception as e:
            print(f"Error fetching resolution times: {e}")
            return []
        finally:
            conn.close()  # Ensure the connection is closed




    def get_politeness_resolution(self) -> List[Dict]:
        """Fetch politeness score vs resolution status."""
        conn = self.connect() 
        if not conn:
            return []  

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT politeness_score, (status = 'Resolved') AS resolved
                    FROM complaints;
                """)
                results = cursor.fetchall()
                return results if results else []  
        except Exception as e:
            print(f"Error fetching politeness vs resolution: {e}")
            return [] 
        finally:
            conn.close() 
            
    def get_status_distribution(self) -> List[Dict]:
        """Fetches the count of complaints based on status (open, closed, etc.)."""
        conn = self.connect()
        if not conn:
            return []

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT status, COUNT(*) AS count
                    FROM complaints
                    GROUP BY status
                    ORDER BY count DESC;
                """)
                results = cursor.fetchall()
                return results if results else []
        except Exception as e:
            print(f"Error fetching status distribution: {e}")
            return []
        finally:
            conn.close()
            
    def get_past_complaints_vs_urgency(self) -> List[Dict]:
        """Fetches past complaint count vs urgency score for a bubble chart."""
        conn = self.connect()
        if not conn:
            return []

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT past_count, priority_score
                    FROM complaints
                    WHERE past_count IS NOT NULL AND priority_score IS NOT NULL;
                """)
                results = cursor.fetchall()
                return results if results else []
        except Exception as e:
            print(f"Error fetching past complaints vs urgency: {e}")
            return []
        finally:
            conn.close()
            
    def get_priority_vs_resolution_speed(self) -> List[Dict]:
        """Fetches priority score vs resolution speed (time difference in hours)."""
        conn = self.connect()
        if not conn:
            return []

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        priority_score, 
                        EXTRACT(EPOCH FROM (scheduled_callback - created_at)) / 3600 AS scheduling_time 
                    FROM complaints
                    WHERE scheduled_callback IS NOT NULL ;
                """)
                results = cursor.fetchall()
                return results if results else []
        except Exception as e:
            print(f"Error fetching priority vs resolution speed: {e}")
            return []
        finally:
            conn.close()
            
    def get_transcripts(self) -> Optional[List[Dict[str, any]]]:
        """
        Fetches phone_number, call_transcript, and called_at from the transcripts table.

        Returns:
            A list of dictionaries containing the retrieved data, or None if an error occurs.
        """
        connection = self.connect()
        if not connection:
            return None

        try:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                query = "SELECT phone_number, call_transcript, called_at FROM transcripts;"
                cursor.execute(query)
                results = cursor.fetchall()
            return results
        except Exception as e:
            print(f"Error fetching transcripts: {e}")
            return None
        finally:
            connection.close()