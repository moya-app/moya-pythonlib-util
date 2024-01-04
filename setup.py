from setuptools import setup, find_namespace_packages

extras_require = {
    "dev": [
        "black==23.3.0",
        "flake8==6.1.0",
        "Flake8-pyproject==1.2.3",
        "isort==5.12.0",
        "mypy==1.5.1",
        "poethepoet==0.22.0",
        "pytest-asyncio==0.21.0",
        "pytest-cov==4.1.0",
        "pytest-subtests==0.11.0",
        "pytest==7.1.3",
        "respx==0.20.2",
        "types-cachetools==5.3.0.7",
    ],
    "kafka": [
        "aiokafka[lz4]>=0.9.0",
    ],
    "redis": [
        "redis==5.0.1",
    ],
    "pydantic-v1": [
        "pydantic>=1.5.0,<2.0.0",
    ],
    "pydantic-v2": [
        "pydantic>=2.0.0,<3.0.0",
        "pydantic-settings>=2.0.0,<3.0.0",
    ],
    "fastapi": [
        "fastapi>=0.95.0",
        "typing-extensions>=4.8.0",
        "sentry-sdk[fastapi]",
    ],
}
extras_require["all"] = [item for name, group in extras_require.items() if name not in {"dev", "pydantic-v1", "pydantic-v2"} for item in group]

setup(
    name="moya-pythonlib-util",
    packages=find_namespace_packages(where="src"),
    version="0.1.0",
    package_dir={"": "src"},
    package_data={
        "moya.util": ["py.typed"],
        "moya.service": ["py.typed"],
        "moya.middleware": ["py.typed"],
    },
    description="Moya Util Library",
    install_requires=[
        "sentry-sdk==1.39.1",
        "opentelemetry-distro",
    ],
    extras_require=extras_require,
    test_suite="tests",
)
