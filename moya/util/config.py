from pydantic import BaseModel  # noqa: F401 For reexporting
from pydantic_settings import BaseSettings, SettingsConfigDict


class MoyaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # Automatically pick up the named variables from the environment and
        # strip the APP_ prefix
        env_prefix="APP_",
        # When using nested models as part of Pydantic config,
        # it's possible to set individual fields by specifying a
        # nested delimiter.
        # https://docs.pydantic.dev/latest/usage/settings/#parsing-environment-variable-values
        env_nested_delimiter="__",
        # Rename the env vars to lowercase in pydantic
        case_sensitive=False,
        # Don't allow mutation of the settings object, and allow it to be hashed
        frozen=True,
    )
