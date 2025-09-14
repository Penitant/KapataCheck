"""
Marks 'server' as a package so pickled models can resolve server.simple_lr.

We avoid importing submodules here to prevent early side effects.
If a WSGI server needs the Flask app, import it explicitly as:
	from server.server import app
"""

# Deliberately empty.
