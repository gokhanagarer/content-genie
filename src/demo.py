"""`make demo` entrypoint — runs the offline pipeline on a built-in example topic."""

from .main import main

if __name__ == "__main__":
    raise SystemExit(main(["--topic", "Server-Side Tagging", "--no-wp"]))
