import logging
import json
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import  groq, deepgram, silero, turn_detector
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

# Example function for function calling
def get_weather(location: str):
    """Mock function to get weather data."""
    return f"The weather in {location} is sunny with 28°C."

# Define available functions
available_functions = {
    "get_weather": get_weather
}

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit with function calling capabilities. "
            "You should respond concisely and use function calls when appropriate."
        ),
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    # Define Groq LLM with function calling
    groq_llm = groq.LLM(model="mixtral-8x7b", function_calling=True)

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),
        llm=groq_llm,
        tts=cartesia.TTS(),
        turn_detector=turn_detector.EOUModel(),
        min_endpointing_delay=0.5,
        max_endpointing_delay=5.0,
        chat_ctx=initial_ctx,
    )

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)

    @agent.on("function_call")
    async def on_function_call(request):
        """Handles function calls from the LLM."""
        function_name = request.function.name
        arguments = json.loads(request.function.arguments)

        if function_name in available_functions:
            result = available_functions[function_name](**arguments)
            await agent.respond_with_function_result(request, result)
        else:
            await agent.respond_with_function_result(request, f"Function '{function_name}' not found.")

    agent.start(ctx.room, participant)

    await agent.say("Hey, how can I help you today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
