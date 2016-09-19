Pull latest commit to local directory
-------------------------------------
```
git reset --hard HEAD
git pull
```

Dependencies
-------
0. FFMPEG (static builds available at [https://johnvansickle.com/ffmpeg/])
0. OpenCV for Python
```bash
sudo apt-get install install build-essential pip cmake git libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev python-dev python-numpy libtbb2 libtbb-dev libjpeg-dev libpng-dev python-opencv
pip install imutils
```
0. Autobahn for Python
```bash
pip install autobahn
```
0. Nginx
```bash
apt-get install nginx -y
```

Setting up nginx
-----------
0. Copy Nginx config to ```/usr/local/nginx/conf/nginx.conf``` Replace path to motion_rec_v1.py according to your setup
```
#user  nobody;
worker_processes  auto;

error_log  logs/error.log;
error_log  logs/error.log  notice;
error_log  logs/error.log  info;

pid        logs/nginx.pid;


events {
    worker_connections  1024;
}
              

rtmp {
    server {
                listen 443;
                timeout 15s;

        application hls {
             live on;
             exec python /root/python-server-for-fyp-pls-ignore/motion_rec_v1.py rtmp://localhost:443/hls/$name $name 1>/var/log/motionlog 2>&1;
             respawn off;
             drop_idle_publisher 10s;
             hls on;
             hls_path /tmp/hls;
             hls_nested on;
             hls_fragment 5s;
             hls_playlist_length 60s;
             allow play all;

             hls_variant _hi  BANDWIDTH=640000;
        }

}
}

http {
    sendfile off;
    tcp_nopush on;
    directio 512;
    default_type application/octet-stream;


 
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }

    upstream websocket {
        server 127.0.0.1:9000;
    }



    server {
        listen 80;
        
        location /api {
            proxy_pass http://127.0.0.1:9000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
        }

        location / {
            proxy_pass http://127.0.0.1:8035;
        }


        location /hls {

            types {
                application/vnd.apple.mpegurl m3u8;
                video/mp2t ts;
            }

            root /tmp;
            add_header Cache-Control no-cache;
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
            if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Headers' 'Range';
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }
    }
}
```
0. Restart nginx
```bash
service nginx restart
```

Usage
-----
```bash
python server-websockets.py
```
