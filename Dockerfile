FROM python:3.10

WORKDIR /opt/bot
COPY . .

RUN apt-get -y update
RUN apt-get install -y ffmpeg
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./app.py"]
