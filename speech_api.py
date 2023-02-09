from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from logging import getLogger
from datetime import datetime, timedelta
from speech_recognition import ConnectionManager, ConfigLoader

# Load config
conf = ConfigLoader()

# Set Logger
logger = getLogger(conf.LOG_OUTPUT)
logger.setLevel(conf.LOG_LEVEL)

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
                                                         "channel_count": conf.CHANNEL_COUNT,
                                                         "sample_rate": conf.SAMPLE_RATE,
                                                         "sample_size": conf.SAMPLE_SIZE})

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
            if now - disp_time > timedelta(seconds = conf.RECOGNIZE_INTERVAL):
                if manager.check_speech_interval(key):
                    text = manager.speech_recognize(key)
                    if text:
                        await manager.send_message(websocket, text)
                    
                disp_time = datetime.now()
            
    except WebSocketDisconnect:
        text = manager.speech_recognize(key)
        manager.disconnect(websocket, key)

