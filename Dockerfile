FROM python:3.6.5-alpine3.7

RUN apk add --update alpine-sdk gcc musl-dev libffi-dev openssl-dev
RUN pip install ethexporter
COPY config_of_config.yml /usr/local/lib/python3.6
ENTRYPOINT ["ethexporter", "-L", "DEBUG", "-H", "0.0.0.0", "-p", "9306"]