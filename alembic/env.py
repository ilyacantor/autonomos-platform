from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get DATABASE_URL from environment variable
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the unified Base from shared.database
from shared.database import Base

# Import all models so they register with Base.metadata
from app.models import *
from aam_hybrid.shared.models import *

# Use the unified Base metadata
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter which database objects Alembic should track.
    
    Exclude capitalized tables (e.g., Account, Contact, Event) which are
    managed by external connectors (Salesforce, etc.) and not part of the
    application's SQLAlchemy models.
    
    This prevents Alembic from:
    - Proposing DROP TABLE for connector-managed tables
    - Tracking schema changes in external tables
    - Interfering with connector data pipelines
    """
    if type_ == "table":
        # Ignore tables with capitalized names (connector-managed)
        # Examples: Account, Contact, Event, Lead, Opportunity, etc.
        if name and name[0].isupper():
            return False
    
    # Track all other objects (lowercase tables, indexes, constraints)
    return True


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
