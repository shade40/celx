from argparse import ArgumentParser

from . import HttpApplication


def run(endpoint: str):
    with HttpApplication(endpoint, title="celx") as app:
        ...


def main() -> None:
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
