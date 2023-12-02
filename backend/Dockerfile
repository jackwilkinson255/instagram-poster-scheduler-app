
# Use the official lightweight Python image.
# https://hub.docker.com/_/python
#FROM python:3.10-buster
FROM google/cloud-sdk:alpine

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True
ENV GOOGLE_PROJECT_ID={{ PROJECT_ID }}
ENV PYTHONPATH /app
## Copy local code to the container image.
ENV APP_HOME /app
ENV ACCOUNT test
WORKDIR $APP_HOME
COPY /src ./src

RUN apk add --update python3 && ln -sf python3.10 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --upgrade pip setuptools

RUN gcloud config set project $GOOGLE_PROJECT_ID

RUN pip3 install -r src/requirements.txt

EXPOSE 8000
#CMD ["uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000"]
#CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
#CMD ["uvicorn", "src.main:app", "--root-path", "/api", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

