# Moya utility library

## TODOs

- [ ] how to do pydantic 1 & 2 in parallel?
- [ ] Business API → number lookup with caching
- [ ] standard root api routing for version call
- [ ] background task error logging stuff
- [ ] sentry auto-config plugin
- [ ] inbound gzip handler
- [ ] async redis testsuite
- [ ] rapidpro start flow?

# Usage

# Development

## Installation

    sudo python3 -m pip install -e .[dev,kafka,pydantic-v2]

## Linting

    poe fix
    poe lint

## Testing

    pytest
