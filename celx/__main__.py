from argparse import ArgumentParser

from . import HttpApplication


def run(endpoint: str):
    with HttpApplication(endpoint, title="celx") as app:
        ...


def main() -> None:
    parser = ArgumentParser("A prototype browser for celx applications.")

    subs = parser.add_subparsers(required=True)

    parser_run = subs.add_parser("run")
    parser_run.add_argument("endpoint", help="The endpoint to connect to.")
    parser_run.set_defaults(func=run)

    args = parser.parse_args()
    command = args.func

    opts = vars(args)
    del opts["func"]

    command(**vars(args))
    return


if __name__ == "__main__":
    main()
