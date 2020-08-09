FROM python:3.7.7-slim-stretch
WORKDIR /app
COPY . /app

#RUN echo "deb http://mirrors.aliyun.com/debian/ stretch main non-free contrib\n"\
#    "deb-src http://mirrors.aliyun.com/debian/ stretch main non-free contrib\n"\
#    "deb http://mirrors.aliyun.com/debian-security stretch/updates main\n"\
#    "deb-src http://mirrors.aliyun.com/debian-security stretch/updates main\n"\
#    "deb http://mirrors.aliyun.com/debian/ stretch-updates main non-free contrib\n"\
#    "deb-src http://mirrors.aliyun.com/debian/ stretch-updates main non-free contrib\n"\
#    "deb http://mirrors.aliyun.com/debian/ stretch-backports main non-free contrib\n"\
#    "deb-src http://mirrors.aliyun.com/debian/ stretch-backports main non-free contrib" > /etc/apt/sources.list && \
#    apt-get update && apt-get -y --no-install-recommends install gcc binutils python3-dev iproute2 && rm -rf /var/lib/apt/lists/* && \
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["python", "app.py"]


