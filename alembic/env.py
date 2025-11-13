from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import MetaData

from alembic import context

# NOTE: No need for sys.path manipulation with proper package installation

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get DATABASE_URL from environment variable (REQUIRED - no fallback)
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "❌ FATAL: DATABASE_URL environment variable is required for migrations.\n"
        "   Please set DATABASE_URL in your environment."
    )

# Validate that we're not connecting to disabled Neon database
if "neon.tech" in database_url:
    raise RuntimeError(
        f"❌ FATAL: DATABASE_URL points to Neon database (disabled).\n"
        f"   Found: {database_url[:50]}...\n"
        f"   Expected: Supabase pooler.supabase.com"
    )

# Remove prepare_threshold for Alembic (psycopg2 doesn't support it)
import re
if "prepare_threshold" in database_url:
    database_url = re.sub(r'[&?]prepare_threshold=\d+', '', database_url)
    database_url = re.sub(r'[?&]$', '', database_url)
    print("🔧 Alembic: Removed prepare_threshold for psycopg2 compatibility")

config.set_main_option("sqlalchemy.url", database_url)
print(f"✅ Alembic using database: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'localhost'}")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import both Base objects from our multi-Base architecture
from app.models import Base as AppBase
from aam_hybrid.shared.models import Base as AAMBase

# Combine metadata from both Base objects
# This ensures all tables from both models are tracked in migrations
combined_metadata = MetaData()
for table in AppBase.metadata.tables.values():
    table.to_metadata(combined_metadata)
for table in AAMBase.metadata.tables.values():
    table.to_metadata(combined_metadata)

target_metadata = combined_metadata


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
