# bottle-response-api
Python Bottle API for getting the instrument frequency response of StationXML through FDSNWS. The response evaluation is powered by ObsPy.

## Building Docker image

    docker build -t response-api:1.0 .

## Running the image

    docker run -d --rm -p 8080:8080 -e "{SERVICE_HOST=0.0.0.0}" -e "SERVICE_PORT=8080" response-api:1.0 
