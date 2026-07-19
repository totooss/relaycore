"""RelayCore package bootstrap helpers."""

from .storage import DEFAULT_DB_PATH, bootstrap_database, connect_database

__version__ = "1.0.0"

__all__ = ["DEFAULT_DB_PATH", "__version__", "bootstrap_database", "connect_database"]
