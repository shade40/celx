## An example celx server using Flask

A crude application created mostly as a way to test celx' functionality.

Usage:

```bash
pip install .  # or `hatch env` to run in an env
flask --app celx-server run --port 8080

# In another terminal instance
celx run 127.0.0.1:8080
```
