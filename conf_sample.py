#################
# API Configuration
#################
# For uvicorn
#LOG_OUTPUT = 'uvicorn'
# For gunicorn
LOG_OUTPUT = 'gunicorn.error'
# Log level
LOG_LEVEL = 'DEBUG'

# Fast Api
API_TITLE = 'MAI Speech Recognition API'
API_VERSION = '0.0.2'

#################
# AUdio Configuration
#################
# Number of channel (1: Mono, 2:Stereo)
CHANNEL_COUNT = 1
# Sample rate (Only support 16000Hz)
SAMPLE_RATE = 16000
# Bitrate (16bit, 24bit) 
SAMPLE_SIZE = 16
# Save audio file or not (in production set False) 
SAVE_AUDIO = False
# Audio save directory
#AUDIO_DIR = 'C:/User/Music/wav'
AUDIO_DIR = '/var/lib/maispeech/data'

#################
# Recognition Configuration
#################
# Speech interval (1-2 sec)
RECOGNIZE_INTERVAL = 1

# Espnet ASR Model Japanese 16kHz
#E2E_ASR_MODEL = "kan-bayashi/csj_asr_train_asr_transformer_raw_char_sp_valid.acc.ave"
E2E_ASR_MODEL = "Shinji Watanabe/laborotv_asr_train_asr_conformer2_latest33_raw_char_sp_valid.acc.ave"

# Model Cache directory
#CACHE_DIR =  "C:/User/Music/models"
CACHE_DIR = '/var/lib/maispeech/models'
