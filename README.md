# Speech Recognition Web Server
Developed with Pytorch, ESPnet2 and Fastapi.

## Demo
![MAIspeech](https://user-images.githubusercontent.com/92005636/170158341-e8a6f585-6a47-4c9f-8438-395a345d10d5.jpg)

## Install
1. Instal requirements  
~~~
apt install python3-pip
pip3 install torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio===0.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
pip3 install fastapi python-multipart
pip3 install uvicorn[standard] Gunicorn
pip3 install aiofiles Jinja2
pip3 install espnet_model_zoo
pip3 install SoundFile
~~~
2. Configure Application  
~~~
mkdir /var/www/
cd /var/www
git clone https://github.com/masayay/maispeech.git
mv maispeech/conf_sample_linux.py maispeech/conf.py
~~~
3. Configure Gunicorn
~~~
mkdir /etc/gunicorn
mv maispeech/gunicorn_config_sample.py /etc/gunicorn/maispeech_config.py
mkdir /var/log/gunicorn
mkdir -p /var/lib/maispeech/models
mkdir -p /var/lib/maispeech/data
useradd -U -m -s /usr/sbin/nologin gunicorn
chown gunicorn:gunicorn /var/log/gunicorn
chown -R gunicorn:gunicorn /var/www/maispeech
chown -R gunicorn:gunicorn /var/lib/maispeech
chown -R gunicorn:gunicorn /etc/gunicorn
~~~
4. Start Application
~~~
mv maispeech/systemd_sample.txt /etc/systemd/system/maispeech.service
systemctl daemon-reload
systemctl start maispeech
~~~
5. Start nginx
~~~
apt install nginx
cp maispeech/nginx_sample.txt /etc/nginx/sites-available/maispeech
rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/maispeech /etc/nginx/sites-enabled/maispeech
systemctl start nginx
~~~