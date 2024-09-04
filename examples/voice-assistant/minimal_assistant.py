import asyncio
import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
from livekit.plugins.azure import TTS, STT
load_dotenv()
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)
def get_case_by_id(caseid):
    
    return "你是一个智能客服的教练，你正在测验客服的技能水平，你现在假设是一个奔驰车主，目前的问题是汽车无法启动了，请你打电给给客服寻求帮助，你通过这个求助电话过程中测试一下客服的服务水平，结束测验后，并给出评分。你每次回复或者提问字数尽量控制在20字以内。"
# def get_case_by_id(caseid):
#     url = "https://api.example.com/cases/" + caseid
#     response = requests.get(url)
#     if response.status_code == 200:
#         case_data = response.json()
#         return case_data["description"]
#     else:
#         return "Failed to retrieve case data"
async def entrypoint(ctx: JobContext):
    

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("starting entrypoint")

    caseid= str(list(ctx.room.remote_participants.values())[0].metadata)

    logger.info("caseid: " + caseid)
    text = get_case_by_id(caseid)
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            text
        ),
    )

    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=STT(languages=["zh-CN","en-US"]), # Speech-to-Text
        llm=openai.LLM.with_ollama(base_url="http://localhost:11434/v1", model="gemma2:27b"),
        tts=TTS(voice="zh-CN-XiaoxiaoNeural"), # Text-to-Speech
        chat_ctx=initial_ctx,
    )
    assistant.start(ctx.room)

    # listen to incoming chat messages, only required if you'd like the agent to
    # answer incoming messages from Chat
    chat = rtc.ChatManager(ctx.room)

    async def answer_from_text(txt: str):
        chat_ctx = assistant.chat_ctx.copy()
        chat_ctx.append(role="user", text=txt)
        stream = assistant.llm.chat(chat_ctx=chat_ctx)
        await assistant.say(stream)


    @chat.on("message_received")
    def on_chat_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(answer_from_text(msg.message))

    await assistant.say("你好是奔驰客户服务中心吗??", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
