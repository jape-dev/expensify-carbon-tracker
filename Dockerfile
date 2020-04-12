FROM python:3.7.5-slim-buster

RUN apt-get update && apt-get install -qq -y \
  build-essential libpq-dev --no-install-recommends

# Sets the working directory then creates it.  
ENV INSTALL_PATH /canopact
RUN mkdir -p $INSTALL_PATH

WORKDIR $INSTALL_PATH

# Copies requirements file into docker image.
# Only installs if changes are made to .txt file.
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copies code into docker image.
COPY . .
# Copies cli egg info into container.
RUN pip install --editable .

# Runs the application using the gunicorn HTTP gateway.
CMD gunicorn -b 0.0.0.0:8000 --access-logfile - "canopact.app:create_app()"
