import torch
from logging import getLogger
import soundfile
from espnet_model_zoo.downloader import ModelDownloader, str_to_hash
from espnet2.bin.asr_inference import Speech2Text
import conf
from pathlib import Path
import yaml
import os
import numpy as np
"""
Load Configuration
"""
logger = getLogger(conf.LOG_OUTPUT)
E2E_ASR_MODEL = conf.E2E_ASR_MODEL
CACHE_DIR = conf.CACHE_DIR
SAMPLE_RATE = conf.SAMPLE_RATE

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
        d = ModelDownloader(CACHE_DIR)
        
        # Get device
        device = get_device()
        logger.info("SpeechRecognition started on device: %s" % device)

        # Check meta.yaml exsists
        url = d.get_url(E2E_ASR_MODEL)
        meta_yaml = Path(CACHE_DIR, str_to_hash(url), "meta.yaml")
    
        if meta_yaml.exists():
            config = get_dict_from_cache(meta_yaml)
            asr_config = config["asr_train_config"]
            asr_pth = config["asr_model_file"]
        else:
            # If doesnot exsist in cache, download and unpack
            config = d.download_and_unpack(E2E_ASR_MODEL)
            asr_config = config["asr_train_config"]
            asr_pth = config["asr_model_file"]

        # Configure Speech2Text
        self.speech2text = Speech2Text(asr_config, asr_pth, device=device)
        
        # torch config
        os.environ['TORCH_HOME'] = CACHE_DIR
        
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
                                                       sampling_rate=SAMPLE_RATE)
        
        return speech_timestamps
    
    def get_timestamp_wav(self, data_path):
        wav = self.read_audio(data_path, sampling_rate=SAMPLE_RATE)
        
        # Get timestamp
        speech_timestamps = self.get_speech_timestamps(wav,
                                                       self.vad_model,
                                                       sampling_rate=SAMPLE_RATE)
        
        return speech_timestamps
