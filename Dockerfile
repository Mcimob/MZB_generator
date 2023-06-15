FROM python:3

WORKDIR /usr/src/project

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY code/ ./

CMD ["python3", "server.py"]