from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from logging import getLogger
import conf
from datetime import datetime, timedelta
from speech_api_util import ConnectionManager
"""
Load Configuration
"""
# Logger
logger = getLogger(conf.LOG_OUTPUT)
logger.setLevel(conf.LOG_LEVEL)

# Audio Configuration
CHANNEL_COUNT = conf.CHANNEL_COUNT
SAMPLE_RATE = conf.SAMPLE_RATE
SAMPLE_SIZE = conf.SAMPLE_SIZE

# Recognize Configuration
RECOGNIZE_INTERVAL = conf.RECOGNIZE_INTERVAL
"""
API Configuration
"""
app = FastAPI(title=conf.API_TITLE,
              version=conf.API_VERSION)
# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount templates
templates = Jinja2Templates(directory="templates")
"""
Load class
"""
manager = ConnectionManager()

"""
page
"""
@app.get("/")
async def speech_recognition(request: Request):
    """
    Speech recorder test3
    """
    return templates.TemplateResponse("recognition.html", {"request": request,
                                                         "channel_count": CHANNEL_COUNT,
                                                         "sample_rate": SAMPLE_RATE,
                                                         "sample_size": SAMPLE_SIZE})

@app.get("/webspeech")
async def webspeech1(request: Request):
    """
    Speech recognition test1
    """
    return templates.TemplateResponse("webspeech_api.html", {"request": request})

"""
Websocket
"""
@app.websocket("/ws")
async def audio_process(websocket: WebSocket):
    # Get connection
    key = await manager.connect(websocket)
    # Set current time
    disp_time = datetime.now()
    
    try:
        while True:
            now = datetime.now()
            # Recieve audio
            await manager.receive_audio(websocket, key)
            
            # Recognize speech
            if now - disp_time > timedelta(seconds = RECOGNIZE_INTERVAL):
                if manager.check_speech_interval(key):
                    text = manager.speech_recognize(key)
                    if text:
                        await manager.send_message(websocket, text)
                    
                disp_time = datetime.now()
            
    except WebSocketDisconnect:
        text = manager.speech_recognize(key)
        manager.disconnect(websocket, key)

