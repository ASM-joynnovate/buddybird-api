import inspect
from collections.abc import Callable

from core.helpers.cache.base import BaseKeyMaker


class CustomKeyMaker(BaseKeyMaker):
    async def make(self, *, function: Callable, prefix: str, bound_args: inspect.BoundArguments) -> str:
        path = f"{prefix}::{inspect.getmodule(function).__name__}.{function.__name__}"  # type: ignore
        args = ""

        for idx, arg in enumerate(inspect.signature(function).parameters.values()):
            if arg.name in ("self", "cls") or arg.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            args += arg.name
            if arg.name in bound_args.arguments:
                if isinstance(bound_args.arguments[arg.name], str) or isinstance(bound_args.arguments[arg.name], int):
                    args += f"={bound_args.arguments[arg.name]}"
                elif isinstance(bound_args.arguments[arg.name], dict):
                    args += f"={sorted(bound_args.arguments[arg.name].items())}"
                elif (
                    isinstance(bound_args.arguments[arg.name], list)
                    or isinstance(bound_args.arguments[arg.name], set)
                    or isinstance(bound_args.arguments[arg.name], tuple)
                ):
                    args += f"={sorted(bound_args.arguments[arg.name])}"
                elif hasattr(bound_args.arguments[arg.name], "id"):
                    args += f"={bound_args.arguments[arg.name].id}"
                else:
                    args += f"={bound_args.arguments[arg.name]}"

            if idx != len(inspect.signature(function).parameters) - 1:
                args += "_"

        if args:
            return f"{path}.{args}"

        return path
