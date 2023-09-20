from flask import g
import sqlite3
import os
from dotenv import load_dotenv
from token_generation import get_token
from validators.table_name import table_name_validator

load_dotenv()  # Load environment variables from .env file
db_path = os.getenv("DATABASE")


class FDataBase:
    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

# Database sampling methods (SELECT)

    def get_username_by_telegram_id(self, telegram_id: int) -> bool | str:
        """
        Get username in the Users table by telegram_link value.
        :return: username or False
        """
        try:
            self.__cur.execute("""SELECT username FROM Users WHERE telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()

            if res:  # If a user with this link is found
                return res[0]
            else:
                return False

        except sqlite3.Error as e:
            print(str(e))
            return False

    def get_group_id_by_token(self, token: str) -> int:
        """
        Get the group id using the group token.
        :return: id | 0
        """
        try:
            self.__cur.execute("""SELECT id FROM Groups WHERE token = ?""", (token,))
            res = self.__cur.fetchone()
            if res:
                return res[0]
            else:
                return 0

        except sqlite3.Error as e:
            print(str(e))
            return 0

    def get_group_id_by_telegram_id(self, telegram_id: int) -> int:
        """
        Get the group id using the telegram id.
        :return: id | False.
        """
        try:
            self.__cur.execute("""SELECT group_id FROM Users WHERE telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()

            if res:
                return res[0]
            else:
                return False

        except sqlite3.Error as e:
            print(str(e))
            return False

    def get_token_by_username(self, username: str) -> str:
        """
        Get the group token using the username.
        :return: token | empty line
        """
        try:
            self.__cur.execute("""SELECT token FROM Groups WHERE id = 
                                 (SELECT group_id FROM Users WHERE username = ?)""", (username,))
            res = self.__cur.fetchone()
            if res:
                return res[0]
            else:
                return ""

        except sqlite3.Error as e:
            print(str(e))
            return ""

    def get_token_by_telegram_id(self, telegram_id: int) -> str:
        """
        Get the group token using the telegram link.
        :return: token | empty line.
        """
        try:
            self.__cur.execute("""SELECT token FROM Groups WHERE id = 
                                 (SELECT group_id FROM Users WHERE telegram_id = ?)""", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                return res[0]
            else:
                return ""

        except sqlite3.Error as e:
            print(str(e))
            return ""

    def get_salt_by_username(self, username: str) -> str | bool:
        """
        Get hash salt using username
        :return: salt | False (if this username is not in database)
        """
        try:
            self.__cur.execute("""SELECT psw_salt FROM Users WHERE username = ?""", (username,))
            res = self.__cur.fetchone()
            if res:
                return str(res[0])
            else:
                return False

        except sqlite3.Error as e:
            print(str(e))
            return False

    def get_id_by_username_or_telegram_id(self, username: str = "", telegram_id: int = 0) -> bool:
        """
        Checking user existence in database
        :param username: (default = "")
        :param telegram_id: (default = 0)
        :return: True | False
        """
        try:
            self.__cur.execute("""SELECT id FROM Users WHERE telegram_id = ?""", (telegram_id,))
            res_link = self.__cur.fetchone()

            self.__cur.execute("""SELECT id FROM Users WHERE username = ?""", (username,))
            res_username = self.__cur.fetchone()

            if res_link or res_username:  # If a user with this link or name is found
                return True
            else:
                return False

        except sqlite3.Error as e:
            print(str(e))
            return False

    def auth_by_username(self, username: str, psw_hash: str, token: str) -> bool:
        """
        Function to confirm user authorization using 3 parameters
        :return: True | False
        """
        try:
            self.__cur.execute("""SELECT username FROM Users WHERE username = ? AND password_hash = ? AND EXISTS (
                    SELECT token FROM Groups WHERE Groups.id = Users.group_id AND token = ?)""",
                               (username, psw_hash, token))
            res = self.__cur.fetchone()
            if res:
                return True
            else:
                return False

        except sqlite3.Error as e:
            print(str(e))
            return False

    def select_data_for_household_table(self, table_name: str, n: int) -> list:
        """
        Returns the specified number of rows (starting with the most recent) from the budget table.
        :param table_name: group table in format "budget_{group_id}" (no additional validation)
        :param n: number of rows returned.
        :return: list of n elements | empty list
        """
        try:
            self.__cur.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ?", (n,))
            result = self.__cur.fetchall()
            result_list = [list(row) for row in result]
            return result_list

        except sqlite3.Error as e:
            print(str(e))
            return []

# Methods for inserting data into a database (INSERT)

    def add_user_to_db(self, username: str, psw_salt: str, psw_hash: str, group_id: int, telegram_id: int) -> bool:
        """
        Insert a new user to the Users table
        :return: True | False
        """
        try:
            self.__cur.execute("INSERT INTO Users "
                               "VALUES(NULL, ?, ?, ?, ?, ?, strftime('%d-%m-%Y %H:%M:%S', 'now', 'localtime'))",
                               (username, psw_salt, psw_hash, group_id, telegram_id,))
            self.__db.commit()

        except sqlite3.Error as e:
            print(str(e))
            return False

        else:
            return True

    def add_monetary_transaction_to_db(self, table_name: str, username: str, amount: int, description: str = "")\
            -> bool:
        """
        Submits the "add_expense" and "add_income" forms to the database.
        :param table_name: String in format "budget_n" -> will undergo additional validation.
        :param username: the name of the user making the changes.
        :param amount: value of the deposited amount.
        :param description: optional parameter.
        :return: True | False
        """
        if not table_name_validator(table_name):  # Additional check of table title format
            return False
        try:
            self.__cur.execute(
                f"INSERT INTO {table_name} VALUES (NULL, COALESCE((SELECT SUM(transfer) FROM {table_name}), 0) + ?,"
                f" ?, ?, strftime('%d-%m-%Y %H:%M:%S', 'now', 'localtime'), ?)",
                (amount, username, amount, description))
            self.__db.commit()

        except sqlite3.Error as e:
            print(str(e))
            return False

        else:
            return True

    def create_new_group(self, owner: int) -> str | bool:
        """
        creating a new group in the Groups table and generate new token for this group.
        :param owner: link to the telegram of the user who initiates the creation of the group.
        :return: token | False
        """
        try:
            token = get_token()
            self.__cur.execute("INSERT INTO Groups VALUES(NULL, ?, ?)", (owner, token,))
            self.__db.commit()

        except sqlite3.Error as e:
            print(str(e))
            return False

        else:
            return token

# Methods for updating data in a database (UPDATE)

    def update_user_last_login(self, username: str) -> None:
        """
        changes the user's last login time in the last_login column in the Users table.
        :return: None
        """
        try:
            self.__cur.execute("""UPDATE Users SET last_login = strftime('%d-%m-%Y %H:%M:%S', 'now', 'localtime') 
            WHERE username = ?""", (username,))
            self.__db.commit()

        except sqlite3.Error as e:
            print(str(e))


def connect_db():
    """
    Connect to a database.
    :return: connection | None
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        print("Database connection (main): OK")
        return conn

    except sqlite3.Error as e:
        print(str(e))


def get_db():
    """
    Connect to a database using a Flask application object.
    :return: connection
    """
    if not hasattr(g, "link_db"):
        g.link_db = connect_db()
        print("Database connection (g): OK")
    return g.link_db


def close_db_g(error) -> None:
    """
    Closing a database connection using a Flask application object.
    :return: None
    """
    if hasattr(g, "link_db"):
        g.link_db.close()
        print("Database connection (g): CLOSED")


def close_db_main(connection):
    """
    Closing a database connection.
    :return: None
    """
    if connection:
        connection.close()
        print("Database connection (main): CLOSED")


def create_db() -> None:
    """
    Creates 2 main tables: Users and Groups, using a .sql file describing their structures.
    :return: None
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()

        with open("create_db.sql", 'r') as file:
            cursor.executescript(file.read())

        conn.commit()
        close_db_main(conn)

    except sqlite3.Error as e:
        print(str(e))


def create_table_group(table_name: str) -> None:
    """
    Creates a table in the database called budget_? (id, total, username, transfer, date_time, description)

    Contains table_name_validator -> to protect against sql injection, validation of the table_name parameter is needed
    :param table_name: "budget_?"
    :return: None
    """
    try:
        if not table_name_validator(table_name):
            raise ValueError("Possible SQL injection attempt")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = (f"CREATE TABLE IF NOT EXISTS {table_name} (id integer PRIMARY KEY AUTOINCREMENT, "
                 f"total integer NOT NULL, "
                 f"username text NOT NULL, "
                 f"transfer integer NOT NULL, "
                 f"date_time text NOT NULL, "
                 f"description text NOT NULL);")
        cursor.execute(query)

        conn.commit()
        conn.close()

    except sqlite3.Error as e:
        print(str(e))

    except ValueError as e:
        print(str(e))


if __name__ == '__main__':
    create_db()
