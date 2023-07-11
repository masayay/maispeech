#!/usr/bin/bash
## config
APP_DIR=/var/lib/maispeech
GUNICORN_CONF_DIR=/etc/gunicorn
GUNICORN_LOG_DIR=/var/log/gunicorn
GUNICORN_CONF_FILE=maispeech_conf.py

## Step1: Install required packages
#apt -y install python3
#apt -y install pip
#pip install -r requirements.txt

## Step2: Create Directory
mkdir ${GUNICORN_CONF_DIR}
mkdir ${GUNICORN_LOG_DIR}
mkdir -p ${APP_DIR}/models
mkdir -p ${APP_DIR}/data

## Step3 Copy pkg
cp -r static templates ${APP_DIR}/
cp speech_*.py ${APP_DIR}/

## Step4 Create gunicorn config file
cat<<EOF> ${GUNICORN_CONF_DIR}/${GUNICORN_CONF_FILE}
#
# Gunicorn config file
#
wsgi_app = 'speech_api:app'

# Server Mechanics
#========================================
chdir = '${APP_DIR}'
user = 'gunicorn'
group = 'gunicorn'
timeout = '300'

# Server Socket
#========================================
# When using unix socket, access log cannot get 'access from ip' 
#bind = 'unix:gunicorn.sock'
bind = '127.0.0.1:8001'

# Worker Processes
#========================================
workers = 1
worker_class = 'uvicorn.workers.UvicornWorker'

#  Logging
#========================================
# access log
#access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
accesslog = '${GUNICORN_LOG_DIR}/maispeech_access.log'
# gunicorn log
errorlog = '${GUNICORN_LOG_DIR}/maispeech_error.log'
# Log Level set above info
# when set 'debug', websocket binary data are logged
loglevel = 'info'
capture_output = True
EOF

## Step5 Create app config file
cat<<EOF> ${APP_DIR}/config.ini
[API]
LOG_OUTPUT = gunicorn.error
LOG_LEVEL = INFO
API_TITLE = Speech Recognition API
API_VERSION = 1.0.0

[AUDIO]
# Number of channel (1: Mono, 2:Stereo)
CHANNEL_COUNT = 1
# Sample rate (Only support 16000Hz)
SAMPLE_RATE = 16000
# Bitrate (16bit, 24bit) 
SAMPLE_SIZE = 16
# Save audio file or not (in production set False) 
ENABLE_AUDIO_SAVE = False
# Audio save directory
AUDIO_DIR = ${APP_DIR}/data

[APP]
# Speech interval (1-2 sec)
RECOGNIZE_INTERVAL = 1

# Espnet ASR Model Japanese 16kHz
E2E_ASR_MODEL = reazon-research/reazonspeech-espnet-next

# Model Cache directory
CACHE_DIR = ${APP_DIR}/models
EOF

## Step6 Create user
useradd -U -m -s /usr/sbin/nologin gunicorn
chown -R gunicorn:gunicorn ${APP_DIR} ${GUNICORN_LOG_DIR} ${GUNICORN_CONF_DIR}

## Step7: Define daemon
cat<<EOF> /etc/systemd/system/maispeech.service
[Unit]
Description=maispeech daemon
After=network.target

[Service]
Type=notify
ExecStart=/usr/local/bin/gunicorn --config ${GUNICORN_CONF_DIR}/${GUNICORN_CONF_FILE}
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
KillMode=mixed
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start maispeech

# Step8: Logrotate
cat<<EOF> /etc/logrotate.d/gunicorn
${GUNICORN_LOG_DIR}/*.log
{
	missingok
	rotate 90
	dateext
	compress
	delaycompress
	daily
	notifempty
	create 0640 gunicorn gunicorn
	sharedscripts
	copytruncate
}
EOF

echo "Successfully installed maispeech.service!"
echo "You can connect on http:/127.0.0.1:8001/"
