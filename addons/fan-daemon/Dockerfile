FROM python:3.11-slim

RUN pip install pigpio

COPY fan_daemon.py /fan_daemon.py
CMD ["python3", "/fan_daemon.py"]
