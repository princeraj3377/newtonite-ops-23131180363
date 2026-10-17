from sqlalchemy import text
def test_user_test_database(db_session):
    database_name = db_session.execute(
        text("SELECT current_database()")
    ).scalar_one()


    assert database_name == "newtonite_ops_test"