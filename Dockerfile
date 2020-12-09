FROM python:3.8-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app.py ./

ENV DOCKER 1

CMD ["python", "app.py"]
