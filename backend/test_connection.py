from sqlalchemy import text
from app.database import engine



try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        )

        print("dataBase connected succesfully")

        print("result :", result.scalar())


except Exception as error:
    print("DATABASE CONNECTION FSLID")
    print("erroe ", error)