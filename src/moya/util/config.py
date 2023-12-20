import pydantic
from pydantic import BaseModel  # noqa: F401 For reexporting

pydantic_version = pydantic.__version__

# Handle both pydantic 1.x and 2.x. There is a lot of hackery here to make mypy
# work correctly in both versions.
if pydantic_version < "2.0.0":
    fix_validator = pydantic.root_validator(pre=True)  # type: ignore
    BaseSettings = pydantic.BaseSettings  # type: ignore
else:
    import pydantic_settings  # type: ignore

    fix_validator = pydantic.model_validator(mode="before")  # type: ignore
    BaseSettings = pydantic_settings.BaseSettings  # type: ignore


class MoyaSettings(BaseSettings):  # type: ignore
    class Config:
        # Automatically pick up the named variables from the environment and
        # strip the APP_ prefix
        env_prefix = "APP_"

        # When using nested models as part of Pydantic config,
        # it's possible to set individual fields by specifying a
        # nested delimiter.
        # https://docs.pydantic.dev/latest/usage/settings/#parsing-environment-variable-values
        env_nested_delimiter = "__"

        # Rename the env vars to lowercase in pydantic
        case_sensitive = False

        # Don't allow mutation of the settings object, and allow it to be hashed
        frozen = True

    # AWS paramstore cannot have a blank string, so if a variable is set to
    # <UNSET> then pretend it didn't exist.
    @fix_validator
    def fix_aws_paramstore(cls, values: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in values.items() if v != "<UNSET>"}
