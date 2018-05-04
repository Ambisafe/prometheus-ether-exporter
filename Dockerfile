FROM python:3.6.5-alpine3.7

RUN apk add --update alpine-sdk gcc musl-dev libffi-dev openssl-dev

COPY . /app
WORKDIR /app
RUN pip install -e .

ENTRYPOINT ["ethexporter"]
