# Moya utility library

# Usage

Add the following to your requirements.txt and set up for ssh to be passed in during the build process per moya-discover-weather

    git+ssh://git@github.com/moya-app/moya-pythonlib-util.git@0.1.1#egg=moya-pythonlib-util[pydantic-v2,redis,kafka]

See individual module documentation for usage.

## TODOs

- [ ] Business API → number lookup with caching
- [ ] standard root api routing for version call
- [ ] background task error logging stuff
- [ ] sentry auto-config plugin
- [ ] inbound gzip handler
- [ ] async redis testsuite
- [ ] rapidpro start flow?

# Development

## Installation

    sudo python3 -m pip install -e .[dev,kafka,pydantic-v2,redis]

## Linting

    poe fix
    poe lint

## Testing

    pytest
