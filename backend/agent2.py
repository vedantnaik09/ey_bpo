from __future__ import annotations
import os
import asyncio
import logging
import subprocess
from datetime import datetime
from time import perf_counter
from dotenv import load_dotenv
from livekit import rtc, api
from livekit.agents import AutoSubscribe, JobContext
from livekit.plugins import openai
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from call_agent import resolve_db
from typing import Annotated

import subprocess
import psycopg2
from psycopg2 import sql
import asyncio
import logging
from livekit.agents.multimodal import MultimodalAgent
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero

# Load environment variables
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

# Initialize environment variables
outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
class DatabaseManager:
    def __init__(self):
        load_dotenv(".env.local")
        
        # Retrieve database connection parameters from environment
        self.connection_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        self.connection = None

    def connect(self):
        """Establish a connection to the database."""
        if self.connection is None:
            self.connection = psycopg2.connect(**self.connection_params)
        return self.connection.cursor()

    def get_complaint_details(self, phone_number: str) -> dict:
        """Fetch the complaint details from the database using the phone number."""
        cursor = self.connect()
        query = sql.SQL("SELECT customer_name, complaint_description ,knowledge_base_solution, created_at FROM complaints WHERE customer_phone_number = %s")
        cursor.execute(query, (phone_number,))
        result = cursor.fetchone()

        if result:
            name, complaint,solution, complaint_time = result
            return {"name": name, "complaint": complaint, "solution":solution,"time": complaint_time}
        else:
            return {"name": "Unknown", "complaint": "No complaint found", "time": "Unknown"}
    def update_complaint_status(self, phone_number: str, status: str,complaint_description:str):
        """Update the complaint status from 'pending' to 'resolved'."""
        cursor = self.connect()
        query = sql.SQL("UPDATE complaints SET status = %s WHERE customer_phone_number = %s and complaint_description = %s")
        cursor.execute(query, (status, phone_number,complaint_description))
        self.connection.commit()
        logger.info(f"Complaint status for {phone_number} updated to {status}")

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
    def get_solution(self,phone_number):
        try:
            cursor=self.connect()
            sql_command = "SELECT knowledge_base_solution FROM your_table_name WHERE customer_phone_number = %s"

        # Execute the SQL command with the phone number as a parameter
            cursor.execute(sql_command, (phone_number,))

            # Fetch the result (assuming there's only one result)
            solution = cursor.fetchone()
            return solution
        except Exception as e:
            print("Error fetching solution for phone number {}: {}".format(phone_number, e))

# Initialize DatabaseManager (assuming you have this from previous code)
db_manager = DatabaseManager()

async def start_recording(room: rtc.Room):
    """Start recording the room and return the recording URL."""
    recording = await room.recording.create(
        api.CreateRecordingRequest(
            recording_layout=api.RecordingLayout.SINGLE,
            media_mode=api.RecordingMediaMode.RECORD_ALL,
        )
    )
    return recording.url

async def stop_recording(room: rtc.Room, recording_url: str):
    """Stop the recording and download the file."""
    await room.recording.stop()
    
    # Download the MP4 file
    response = await api.download_file(recording_url)
    
    # Create recordings directory
    os.makedirs("recordings", exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"recordings/call_recording_{timestamp}.mp4"
    
    # Save the file locally
    with open(file_path, "wb") as f:
        f.write(response)
    
    logger.info(f"Recording saved as {file_path}")
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    global outbound_trunk_id
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Start system audio recording
    recording_info = await start_recording()

    user_identity = "phone_user"
    phone_number = ctx.job.metadata
    logger.info(f"Dialing {phone_number} to room {ctx.room.name}")

    # Read complaint details from the database
    complaint_details = db_manager.get_complaint_details(phone_number)
    logger.info(f"User complaint details: {complaint_details}")

    instructions = (
        f"You are a BPO client complaint resolver agent for a broadband company called Bharat Telecom. "
        f"The customer's name is {complaint_details['name']}. The complaint is {complaint_details['complaint']}. "
        f"The time of the complaint is {complaint_details['time']}. Resolve their complaint and provide assistance as needed."
    )

    # Call the user and start the interaction
    await ctx.api.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=outbound_trunk_id,
            sip_call_to=phone_number,
            participant_identity=user_identity,
        )
    )

    participant = await ctx.wait_for_participant(identity=user_identity)
    run_multimodal_agent(ctx, participant, instructions)

    start_time = perf_counter()
    while perf_counter() - start_time < 30:
        call_status = participant.attributes.get("sip.callStatus")
        if call_status == "active":
            logger.info("User has picked up")
            return
        elif call_status == "hangup":
            logger.info("User hung up, exiting job")
            break
        await asyncio.sleep(0.1)

    logger.info("Session timed out, exiting job")
    
    # Stop system audio recording
    stop_recording(recording_info)
    ctx.shutdown()
class CallActions(llm.FunctionContext):
    """
    Detect user intent and perform actions
    """

    def __init__(
        self, *, api: api.LiveKitAPI, participant: rtc.RemoteParticipant, room: rtc.Room
    ):
        super().__init__()

        self.api = api
        self.participant = participant
        self.room = room
       

    async def hangup(self):
        try:
            await self.api.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=self.room.name,
                    identity=self.participant.identity,
                )
            )
        except Exception as e:
            logger.info(f"Received error while ending call: {e}")

    @llm.ai_callable()
    async def end_call(self):
        """Called when the user wants to end the call"""
        logger.info(f"Ending the call for {self.participant.identity}")
        await self.hangup()

    @llm.ai_callable()
    async def resolve_complaint(self, complaint: Annotated[str, "Call this function to update the status of the complaint of the user "]):
        """Called to resolve a user's complaint by providing relevant information."""
        phone_number = self.participant.identity 
        complaint_details=db_manager.get_complaint_details(phone_number)
        complaint_description=complaint_details['complaint']
        logger.info(f"Resolving complaint for {self.participant.identity}: {complaint}")
        
        # Update the complaint status in the database to "resolved"
         # Assuming the participant identity is the phone number
        db_manager.update_complaint_status(phone_number, "resolved",complaint_description)
        
        return "Your complaint has been noted. We will resolve it promptly."

    @llm.ai_callable()
    async def search_knowledge_base(self, query: Annotated[str, "Query to search in the knowledge base the question user is asking on the call you want to check"]):
        """Called to search the knowledge base for user queries."""
        logger.info(f"Searching knowledge base for query: {query}")
        
        # Read the knowledge base from the file
        solution = resolve_db(query)
        
        # Simulate a search by checking if any knowledge base entry matches the complaint
        
        
        return str(solution)
    
    @llm.ai_callable()
    async def confirm_resolution(self):
        """Called to confirm the resolution of the user's complaint."""
        logger.info(f"Confirming resolution for {self.participant.identity}")
        return "We have resolved your issue. Please let us know if there's anything else."

    @llm.ai_callable()
    async def detected_answering_machine(self):
        """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting."""
        logger.info(f"Detected answering machine for {self.participant.identity}")
        await self.hangup()

def run_multimodal_agent(ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str):
    logger.info("Starting multimodal agent")
    model = openai.realtime.RealtimeModel(
        instructions=instructions,
        modalities=["audio", "text"],
    )
    agent = MultimodalAgent(
        model=model,
        fnc_ctx=CallActions(api=ctx.api, participant=participant, room=ctx.room),
    )
    agent.start(ctx.room, participant)

# Main execution
if __name__ == "__main__":
    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        raise ValueError(
            "SIP_OUTBOUND_TRUNK_ID is not set. Please follow the guide at https://docs.livekit.io/agents/quickstarts/outbound-calls/ to set it up."
        )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="outbound-caller",
            prewarm_fnc=prewarm,
        )
    )