
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

env_path = Path(__file__).parent / ".env.test"
config = dotenv_values(env_path)

database_url = config.get("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL missing in .env.test")

if database_url.rsplit("/", 1)[-1] != "newtonite_ops_test":
    raise RuntimeError("Refusing to connect to a non-test database")

engine = create_engine(database_url)

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT current_database()")
    )

    print("Connected to:", result.scalar())
