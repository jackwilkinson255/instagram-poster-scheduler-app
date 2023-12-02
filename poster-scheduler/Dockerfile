
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

# Install ffmpeg
#RUN apt-get -y update
#RUN apt-get -y upgrade
#RUN apt-get install -y ffmpeg

#ENV GOOGLE_APPLICATION_CREDENTIALS=/.gcp/your_service_account_key.json

#ENV IMAGEMAGICK_BINARY=
RUN #apk add --no-cache imagemagick
RUN apk add ffmpeg
#RUN apk add --update --no-cache python3 && ln -sf python3.10 /usr/bin/python
#RUN python3 -m ensurepip
#RUN pip3 install --no-cache --upgrade pip setuptools
RUN apk add --update python3 && ln -sf python3.10 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --upgrade pip setuptools

#RUN #gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS --project $GOOGLE_PROJECT_ID
RUN gcloud config set project $GOOGLE_PROJECT_ID
#RUN gcloud auth application-default set-quota-project $GOOGLE_PROJECT_ID

# Install production dependencies.
RUN pip3 install -r src/requirements.txt

CMD ["python3", "src/main.py"]