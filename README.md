# Moya utility library

# Usage

Add the following to your requirements.txt and set up for ssh to be passed in during the build process per moya-discover-weather

    git+ssh://git@github.com/moya-app/moya-pythonlib-util.git@0.1.1#egg=moya-pythonlib-util[pydantic-v2,redis,kafka]

See individual module documentation for usage.

## TODOs

- [ ] Business API → number lookup with caching + fastapi Depends() fn - see weather api for an example
- [ ] standard fastapi root router for version call
- [ ] add tests for src/moya/util/background.py
- [ ] sentry auto-config plugin
- [ ] inbound gzip handler
- [ ] rapidpro start flow?

# Development

## Installation

    sudo python3 -m pip install -e .[dev,kafka,pydantic-v2,redis]

## Linting

    poe fix
    poe lint

## Testing

    pytest
