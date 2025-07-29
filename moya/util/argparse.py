import argparse
import os
import typing as t

from pydantic import ValidationError
from pydantic_settings import CliApp, CliSettingsSource

from moya.util.config import MoyaSettings


class EnvArgumentParser(argparse.ArgumentParser):
    """
    Like standard argparse, but assigns default values from environment variables that are prefixed with APP_ per the Moya standard.
    """

    def _add_action(self, action: argparse.Action) -> t.Any:
        env_var = "APP_" + action.dest.upper()
        action.default = os.environ.get(env_var, action.default)
        action.help += f" [env: {env_var}]"  # type: ignore
        return super()._add_action(action)


class PydanticArguments(MoyaSettings, cli_parse_args=True, cli_kebab_case=True):
    @classmethod
    def run(cls) -> int:
        css: CliSettingsSource[argparse.ArgumentParser] = CliSettingsSource(cls)
        try:
            CliApp.run(cls, cli_settings_source=css)
        except ValidationError as e:
            msg = ""
            for err in e.errors():
                msg += f"\nargument {err['loc'][0]}: {err['msg']}"
            css.root_parser.error(msg)
        return 0
