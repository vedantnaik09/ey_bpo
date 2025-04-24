from __future__ import annotations
from aiofile import async_open
from datetime import datetime
import asyncio
import logging
import asyncpg
from dotenv import load_dotenv
import json
import os
from time import perf_counter
from typing import Annotated
from livekit import rtc, api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from whatsapp import send_whatsapp
from asyncpg import create_pool
from psycopg2 import sql
import psycopg2
from call_agent import resolve_db
from livekit.agents.multimodal import MultimodalAgent
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero
from typing import Optional


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
        
    def connect(self) -> Optional[psycopg2.extensions.connection]:
            try:
                return psycopg2.connect(**self.connection_params)
            except Exception as e:
                print(f"Error connecting to database in database.py: {e}")
                return None

    def get_complaint_details(self, phone_number: str) -> dict:
        """Fetch the complaint details from the database using the phone number."""
        conn = self.connect()  # Get connection first
        if conn:
            try:
                with conn.cursor() as cursor:  # Create cursor from connection
                    query = """SELECT customer_name, complaint_description, 
                                    knowledge_base_solution, created_at 
                            FROM complaints 
                            WHERE customer_phone_number = %s"""
                    cursor.execute(query, (phone_number,))
                    result = cursor.fetchone()

                if result:
                    name, complaint, solution, complaint_time = result
                    return {"name": name, "complaint": complaint, 
                            "solution": solution, "time": complaint_time}
                else:
                    return {"name": "Unknown", "complaint": "No complaint found", 
                            "time": "Unknown"}
            finally:
                conn.close()  # Ensure connection is closed
        return {"name": "Unknown", "complaint": "Connection failed", "time": "Unknown"}
        
    def update_complaint_status(self, phone_number: str, status: str):
        """Update the complaint status from 'pending' to 'resolved'."""
        conn= self.connect()
        if conn:
            try:
                with conn.cursor() as cursor:
                 query = sql.SQL("UPDATE complaints SET status = %s WHERE customer_phone_number = %s ")
                
                 cursor.execute(query, (status, phone_number))
                 conn.commit()
            except Exception as e:
                print(f"Error updating complaint status for {phone_number}: {e}")
            
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
        


# Initialize DatabaseManager
db_manager = DatabaseManager()




# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")
os.environ["OPENAI_API_KEY"]="Put openai key"

logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

async def entrypoint(ctx: JobContext):
    
    global _default_instructions, outbound_trunk_id
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    user_identity = "phone_user"
    # the phone number to dial is provided in the job metadata
    phone_number = ctx.job.metadata
    logger.info(f"dialing {phone_number} to room {ctx.room.name}")
    complaint_details = db_manager.get_complaint_details(phone_number)
    print(f"the name  of the user is {complaint_details['name']}")

    # look up the user's phone number and appointment details
    instructions = (
        f"You are a BPO client complaint resolver agent for a broadband company called Bharat Telecom. Your interface with the user will be voice. "
        f"You have to talk in fluent English"
        f"The customer's name is {complaint_details['name']}. the complaint is {complaint_details['complaint']}. the time of the complaint is {complaint_details['time']}.Resolve their complaint and provide assistance as needed."
        f"the Initial Solution provided by the database is {complaint_details['solution']}."
        "You have to give introduction about urself and tell the problem and solution at start of the call"
        f"if user asks for questions whose answer is not mentioned in the initial solution use read knowledge base function tool  to get entire knowledge base and before searching tell him to please wait "
        "provide this solution and listen to their queries"
        "You can look into knowledge base to find solution for the user's queries"
        f"before ending the call do save the entire conversation in the database"
        f"also send whatsapp message of the complaint or enquiry details at the end"
        f"Also change the status of the complaint if the complaint has been resolved or if the user wants human assistance instead of AI"
        f"do end the call automatically using end_call function at the end when the conversation has been logged"
        """This are the tasks u have to do sequentially
        1. Check for knowledge base for user queries if you dont know about it 
        2. Change the update to 1. resolved if u have resolved the complained 2.Human Assistance if the user needs human assistance or keep unchanged if the complaint is still unresolved before ending the call
        3.Send Whatsapp message of the confirmation of the complaint and complaint details before ending the call
        4.Log the conversation into the database before ending the call(VERY IMPORTANT)
        5.End the call if you feel user wants to end the call
        MAKE SURE TO FOLLOW THIS SEQUENCE OF FUNCTION CALLING """
        
    )

    # `create_sip_participant` starts dialing the user
    await ctx.api.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=outbound_trunk_id,
            sip_call_to=phone_number,
            participant_identity=user_identity,
        )
    )

    # a participant is created as soon as we start dialing
    participant = await ctx.wait_for_participant(identity=user_identity)

    # start the agent, either a VoicePipelineAgent or MultimodalAgent
    # this can be started before the user picks up. The agent will only start
    # speaking once the user answers the call.
    # run_voice_pipeline_agent(ctx, participant, instructions)
    run_voice_pipeline_agent(ctx, participant, instructions)

    # in addition, you can monitor the call status separately
    start_time = perf_counter()
    while perf_counter() - start_time < 30:
        call_status = participant.attributes.get("sip.callStatus")
        if call_status == "active":
            logger.info("user has picked up")
            return
        elif call_status == "automation":
            # if DTMF is used in the `sip_call_to` number, typically used to dial
            # an extension or enter a PIN.
            # during DTMF dialing, the participant will be in the "automation" state
            pass
        elif participant.disconnect_reason == rtc.DisconnectReason.USER_REJECTED:
            logger.info("user rejected the call, exiting job")
            break
        elif participant.disconnect_reason == rtc.DisconnectReason.USER_UNAVAILABLE:
            logger.info("user did not pick up, exiting job")
            break
        await asyncio.sleep(0.1)

    logger.info("session timed out, exiting job")
    ctx.shutdown()


class CallActions(llm.FunctionContext):
    """
    Detect user intent and perform actions
    """

    def __init__(
        self, *, api: api.LiveKitAPI, participant: rtc.RemoteParticipant, room: rtc.Room,phone_number
    ):
        super().__init__()

        self.api = api
        self.participant = participant
        self.room = room
        self.phone_number=phone_number

    async def hangup(self):
        try:
            await self.api.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=self.room.name,
                    identity=self.participant.identity,
                )
            )
        except Exception as e:
            # it's possible that the user has already hung up, this error can be ignored
            logger.info(f"received error while ending call: {e}")
    async def _store_transcript_in_db(self, phone_number: str, transcript: str) -> bool:
        """Async database operation to store the transcript"""
        try:
            # Use asyncpg for proper async support
            conn = await asyncpg.connect(**db_manager.connection_params)
            await conn.execute('''
                INSERT INTO user_transcripts (phone_number, call_transcript, created_at)
                VALUES ($1, $2, NOW())
            ''', phone_number, transcript)
            await conn.close()
            return True
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return False
            
    @llm.ai_callable()
    async def change_status(self, status: Annotated[str, """The status can be a flag u want to give to the complaint it can be 1.Resolved if u have succesfully resolved the issue
                                                    2.Human Assistance if the complaint needs human assistance and cant be resolved by AI alone. By default the status is pending u can also leave it in pending """]):
        """Call this function to change the status of complaint """
        phone_number = self.phone_number
        complaint_details=db_manager.get_complaint_details(phone_number)
        complaint_description=complaint_details['complaint']
        logger.info(f"Resolving complaint for {self.phone_number}")
        
        # Update the complaint status in the database to "resolved"
         # Assuming the participant identity is the phone number
        db_manager.update_complaint_status(phone_number, status)
        
        return "Your complaint has been noted. We will resolve it promptly."

    @llm.ai_callable()
    async def end_call(self):
        """Called when the user wants to end the call"""
        logger.info(f"ending the call for {self.phone_number}")
        await self.hangup()

    @llm.ai_callable()
    async def search_knowledge_base(self, query: Annotated[str, "Query to search in the knowledge base the question user is asking on the call you want to check"]):
        """Called to search the knowledge base for user queries."""
        logger.info(f"Searching knowledge base for query: {query}")
        
        # Read the knowledge base from the file
        solution = resolve_db(query)
        # Simulate a search by checking if any knowledge base entry matches the complain
        return str(solution)


    @llm.ai_callable()
    async def detected_answering_machine(self):
        """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
        logger.info(f"detected answering machine for {self.participant.identity}")
        await self.hangup()

    @llm.ai_callable()
    async def log_conversation(
        self, 
        conversation_transcription: Annotated[
            str, 
            """Complete Exact transcript of the conversation in chronological order. Format: 'Agent: ... |
            User: ...|
            Agent:...' """]):
            """Called to permanently save the full conversation transcript before ending the call."""
            phone_number = self.phone_number
            formatted_transcript = "\n".join(
            [line.strip() for line in conversation_transcription.split("|")]
            )
            conn = db_manager.connect()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        # 1. Use %s placeholders instead of $1, $2
                        # 2. Pass parameters as a tuple
                        cursor.execute("""INSERT INTO transcripts (phone_number, call_transcript, called_at)
                        VALUES (%s, %s, NOW())""", (phone_number, formatted_transcript))
                        conn.commit()
                        return "the conversation has been updated"
    
                except Exception as e:
                    logger.error(f"Error saving transcript: {str(e)}")
                    return "Error saving conversation log"
                finally:
                    conn.close()
                    
    @llm.ai_callable()
    async def send_whatsapp(self,confirmation_message:Annotated[str,"Confirmation message that has to be sent to the user regarding the registeration of the complaint"]):
        """Send confirmation message to the user"""
        logger.info(f"Sending  details to {self.phone_number}")
        print(self.participant.identity)
        result=send_whatsapp(self.phone_number,confirmation_message)
        if result=="success":
            logging.info(f"the details have been sent to {self.participant.identity}")
            return "The details have been sent to {self.participant.identity"
        else:
            return "could not send the details to {self.participant.identity}"
                
        
    


def run_voice_pipeline_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str
):
    logger.info("starting voice pipeline agent")

    initial_ctx = llm.ChatContext().append(
        role="system",
        text=instructions,
    )

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-2-phonecall",api_key=os.getenv("DEEPGAM_API_KEY")),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
        fnc_ctx=CallActions(api=ctx.api, participant=participant, room=ctx.room,phone_number=ctx.job.metadata),
    )

    agent.start(ctx.room, participant)


def run_multimodal_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str
):
    logger.info("starting multimodal agent")

    model = openai.realtime.RealtimeModel(
        instructions=instructions,
        modalities=["audio", "text"],
    )
    agent = MultimodalAgent(
        model=model,
        fnc_ctx=CallActions(api=ctx.api, participant=participant, room=ctx.room),
    )
    agent.start(ctx.room, participant)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        raise ValueError(
            "SIP_OUTBOUND_TRUNK_ID is not set. Please follow the guide at https://docs.livekit.io/agents/quickstarts/outbound-calls/ to set it up."
        )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # giving this agent a name will allow us to dispatch it via API
            # automatic dispatch is disabled when `agent_name` is set
            agent_name="outbound-caller",
            # prewarm by loading the VAD model, needed only for VoicePipelineAgent
            prewarm_fnc=prewarm,
        )
    )
