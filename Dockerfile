FROM python:3.14

RUN apt-get update  && \
    apt-get install gcc -y  && \
    apt-get install -y git --no-install-recommends && \
    apt-get install -y graphviz && \
    apt-get clean -y

RUN mkdir /dataplatform_design

COPY ./requirements.txt  /dataplatform_design

RUN pip install -r /dataplatform_design/requirements.txt

RUN pip install --upgrade pip
RUN pip install flake8 black

COPY ./ /dataplatform_design/

WORKDIR /dataplatform_design

RUN chmod +x *.sh


