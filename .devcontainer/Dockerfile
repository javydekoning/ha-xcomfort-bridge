FROM mcr.microsoft.com/devcontainers/python:3.14

USER vscode
WORKDIR /home/vscode

COPY requirements.txt /tmp/requirements.txt

RUN python3 -m pip --no-cache-dir install -r /tmp/requirements.txt
