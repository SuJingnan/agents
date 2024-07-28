import asyncio

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import silero,openai
from livekit.plugins.azure import TTS, STT
from alibabacloud.llm import LLM

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "你是一个语音助手"
        ),
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=STT(languages=["zh-CN","en-US"]), # Speech-to-Text
        llm=openai.LLM(base_url="http://localhost:3001/v1",model="qwen2:7b"),
        tts=TTS(voice="zh-CN-XiaoxiaoNeural"), # Text-to-Speech
        chat_ctx=initial_ctx,
    )
    assistant.start(ctx.room)

    await asyncio.sleep(1)
    await assistant.say("你好啊，大帅哥", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
