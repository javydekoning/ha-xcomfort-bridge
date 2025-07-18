FROM mcr.microsoft.com/devcontainers/python:3.13

USER vscode
WORKDIR /home/vscode

RUN echo "homeassistant==2025.7.1" >> requirements.txt
RUN echo "pip>=21.3.1" >> requirements.txt
RUN echo "xcomfort==0.1.2" >> requirements.txt

RUN python3 -m pip --no-cache-dir install --requirement requirements.txt
