FROM python:3.7.5-slim-buster

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

# Runs the application using the gunicorn HTTP gateway.  
CMD gunicorn -b 0.0.0.0:8000 --access-logfile - "canopact.app:create_app()"
