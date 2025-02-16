from __future__ import annotations
import asyncio
import logging
from psycopg2 import sql
import psycopg2
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
from datetime import datetime
from call_agent import resolve_db
from livekit.agents.multimodal import MultimodalAgent
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.openai import stt
from livekit.plugins.deepgram import tts
from whatsapp import send_whatsapp
# from livekit.plugins.elevenlabs import tts
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
        


# Initialize DatabaseManager
db_manager = DatabaseManager()


# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
os.environ['OPENAI_API_KEY']=os.getenv("OPENAI_API_KEY")
os.environ["DEEPGRAM_API_KEY"]=os.getenv('DEEPGRAM_API_KEY')
os.environ["ELEVEN_API_KEY"]=os.getenv('ELEVENLABS_API_KEY')


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
    instructions = (
        f"You are a BPO client complaint resolver agent for a broadband company called Bharat Telecom. Your interface with the user will be voice. "
        f"You have to talk in fluent English"
        f"The customer's name is {complaint_details['name']}. the complaint is {complaint_details['complaint']}. the time of the complaint is {complaint_details['time']}.Resolve their complaint and provide assistance as needed."
        f"the Initial Solution provided by the database is {complaint_details['solution']}."
        f"if user asks for questions whose answer is not mentioned in the initial solution use read knowledge base function tool  to get entire knowledge base and before searching tell him to please wait "
        "provide this solution and listen to their queries"
        f"use function calling to get solution during conversation realtime from the knowledge base"
        f"U should only end the call if the user tells u to or u feel that the conversation has ended"
      
    
        f"Dont speak the things about the function calling and the output ur getting from it "     
    )
    # look up the user's phone number and appointment details
    instructions = (
        instructions
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
        elif call_status == "hangup":
            # user hung up, we'll exit the job
            logger.info("user hung up, exiting job")
            break
        await asyncio.sleep(0.1)

    logger.info("session timed out, exiting job")
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
            # it's possible that the user has already hung up, this error can be ignored
            logger.info(f"received error while ending call: {e}")

    @llm.ai_callable()
    async def end_call(self):
        """Called when the user wants to end the call"""
        logger.info(f"ending the call for {self.participant.identity}")
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
    # @llm.ai_callable()
    # async def flag_for_human(self, complaint: Annotated[str]):
    #     """Called to resolve a user's complaint by providing relevant information."""
    #     phone_number = self.participant.identity 
    #     complaint_details=db_manager.get_complaint_details(phone_number)
    #     complaint_description=complaint_details['complaint']
    #     logger.info(f"Resolving complaint for {self.participant.identity}: {complaint}")
        
    #     # Update the complaint status in the database to "resolved"
    #      # Assuming the participant identity is the phone number
    #     db_manager.update_complaint_status(phone_number, "resolved",complaint_description)
        
    #     return "Your complaint has been noted. We will resolve it promptly."

   
    @llm.ai_callable()
    async def search_knowledge_base(self, query: Annotated[str, "Query to search in the knowledge base the question user is asking on the call you want to check"]):
        """Called to search the knowledge base for user queries."""
        logger.info(f"Searching knowledge base for query: {query}")
        
        # Read the knowledge base from the file
        solution = resolve_db(query)
        # Simulate a search by checking if any knowledge base entry matches the complain
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
        
        
    @llm.ai_callable()
    async def log_conversation(
        self, 
        conversation_transcription: Annotated[
            str, 
            "Complete transcript of the conversation in chronological order. Format: 'Agent: ... | User: ...'"
        ]
    ):
        """Called to permanently save the full conversation transcript before ending the call."""
        try:
            # Process transcript in chunks to avoid blocking
            transcript_chunks = [
                conversation_transcription[i:i+1000] 
                for i in range(0, len(conversation_transcription), 1000)
            ]
            
            for chunk in transcript_chunks:
                await self._log_conversation(chunk)
                
            return "Conversation transcript has been securely archived."
            
        except Exception as e:
            logger.error(f"Conversation logging failed: {e}")
            return "Failed to save conversation transcript."
          
    @llm.ai_callable()
    async def send_whatsapp(self):
        """Send confirmation message to the user"""
        logger.info(f"Sending sale details to {self.participant.identity}")
        print(self.participant.identity)
        result=send_whatsapp(self.participant.identity)
        if result=="success":
            logging.info(f"the details have been sent to {self.participant.identity}")
            return "The details have been sent to {self.participant.identity"
        else:
            return "could not send the details to {self.participant.identity}"
         

def run_voice_pipeline_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str):
    logger.info("starting voice pipeline agent")

    initial_ctx = llm.ChatContext().append(
        role="system",
        text=instructions,
    )

    agent = VoicePipelineAgent(
    vad=ctx.proc.userdata["vad"],
    stt=stt.STT.with_groq(model="whisper-large-v3", language="en"),
    llm=openai.LLM.with_groq(model="llama-3.3-70b-versatile", temperature=0.8),
    tts= tts.TTS(
    model="aura-asteria-en",
    
    ),
    chat_ctx=initial_ctx,
    
    

    )  # Closing parenthesis for VoicePipelineAgent
    agent.start(ctx.room, participant)
    

    # 


# def run_multimodal_agent(
#     ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str
# ):
#     logger.info("starting multimodal agent")

#     model = openai.realtime.RealtimeModel(
#         instructions=instructions,
#         modalities=["audio", "text"],
#     )
#     agent = MultimodalAgent(
#         model=model,
#         fnc_ctx=CallActions(api=ctx.api, participant=participant, room=ctx.room),
#     )
#     agent.start(ctx.room, participant)


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
