FROM python:latest

EXPOSE 25
STOPSIGNAL SIGINT

COPY . /app
WORKDIR /app
RUN python -m pip install -r requirements.txt

ENTRYPOINT ["python", "run.py"]