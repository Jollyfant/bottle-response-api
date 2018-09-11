FROM ubuntu

# Add metadata
LABEL maintainer="Mathijs Koymans"
LABEL email="koymans@knmi.nl"

# create user
RUN useradd -ms /bin/bash bottle

# make sure sources are up to date
RUN apt-get update \
	&& apt-get upgrade -y \
	&& apt-get install -y python-pip

WORKDIR /home/bottle

# Install dependencies
RUN pip install numpy obspy bottle

# install pip and hello-world server requirements
COPY . .

# Set default environment variables
ENV SERVICE_HOST="" \
    SERVICE_PORT=""

# Expose the port bottle is running under 
EXPOSE 8080

# Run the server
CMD ["python", "server.py"]
