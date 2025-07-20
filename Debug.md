# Debugging

This project is configured to use devcontainers with Visual Studio code.

*Prerequisites:*

- Docker
- Visual Studio code with "Dev Containers" extension.

*Steps*

1.  Launch root folder of repository in VS Code:

```sh
:~/git/ha-xcomfort-bridge$ code .

```

2.  After VS Code is loaded, you should be prompted to re-open folder in container.  Do so.  This _might_ take a few minutes, but be patient.
3.  Once this is done, everything should be set up. Hit F5 to debug your code inside a running HomeAssistant instance. This should work with breakpoints etc. Alternatively, use the "Run Home Assistant" task. This will start Hass on the defaul 8123 port.
4.  Should be prompted to open in a browser, if not, then do Ctrl-Shift-p and select "Open port in browser" and then select "Home assistant (8123)".
