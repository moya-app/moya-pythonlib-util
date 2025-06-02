# Moya utility library

# Usage

Add the following to your requirements.txt and set up for ssh to be passed in during the build process per moya-discover-weather

    git+ssh://git@github.com/moya-app/moya-pythonlib-util.git@0.1.1#egg=moya-pythonlib-util[pydantic-v2,redis,kafka]

See individual module documentation for usage.

# Build modifications when using the library

- Add `git openssh-client` to `apt install`
- Add `echo StrictHostKeyChecking=accept-new >> /etc/ssh/ssh_config` as a stage in the build
- Modify `RUN pip3 install ...` to `RUN --mount=type=ssh pip3 install ...`
- Build like `docker-compose build --ssh=default` and then use `docker-compose up -d` rather than using `docker-compose up -d --build`
- You likely need to add `gcc libc6-dev` to `apt install` packages when using the kafka library

## TODOs

- [ ] add tests for src/moya/service/kafka_runner.py
- [ ] add tests for src/moya/util/asyncpool.py
- [ ] add tests for src/moya/util/beartype.py
- [ ] add tests for src/moya/util/background.py
- [ ] add kafka tests with real kafka rather than just mocked
- [ ] rapidpro start flow?

# Development

## Installation for local development

    uv venv --python 3.12
    source .venv/bin/activate
    uv pip install -e .[dev,pydantic-v2,all]

## Linting

    poe fix
    poe lint

## Testing

    poe test

Or to test against real redis:

    cd test_envs/redis-sentinel
    docker-compose up -d
    export REDIS_URL="redis://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker-compose ps -q redis-master)):6379/0"
    export REDIS_SLAVE_URL="redis://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker-compose ps -q redis-slave)):6379/0"
    export SENTINEL_HOSTS="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker-compose ps -q redis-sentinel) | jq --slurp -R -c 'split("\n") | map(select(.!="") | [., 26379])')"
    poe test
