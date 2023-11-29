FROM python:3.9

RUN mkdir /src

COPY ./ /src/

RUN apt-get update  && \
    apt-get install gcc -y  && \
    apt-get install -y git --no-install-recommends && \
    apt-get install -y graphviz && \
    apt-get clean -y 
    
RUN pip install --upgrade pip && \
    pip install -r src/requirements.txt