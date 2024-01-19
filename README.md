# GitHub Pull Request Monitor

## Overview
GitHub Pull Request Monitor is a menu bar application for macOS that helps you monitor pull requests across your GitHub repositories. It uses a GitHub Personal Access Token to connect and fetch data.

## Features
- Monitors pull requests for all your repositories
- Provides easy access to pull requests directly from your macOS menu bar
- Uses GitHub Personal Access Token for secure access to your repositories

## Prerequisites
- Python 3
- pip (Python package manager)

## Installation
To set up the GitHub Pull Request Monitor, you need to clone the repository and run the setup script. Make sure you have Python 3 and pip installed on your system.

### Steps:
1. Clone the repository: `git clone https://github.com/ffoissey/github_pr_monitor.git`
2. Navigate to the cloned repository directory: `cd github_pr_monitor` 
3. Run the setup script: `./setup.sh`

The script will create a virtual environment, install necessary dependencies, and build the application using PyInstaller.

## Running the Application
After installation, you can run the application by opening the built application in the `dist` directory from the GUI or by running the command `open ./dist/github_pr_monitor.app`

On first run, you'll need to provide your GitHub Personal Access Token for the app to fetch and monitor your pull requests.

## Contributing
Contributions are welcome! Feel free to open issues or submit pull requests.
