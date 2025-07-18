FROM mcr.microsoft.com/devcontainers/python:3.13

USER vscode
WORKDIR /home/vscode

RUN python3 -m pip --no-cache-dir install \
    homeassistant==2025.7.1 \
    pip>=21.3.1 \
    xcomfort==0.1.2
