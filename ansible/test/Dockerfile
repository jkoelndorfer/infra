FROM debian:9

RUN apt-get -y update && \
    apt-get -y install python-pip && \
    pip install ansible && \
    rm -rf /var/lib/apt/cache/*

VOLUME ["/opt/cloudtools"]
