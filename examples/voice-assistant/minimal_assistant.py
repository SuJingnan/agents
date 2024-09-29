# import sys
# import os

# # 获取当前脚本所在目录的父目录
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.abspath(os.path.join(current_dir, '../..'))
# livekit_plugins_path = os.path.join(project_root, 'livekit-plugins/livekit-plugins-azure/livekit/plugins/azure')

# # 将 livekit-plugins-azure 目录添加到 sys.path
# sys.path.insert(0, livekit_plugins_path)

import asyncio
import requests
import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant,AssistantTranscriptionOptions
from livekit.plugins import openai, silero
# from tts import TTS  # 修改导入路径
# from stt import STT  # 修改导入路径2
from azure2 import TTS, STT

# from livekit.plugins.azure import TTS  # 修改导入路径
# from livekit.plugins.azure import STT  # 修改导入路径
# from ...livekit.plugins.livekit.plugins.azure import TTS, STT
# from ...livekit.plugins.livekit.plugins.azure import TTS, STT
load_dotenv()
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)
# def get_case_by_id(caseid):
    
    # return "你是一个智能客服的教练，你正在测验客服的技能水平，你现在假设是一个奔驰车主，目前的问题是汽车无法启动了，请你打电给给客服寻求帮助，你通过这个求助电话过程中测试一下客服的服务水平，结束测验后，并给出评分。你每次回复或者提问字数尽量控制在20字以内。"
def get_case_by_id(caseid):
    url = "https://strapi.shougan.net/api/robot-prompts/" + caseid + "?populate=robot_language,robot_type,llm,welcomeMessage"
    response = requests.get(url)
    if response.status_code == 200:
            return response.json()
            # try:
            #     return case_data["data"]["attributes"]["ClassPrompt"]
            # except KeyError:
            #     return "ClassPrompt not found in case data"
    else:
            return "Failed to retrieve case data"

async def entrypoint(ctx: JobContext):
    

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("starting entrypoint")
    caseid= str(list(ctx.room.remote_participants.values())[0].metadata)
    logger.info("caseid: " + caseid)
    assistantTranscriptionOptions = AssistantTranscriptionOptions(
           agent_transcription_speed=50.0,
        )
    if(caseid):
        robot_case = get_case_by_id(caseid)
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=(
                robot_case["data"]["attributes"]["Prompt"]
            ),
        )
        assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=STT(languages=[robot_case["data"]["attributes"]["STTLang"]]), # Speech-to-Text
        # stt=STT(languages=["zh-CN","en-US"]), # Speech-to-Text
        # llm=openai.LLM.with_ollama(base_url="http://localhost:11434/v1", model="qwen2:7b"),
        # llm=openai.LLM.with_azure(model="gpt-4o-mini", azure_endpoint="https://livekit.openai.azure.com/", azure_deployment="livekit-test", api_version="2024-02-15-preview", api_key=""),
        # llm=openai.LLM.with_azure(model="gpt-4o", azure_endpoint="https://livekit.openai.azure.com/", azure_deployment="gpt-4o", api_version="2024-02-15-preview", api_key=""),
        llm=openai.LLM.with_azure(model="gpt-4o", azure_deployment="gpt-4o"),
        tts=TTS(voice=robot_case["data"]["attributes"]["TTSVoice"]), # Text-to-Speech en-US-AndrewMultilingualNeural  zh-CN-XiaohanNeural
        chat_ctx=initial_ctx,
        transcription=assistantTranscriptionOptions
    )
    else:
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=(
                "你是一个助手"
            ),
        )
        assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=STT(languages=["zh-CN"]), # Speech-to-Text
        # stt=STT(languages=["zh-CN","en-US"]), # Speech-to-Text
        # llm=openai.LLM.with_ollama(base_url="http://localhost:11434/v1", model="qwen2:7b"),
        # llm=openai.LLM.with_azure(model="gpt-4o-mini", azure_endpoint="https://livekit.openai.azure.com/", azure_deployment="livekit-test", api_version="2024-02-15-preview", api_key=""),
        # llm=openai.LLM.with_azure(model="gpt-4o", azure_endpoint="https://livekit.openai.azure.com/", azure_deployment="gpt-4o", api_version="2024-02-15-preview", api_key=""),
        llm=openai.LLM.with_azure(model="gpt-4o", azure_deployment="gpt-4o"),
        tts=TTS(voice="zh-CN-XiaohanNeural"), # Text-to-Speech en-US-AndrewMultilingualNeural  zh-CN-XiaohanNeural
        chat_ctx=initial_ctx,
        transcription=assistantTranscriptionOptions
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

    # await assistant.say("AI Coath Connected", allow_interruptions=True,add_to_chat_ctx=False)
    if(caseid):
        welcomeMessage= robot_case["data"]["attributes"]["welcomeMessage"]
        if welcomeMessage:
            await assistant.say(welcomeMessage, allow_interruptions=True)
    else:
        await assistant.say("系统没有获取到Case，请确认URL是否正确", allow_interruptions=True,add_to_chat_ctx=False)
     


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
