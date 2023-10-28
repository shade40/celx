import re

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from celadon import Widget


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"
    PATCH = "PATCH"


class TreeMethod(Enum):
    INSERT = "INSERT"
    SWAP = "SWAP"
    APPEND = "APPEND"


class Verb(Enum):
    GET = HTTPMethod.GET.value
    POST = HTTPMethod.POST.value
    DELETE = HTTPMethod.DELETE.value
    PUT = HTTPMethod.PUT.value
    PATCH = HTTPMethod.PATCH.value

    INSERT = TreeMethod.INSERT.value
    SWAP = TreeMethod.SWAP.value
    APPEND = TreeMethod.APPEND.value

    SELECT = "SELECT"


@dataclass
class Instruction:
    verb: Verb
    args: tuple[str, ...]


def _instruction_runner(instructions: list[Instruction]) -> Callable[[Widget], None]:
    """Creates a function to runs the given instructions on the calller widget's app."""

    def _interpret(self: Widget) -> None:
        self.app.run_instructions(instructions, self)

    return _interpret


def parse_callback(text: str) -> Callable[[str], bool]:
    """Parses a callback descriptor into a list of Instructions."""

    lines = re.split("[;\n]", text)

    instructions = []

    for line in lines:
        verb_str, *args = line.strip().split()
        verb = Verb(verb_str.upper())

        if verb is Verb.SELECT:
            if len(args) > 1:
                raise ValueError(f"too many arguments for verb {verb!r}")

            instructions.append(Instruction(verb, (args[0],)))

        else:
            if len(args) > 2:
                raise ValueError(f"too many arguments for verb {verb!r}")

            modifier = None
            arg = args[0]

            if len(args) == 2:
                modifier, arg = args

            instructions.append(Instruction(verb, (arg, modifier)))

    return _instruction_runner(instructions)
