from fastapi import WebSocket
from logging import getLogger
import wave
import numpy as np
from numpy import ndarray
from typing import List, Dict
from datetime import datetime
import os
import conf
from speech_recognition import SpeechRecognition

"""
Load Configuration
"""
# Logger
logger = getLogger(conf.LOG_OUTPUT)
# Audio Configuration
CHANNEL_COUNT = conf.CHANNEL_COUNT
SAMPLE_RATE = conf.SAMPLE_RATE
SAMPLE_SIZE = conf.SAMPLE_SIZE
AUDIO_DIR = conf.AUDIO_DIR
SAVE_AUDIO = conf.SAVE_AUDIO

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.websocket_data: Dict[str, List[ndarray]] = {}
        self.speech_data: Dict[str, List[ndarray]] = {}
        
        # Load SpeechRecognition
        self.speech_recognizer = SpeechRecognition()
        
        # Speech continue flag
        self.speech_continue = False

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Get web socket client key
        key = websocket.headers.get('sec-websocket-key')
        # Prepare list
        self.websocket_data[key] = []
        self.speech_data[key] = []
        
        return key

    def disconnect(self, websocket, key):
        # Remove websocket
        self.active_connections.remove(websocket)
        # Remove blob data
        self.websocket_data.pop(key, None)
        self.speech_data.pop(key, None)
        
    async def send_message(self, websocket: WebSocket, message: str):
        await websocket.send_text(message)
        
    async def receive_audio(self, websocket, key):
        # Recieve binary data
        data = await websocket.receive_bytes()
        # Convert bibary to numpy ndarray(float32)
        np_data = np.frombuffer(data, dtype='float32')
        # Append data to list
        self.websocket_data[key].append(np_data)
            
    def _pop_websocket_data(self, key):
        # Get list
        np_list = self.websocket_data[key]
        # Change list to 1 dimension ndarray
        np_data = np.array(np_list).flatten()
        # Clear buffer data
        self.websocket_data[key] = []
        
        return np_data

    def _np_list_flatten(self, np_list):
        l = []
        for np_data in np_list:
            l.extend(np_data.tolist())       
        l = np.array(l).flatten()        
        return l

    def _pop_speech_data(self, key):
        # Get list
        np_list = self.speech_data[key]
        # Change list to 1 dimension ndarray
        np_data = self._np_list_flatten(np_list)
        # Clear buffer data
        self.speech_data[key] = []
        
        return np_data

    def _save_audio(self, np_data):
        # Defile audio filename
        now = datetime.now()
        filename = "voice_" + now.strftime('%Y%m%d_%H%M%S') + ".wav"
        save_path = os.path.join(AUDIO_DIR, filename)

        # Change float32(-1.0 ~ 1.0) to 16bit signed integer(-32,768 ~ 32767)
        int_size = 2**(SAMPLE_SIZE - 1) - 1
        np_data = (np_data * int_size).astype(np.int16)
        
        # Write audio
        with wave.open(save_path, 'wb') as wf:
            # Set header information
            wf.setnchannels(CHANNEL_COUNT)
            wf.setframerate(SAMPLE_RATE)
            wf.setsampwidth(int(SAMPLE_SIZE / 8)) # bit -> byte
            wf.writeframes(np_data.tobytes('C'))
        
        logger.debug("Audio file saved: %s" % save_path)
        
    def speech_recognize(self, key):
        #np_data = self._pop_websocket_data(key)
        np_data = self._pop_speech_data(key)

        if len(np_data) > 0:
            text = self.speech_recognizer.recognize_np(np_data)
            logger.debug("Speech Recognition: %s" % text)
        
            if SAVE_AUDIO:
                self._save_audio(np_data)
        else:
            text = ""

        return text

    def check_speech_interval(self, key):
        # pop websocket data
        np_data = self._pop_websocket_data(key)
        
        # Check speech segment
        speech_timestamps = self.speech_recognizer.get_timestamp_np(np_data)
        
        # If there's speech segments, store in speech_data
        if speech_timestamps:            
            self.speech_data[key].append(np_data)
            self.speech_continue = True
            result = False
        elif self.speech_continue:
            self.speech_data[key].append(np_data)
            self.speech_continue = False
            result = True
        else:
            result = True
        
        return result 

