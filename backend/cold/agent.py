from __future__ import annotations
import subprocess
import psycopg2
from psycopg2 import sql
import asyncio
import logging
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
import pandas as pd
from demo import send_whatsapp
from livekit.agents.multimodal import MultimodalAgent
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero

# Load environment variables
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

def get_user_info(phone_number, file_path='data.csv'):
    try:
        df = pd.read_csv(file_path)
        user = df[df['Phone Number'] == phone_number]
        
        if not user.empty:
            # Extract Name and Person Info
            return {
                'Name': user.iloc[0]['Name'],
                'Person Info': user.iloc[0]['Person Info']
            }
        return None  # Return None if no match is found
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
    except KeyError as e:
        print(f"Error: Missing column in CSV file - {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None


async def entrypoint(ctx: JobContext):
    global outbound_trunk_id
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    data = pd.read_csv("data.csv")
    user_identity = "phone_user"
    phone_number = ctx.job.metadata
    
    
    logger.info(f"Dialing {phone_number} to room {ctx.room.name}")
    result = get_user_info(phone_number)
    customer_name = result['Name']
    customer_info = result['Person Info']
    
    instructions = (
        f"You are cold caller advertiser for a clothing company called Powerlook"
        f"You have to advertise the discount for Republic Day where there is 15% discount above 1500rs shopping"
        f"You have to speak in Hindi"
        f"You have to be a entertaining advertiser and make complitments to the user so that he will want to talk to u more "
        f"The customers name is {customer_name} and this is some info that will help u pitch {customer_info}"
        f"give remark of the call using function calling  before ending the call"
        "make sure to update_call_status using function calling before ending the call"
    )
    
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
    ctx.shutdown()

class CallActions(llm.FunctionContext):
    """
    Detect user intent and perform actions
    """

    def __init__(self, *, api: api.LiveKitAPI, participant: rtc.RemoteParticipant, room: rtc.Room):
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
    import pandas as pd

    def update_call_status(self,customer_name, file_path='data.csv'):
        try:
            # Load the CSV file into a DataFrame
            df = pd.read_csv(file_path)

            # Find the row where the Name matches the customer_name
            if customer_name in df['Name'].values:
                # Update the 'Call Status' to 'called' for the matched row
                df.loc[df['Name'] == customer_name, 'Call Status'] = 'called'
                
                # Save the updated DataFrame back to the CSV file
                df.to_csv(file_path, index=False)
                print(f"Call status updated to 'called' for {customer_name}.")
                return "success"
            else:
                print(f"Customer {customer_name} not found in the data.")
                
        
        except FileNotFoundError:
            print(f"Error: The file {file_path} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")
    def update_remarks(self,customer_name, remark, file_path='data.csv'):
        try:
            # Load the CSV file into a DataFrame
            df = pd.read_csv(file_path)

            # Find the row where the Name matches the customer_name
            if customer_name in df['Name'].values:
                # Update the 'Remarks' column for the matched row
                df.loc[df['Name'] == customer_name, 'Remarks'] = remark
                
                # Save the updated DataFrame back to the CSV file
                df.to_csv(file_path, index=False)
                print(f"Remark added for {customer_name}.")
                return "success"
            else:
                print(f"Customer {customer_name} not found in the data.")
        
        except FileNotFoundError:
            print(f"Error: The file {file_path} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")
    def update_callback(self,customer_name, callback_date, file_path='data.csv'):
        try:
            # Load the CSV file into a DataFrame
            df = pd.read_csv(file_path)

            # Find the row where the Name matches the customer_name
            if customer_name in df['Name'].values:
                # Update the 'Next Follow-up Date' column for the matched row
                df.loc[df['Name'] == customer_name, 'Next Follow-up Date'] = callback_date
                
                # Save the updated DataFrame back to the CSV file
                df.to_csv(file_path, index=False)
                print(f"Callback date added for {customer_name}.")
                return "success"
            else:
                print(f"Customer {customer_name} not found in the data.")
        
        except FileNotFoundError:
            print(f"Error: The file {file_path} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")


# Example usage:


    @llm.ai_callable()
    async def end_call(self):
        """Called when the user wants to end the call"""
        logger.info(f"Ending the call for {self.participant.identity}")
        await self.hangup()

    @llm.ai_callable()
    async def offer_sale_details(self):
        """Called when the user asks for more details about the sale"""
        logger.info(f"Offering sale details to {self.participant.identity}")
        return "Our sale includes discounts on dresses, shirts, pants, and accessories. You can save up to 50% off on selected items. Hurry, the sale is for a limited time only!"

    @llm.ai_callable()
    async def thank_user(self):
        """Called to thank the user for their time"""
        logger.info(f"Thanking {self.participant.identity}")
        return "Thank you for your time! We hope to see you soon in our store. Have a great day!"
    
    @llm.ai_callable()
    async def send_whatsapp(self):
        """Called to send the sale details to user through whatsapp"""
        logger.info(f"Sending sale details to {self.participant.identity}")
        print(self.participant.identity)
        result=send_whatsapp("+917769915068")
        if result=="success":
            logging.info(f"the details have been sent to {self.participant.identity}")
            return "The details have been sent to {self.participant.identity"
        else:
            return "could not send the details to {self.participant.identity}"
        
    @llm.ai_callable()
    def update_status(self,customer_name:Annotated[str,"The name of the customer initially provided in the instructions"]):
        """Call this to update the call status of the customer. Always do this before ending the call."""
        logger.info(f"Updating the call status of {self.participant.identity}")
        result=self.update_call_status(customer_name)
        if result=="success":
         return "call status has been updated"
    
    @llm.ai_callable()
    async def add_remark(self,customer_name:Annotated[str,"The name of the customer initially provided in the instructions"],remark:Annotated[str,"The review of the call how was the experience how was the customer"]):
        """Call this function always before ending the call to give a review of the call"""
        logger.info(f"Updating the call status of {self.participant.identity}")
        result=self.update_remarks(customer_name,remark)
        if result=="success":
         return "call status has been updated"
    
    @llm.ai_callable()
    async def add_callback(self,customer_name:Annotated[str,"The name of the customer initially provided in the instructions"],callback_date:Annotated[str,"The date when the customer wants you to callback"]):
        """Call this function when the user is busy or wants to talk some other time ask him the preferred date and time"""
        logger.info(f"Adding a callback for {self.participant.identity}")
        result= self.update_callback(customer_name,callback_date)
        if result=="success":
         return "callback date has been added"
    
        
        
        

def run_multimodal_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str
):
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
            agent_name="outbound-caller",
            prewarm_fnc=prewarm,
        )
    )
