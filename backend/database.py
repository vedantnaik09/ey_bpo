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

        self.connection_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }

    def connect(self) -> Optional[psycopg2.extensions.connection]:
        """Connect to PostgreSQL; returns None if connection fails."""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            print(f"Error connecting to database: {e}")
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
                    CREATE TABLE IF NOT EXISTS complaints (
                        complaint_id SERIAL PRIMARY KEY,
                        customer_name VARCHAR(255) NOT NULL,
                        customer_phone_number VARCHAR(50) NOT NULL,
                        complaint_description TEXT NOT NULL,
                        sentiment_score FLOAT,
                        urgency_score FLOAT,
                        priority_score FLOAT,
                        status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        scheduled_callback TIMESTAMP,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        knowledge_base_solution TEXT
                    );
                """)

            conn.commit()
            print("Tables ensured (created if not existed).")
        except Exception as e:
            print(f"Error creating tables: {e}")
        finally:
            conn.close()

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
                        """,
                        (name, phone, description, sentiment, urgency, priority_score, 'pending')
                    )

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
        """Automatically schedule callback based on priority and availability."""
        start_date = datetime.now()

        if priority_score >= 0.7:      # High priority
            max_delay = timedelta(days=1)   # Within 24 hours
        elif priority_score >= 0.4:   # Medium priority
            max_delay = timedelta(days=2)   # Within 48 hours
        else:                         # Low priority
            max_delay = timedelta(days=5)   # Within 5 days

        end_date = start_date + max_delay

        # Generate 30-min timeslots within business hours (9-17), excluding weekends
        time_slots = []
        current = start_date
        while current <= end_date:
            if current.weekday() not in [5, 6] and 9 <= current.hour < 17:
                time_slots.append(current)
            current += timedelta(minutes=30)

        # Find the first free slot
        for slot in time_slots:
            cursor.execute("""
                SELECT 1 FROM complaints
                WHERE scheduled_callback = %s
            """, (slot,))
            if cursor.fetchone() is None:
                # Schedule the complaint
                cursor.execute("""
                    UPDATE complaints
                    SET scheduled_callback = %s
                    WHERE complaint_id = %s
                """, (slot, complaint_id))
                return

        print("No available slots found within the specified time frame.")

    def reschedule_callback(self, complaint_id: int, new_time: datetime) -> bool:
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Check if slot is already taken
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

    def get_scheduled_callbacks(self, date: Optional[str] = None) -> pd.DataFrame:
        """Get all scheduled callbacks for a specific date (YYYY-MM-DD)."""
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
                params = None
                if date:
                    query += " AND DATE(scheduled_callback) = %s"
                    params = (date,)

                return pd.read_sql_query(query, conn, params=params)
            finally:
                conn.close()
        return pd.DataFrame()

    def get_complaints(self) -> pd.DataFrame:
        """Fetch all complaints, ordered by priority_score DESC then created_at DESC."""
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
        """
        Returns:
          - total number of complaints
          - number of pending complaints
          - average priority_score
        """
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
        return (0, 0, 0.0)

    def resolve_complaint(self, complaint_id: int) -> bool:
        """Toggle complaint status between 'pending' and 'resolved'."""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # Check current status
                    cursor.execute("""
                        SELECT status
                        FROM complaints
                        WHERE complaint_id = %s
                    """, (complaint_id,))
                    row = cursor.fetchone()
                    if not row:
                        print(f"No complaint found with ID {complaint_id}")
                        return False

                    current_status = row[0]
                    new_status = 'pending' if current_status == 'resolved' else 'resolved'

                    # Update
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
        """Auto-schedule all unscheduled, pending complaints (high priority first)."""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT complaint_id, priority_score
                        FROM complaints
                        WHERE scheduled_callback IS NULL
                          AND status = 'pending'
                        ORDER BY priority_score DESC, created_at ASC
                    """)
                    complaints = cursor.fetchall()

                    for c_id, p_score in complaints:
                        self._auto_schedule_callback(cursor, c_id, p_score)

                conn.commit()
                return True
            except Exception as e:
                print(f"Error scheduling existing complaints: {e}")
                return False
            finally:
                conn.close()
        return False

    def upload_solution(self, phone_number: str, solution: str) -> bool:
        """Updates the knowledge_base_solution for a given phone number."""
        conn = self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE complaints
                        SET knowledge_base_solution = %s
                        WHERE customer_phone_number = %s
                    """, (solution, phone_number))
                conn.commit()
                print("Solution updated successfully.")
                return True
            except Exception as e:
                print(f"Error uploading solution: {e}")
                return False
            finally:
                conn.close()
        return False

    def upsert_user(self, email: str, role: str = "employee") -> bool:
        """
        Checks if user exists by email. If not, inserts a new user with 'role'.
        Returns True if successful, False otherwise.
        """
        conn = self.connect()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                # Check if user already exists
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
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
                else:
                    # Optionally update or just skip
                    print(f"User with email {email} already exists. Skipping creation.")

                conn.commit()
                return True
        except Exception as e:
            print(f"Error upserting user: {e}")
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
