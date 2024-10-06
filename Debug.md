# Debugging

This project is configured to use devcontainers with Visual Studio code.

*Prerequisites:*

- Docker CE installed and working(On Windows WSL2 is absolutely encouraged)
- Visual Studio code installed
- Code extension for Dev Containers

*Steps*

1.  Launch root folder of repository in VS Code:

```sh
:~/git/ha-xcomfort-bridge$ code .

```

2.  After VS Code is loaded, you should be prompted to re-open folder in container.  Do so.  This _might_ take a few minutes, but be patient.
3.  Once this is done, everything should be set up.  Hit F5 to debug your code inside a running Home Assistant instance
4.  Open a browser to http://localhost:9123 (not 8123 !!) and complete the onboarding proccess and add your integration.

*Troubleshooting*

The dev container we are using is based on `https://github.com/devcontainers/images/tree/main/src/python`, which is a specialized container for Python development. We are then configuring it for Home Assistant integration development by using the template from `https://github.com/ludeeus/integration_blueprint`. The version of Home Assistant and core dependencies are controlled by the `requirements.txt` file, and can be applied to an already built container by running `scripts/setup`.
