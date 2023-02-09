import torch, soundfile, yaml, os, configparser
from espnet_model_zoo.downloader import ModelDownloader, str_to_hash
from espnet2.bin.asr_inference import Speech2Text
from pathlib import Path
import numpy as np
import wave
from numpy import ndarray
from fastapi import WebSocket
from typing import List, Dict
from datetime import datetime
from logging import getLogger

class ConfigLoader:
    LOG_OUTPUT = None
    LOG_LEVEL = None
    API_TITLE = None
    API_VERSION = None
    CHANNEL_COUNT = None
    SAMPLE_RATE = None
    SAMPLE_SIZE = None
    ENABLE_AUDIO_SAVE = None
    AUDIO_DIR = None
    RECOGNIZE_INTERVAL = None
    E2E_ASR_MODEL = None
    CACHE_DIR = None
    
    def __init__(self):
        config = configparser.ConfigParser()
        config_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(config_path, 'config.ini')
        config.read(config_path, 'UTF-8')
        self.LOG_OUTPUT = config["API"]["LOG_OUTPUT"]
        self.LOG_LEVEL = config["API"]["LOG_LEVEL"]
        self.API_TITLE = config["API"]["API_TITLE"]
        self.API_VERSION = config["API"]["API_VERSION"]  
        self.CHANNEL_COUNT = config.getint("AUDIO","CHANNEL_COUNT")
        self.SAMPLE_RATE = config.getint("AUDIO","SAMPLE_RATE")
        self.SAMPLE_SIZE = config.getint("AUDIO","SAMPLE_SIZE")
        self.ENABLE_AUDIO_SAVE = config.getboolean("AUDIO","ENABLE_AUDIO_SAVE")
        self.AUDIO_DIR = config["AUDIO"]["AUDIO_DIR"]
        self.RECOGNIZE_INTERVAL = config.getint("APP","RECOGNIZE_INTERVAL")
        self.E2E_ASR_MODEL = config["APP"]["E2E_ASR_MODEL"]
        self.CACHE_DIR = config["APP"]["CACHE_DIR"]

# Load config
conf = ConfigLoader()

# Set logger
logger = getLogger(conf.LOG_OUTPUT)

def get_device():
    """
    Determine if an nvidia GPU is available
    
    Returns
    -------
    device:
        'cuda'
        'cpu'
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    return device

def get_dict_from_cache(meta:Path):
    meta = Path(meta)
    outpath = meta.parent
    if not meta.exists():
        return None

    with meta.open("r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
        assert isinstance(d, dict), type(d)
        yaml_files = d["yaml_files"]
        files = d["files"]
        assert isinstance(yaml_files, dict), type(yaml_files)
        assert isinstance(files, dict), type(files)

        retval = {}
        for key, value in list(yaml_files.items()) + list(files.items()):
            if not (outpath / value).exists():
                return None
            retval[key] = str(outpath / value)
        return retval

class SpeechRecognition(object):
    def __init__(self):
        # Download pretrained data and define model
        d = ModelDownloader(conf.CACHE_DIR)
        
        # Get device
        device = get_device()
        logger.info("SpeechRecognition started on device: %s" % device)

        # Check meta.yaml exsists
        url = d.get_url(conf.E2E_ASR_MODEL)
        meta_yaml = Path(conf.CACHE_DIR, str_to_hash(url), "meta.yaml")
    
        if meta_yaml.exists():
            config = get_dict_from_cache(meta_yaml)
            asr_config = config["asr_train_config"]
            asr_pth = config["asr_model_file"]
        else:
            # If doesnot exsist in cache, download and unpack
            config = d.download_and_unpack(conf.E2E_ASR_MODEL)
            asr_config = config["asr_train_config"]
            asr_pth = config["asr_model_file"]

        # Configure Speech2Text
        self.speech2text = Speech2Text(asr_config, asr_pth, device=device)
        
        # torch config
        os.environ['TORCH_HOME'] = conf.CACHE_DIR
        
        # Voice Activity Detector
        self.vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      verbose=False)
        (self.get_speech_timestamps,
         _, self.read_audio,
         *_) = utils

    def recognize_wav(self, data_path):
        """
        Recognize speech by wav audio file

        Parameters
        ----------
        data_path : wav audio path

        Returns
        -------
        text : str
        """
        # load wav audio file
        data, samplerate = soundfile.read(data_path)

        # Get speech recognition
        nbests = self.speech2text(data)
        text, *_ = nbests[0]
        
        return text

    def recognize_np(self, np_data):
        """
        Recognize speech by numpy file

        Parameters
        ----------
        np_data : numpy.ndarray(float32)

        Returns
        -------
        text : str
        """
        
        # Get speech recognition
        nbests = self.speech2text(np_data)
        text, *_ = nbests[0]
        
        return text
    
    def get_timestamp_np(self, np_data):
        # Chnage numpy.ndarray(float32) to torch.tensor
        py_data = torch.from_numpy(np_data.astype(np.float32)).clone()
        
        # Get timestamp
        speech_timestamps = self.get_speech_timestamps(py_data,
                                                       self.vad_model,
                                                       sampling_rate=conf.SAMPLE_RATE)
        
        return speech_timestamps
    
    def get_timestamp_wav(self, data_path):
        wav = self.read_audio(data_path, sampling_rate=conf.SAMPLE_RATE)
        
        # Get timestamp
        speech_timestamps = self.get_speech_timestamps(wav,
                                                       self.vad_model,
                                                       sampling_rate=conf.SAMPLE_RATE)
        
        return speech_timestamps


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
        save_path = os.path.join(conf.AUDIO_DIR, filename)

        # Change float32(-1.0 ~ 1.0) to 16bit signed integer(-32,768 ~ 32767)
        int_size = 2**(conf.SAMPLE_SIZE - 1) - 1
        np_data = (np_data * int_size).astype(np.int16)
        
        # Write audio
        with wave.open(save_path, 'wb') as wf:
            # Set header information
            wf.setnchannels(conf.CHANNEL_COUNT)
            wf.setframerate(conf.SAMPLE_RATE)
            wf.setsampwidth(int(conf.SAMPLE_SIZE / 8)) # bit -> byte
            wf.writeframes(np_data.tobytes('C'))
        
        logger.debug("Audio file saved: %s" % save_path)
        
    def speech_recognize(self, key):
        #np_data = self._pop_websocket_data(key)
        np_data = self._pop_speech_data(key)

        if len(np_data) > 0:
            text = self.speech_recognizer.recognize_np(np_data)
            logger.debug("Speech Recognition: %s" % text)
        
            if conf.ENABLE_AUDIO_SAVE:
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
