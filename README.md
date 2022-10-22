# valmon - Validator Monitor

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Requirements

- Running onomy node with REST API enabled
- Docker and docker-compose installed
- Python 3.8+

## Installation

Clone repository
```
git clone https://github.com/dotneko/valmon.git
```

### Setup PostgreSQL

Configure PostgreSQL settings `pg_settings_dev.env` (from `pg_settings_example.env`)

Build and run PostgreSQL db with docker compose:

N.B. Following commands/scripts may require `sudo`

```
docker compose up --build
```

Confirm database table created with script `db_select_all.sh`

### Setup monitoring daemon

Python monitoring daemon located in `./monitor` directory

Ensure REST API enabled for **onomyd** and check endpoint in `./onomy/config/app.toml`

Configure settings in `./monitor/config.json` (from `./monitor/config.json.example`)

Install dependencies (optionally create virtual environment for installation):

```
pip install -r requirements.txt
# or
python -m pip install -r requirements.txt
```

## Launch

Launch dockerized PostgreSQL if not already running

Launch daemon with script `launch_daemon.sh`
