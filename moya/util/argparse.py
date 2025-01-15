import argparse
import os
from typing import Any


class EnvArgumentParser(argparse.ArgumentParser):
    """
    Like standard argparse, but assigns default values from environment variables that are prefixed with APP_ per the Moya standard.
    """

    def _add_action(self, action: argparse.Action) -> Any:
        env_var = "APP_" + action.dest.upper()
        action.default = os.environ.get(env_var, action.default)
        action.help += f" [env: {env_var}]"  # type: ignore
        return super()._add_action(action)
