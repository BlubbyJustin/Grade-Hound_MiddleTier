# # Python image to use.
# FROM python:3.10

# # Set the working directory to /app
# WORKDIR /app

# # copy the requirements file used for dependencies
# COPY requirements.txt .

# RUN apt-get update \
#     && apt-get -y install libpq-dev gcc 
# # Install any needed packages specified in requirements.txt
# RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

# # Copy the rest of the working directory contents into the container at /app
# COPY . .

# # Run app.py when the container launche][]
# ENTRYPOINT ["python", "app.py"]

# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3

# Copy application dependency manifests to the container image.
# Copying this separately prevents re-running pip install on every code change.
COPY requirements.txt ./

# Install production dependencies.
RUN set -ex; \
    pip install -r requirements.txt; \
    pip install gunicorn

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Copy any certificates if present.
#COPY ./certs /app/certs

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app

# ENTRYPOINT ["python", "app.py"]