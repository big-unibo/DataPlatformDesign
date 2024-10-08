FROM python:3.13

RUN mkdir /src

COPY ./ /src/

RUN apt-get update  && \
    apt-get install gcc -y  && \
    apt-get install -y git --no-install-recommends && \
    apt-get install -y graphviz && \
    apt-get clean -y

RUN pip install --upgrade pip
RUN pip install -r src/requirements.txt
RUN pip install flake8 black
