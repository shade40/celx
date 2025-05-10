from argparse import ArgumentParser

from . import Browser
from slate import feed


def run(endpoint: str):
    """Runs the application at the given endpoint."""

    with open("debug.lua", "w") as f:
        ...

    with Browser(endpoint, title="celx") as app:
        ...

    root = app.find("#root")
    print(root.children[0].content)
    print(app.dump_rules_applied_to(root.children[0].content))

def main() -> None:
    """The main entrypoint."""

    parser = ArgumentParser("A prototype browser for celx applications.")

    subs = parser.add_subparsers(required=True)

    run_command = subs.add_parser("run")
    run_command.set_defaults(func=run)
    run_command.add_argument("endpoint", help="The endpoint to connect to.")

    args = parser.parse_args()
    command = args.func

    opts = vars(args)
    del opts["func"]

    command(**vars(args))


if __name__ == "__main__":
    main()
