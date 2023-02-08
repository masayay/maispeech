# Speech Recognizer API
Developed with Pytorch, ESPnet2 and Fastapi.

## Demo
![MAIspeech](https://user-images.githubusercontent.com/92005636/170158341-e8a6f585-6a47-4c9f-8438-395a345d10d5.jpg)

## Install
~~~
apt -y install git
git clone https://github.com/masayay/maispeech.git
cd maispeech
sudo bash install.sh
~~~

## Usage
### start / stop service
~~~
systemctl start maispeech
systemctl stop maispeech
~~~

### Access with web browser
http:/X.X.X.X:8000/


## nginx configuration sample
~~~
apt install nginx
cp nginx_sample.txt /etc/nginx/sites-available/maispeech
rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/maispeech /etc/nginx/sites-enabled/maispeech
systemctl start nginx
~~~

