import sys

sys.path.append('../')

import sqlite3
import os
import re
from dotenv import load_dotenv
from flask import g

from app.logger import setup_logger
from app.encryption import get_token
from app.time_checking import timeit

load_dotenv()  # Load environment variables from .env file
db_path = os.getenv("DATABASE")

logger_database = setup_logger("logs/DatabaseLog.log", "db_logger")
        

class DatabaseQueries:
    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

# Database sampling methods (SELECT)

    def get_username_by_telegram_id(self, telegram_id: int) -> str:
        try:
            self.__cur.execute("""SELECT username 
                                  FROM Users 
                                  WHERE telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()

            if res:  # If a user with this link is found
                return res[0]
            else:
                return ""

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {telegram_id}")
            return ""

    def get_telegram_id_by_username(self, username: str) -> int:
        try:
            self.__cur.execute("""SELECT telegram_id 
                                  FROM Users 
                                  WHERE username = ?""", (username,))
            res = self.__cur.fetchone()

            if res:  # If a user with this link is found
                return res[0]
            else:
                return 0

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {username}")
            return 0

    def get_group_id_by_token(self, token: str) -> int:
        """
        :return: id | 0
        """
        try:
            self.__cur.execute("""SELECT id 
                                  FROM Groups 
                                  WHERE token = ?""", (token,))
            res = self.__cur.fetchone()
            if res:
                return res[0]
            else:
                return 0

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {token}")
            return 0

    def get_group_id_by_telegram_id(self, telegram_id: int) -> int:
        """
        :return: group id | 0.
        """
        try:
            self.__cur.execute("""SELECT group_id 
                                  FROM Users 
                                  WHERE telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()

            if res:
                return res[0]
            else:
                return 0

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {telegram_id}")
            return 0

    def get_group_id_by_username(self, username: str) -> int:
        try:
            self.__cur.execute("""SELECT group_id 
                                  FROM Users 
                                  WHERE username = ?""", (username,))
            res = self.__cur.fetchone()

            if res:
                return res[0]
            else:
                return 0

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {username}")
            return 0

    def get_token_by_username(self, username: str) -> str:
        """
        :return: token | empty string
        """
        try:
            self.__cur.execute("""SELECT g.token
                                  FROM Groups g
                                  JOIN Users u ON g.id = u.group_id
                                  WHERE u.username = ?""", (username,))
            res = self.__cur.fetchone()
            if res:
                return res[0]
            else:
                return ""

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {username}")
            return ""

    def get_token_by_telegram_id(self, telegram_id: int) -> str:
        """
        :return: token | empty string
        """
        try:
            self.__cur.execute("""SELECT g.token
                                  FROM Groups g
                                  JOIN Users u ON g.id = u.group_id
                                  WHERE u.telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                return res[0]
            else:
                return ""

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {telegram_id}")
            return ""

    def get_salt_by_username(self, username: str) -> str:
        """
        :return: salt | empty string (if this username is not in the database)
        """
        try:
            self.__cur.execute("""SELECT psw_salt 
                                  FROM Users 
                                  WHERE username = ?""", (username,))
            res = self.__cur.fetchone()
            if res:
                return str(res[0])
            else:
                return ""

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: {username}")
            return ""

    def auth_by_username(self, username: str, psw_hash: str) -> bool:
        """
        Function to confirm user authorization using three parameters
        """
        try:
            self.__cur.execute("""SELECT * 
                                  FROM Users u
                                  JOIN Groups g ON g.id = u.group_id
                                  WHERE u.username = ?
                                  AND password_hash = ?""", (username, psw_hash))
            res = self.__cur.fetchone()
            if res:
                return True
            else:
                return False

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: username: {username}, psw_hash: {psw_hash}")
            return False

    def select_data_for_household_table(self, group_id: int, number_of_last_records: int) -> list:
        """
        returns the specified number of rows (starting with the most recent) from the budget table.
        :param group_id:
        :param number_of_last_records: number of rows returned.
        :return: list of n elements | empty list
        """
        table_name = f"budget_{group_id}"

        try:
            if number_of_last_records == 0:  # getting all records
                self.__cur.execute(f"""SELECT *
                                       FROM {table_name}
                                       ORDER BY id DESC""")
                result = self.__cur.fetchall()
                result_list = [list(row) for row in result]
                return result_list
            else:
                self.__cur.execute(f"SELECT * "
                                   f"FROM {table_name} "
                                   f"ORDER BY id DESC "
                                   f"LIMIT ?", (number_of_last_records,))
                result = self.__cur.fetchall()
                result_list = [list(row) for row in result]
                return result_list

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: "
                                  f"group id: {group_id}, n: {number_of_last_records}, table name: {table_name}")
            return []

    def get_group_users(self, group_id: int) -> list:
        """
        :return: list (empty or with usernames of group members)
        """
        try:
            self.__cur.execute("""SELECT username
                                  FROM Users
                                  WHERE group_id=?""", (group_id,))
            result = self.__cur.fetchall()
            result_list = [str(row[0]) for row in result]
            return result_list

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: group id: {group_id}")
            return []

    def get_group_users_data(self, group_id: int) -> list:
        """
        :return: list (empty or with usernames of group members and last_login row)
        """
        try:
            self.__cur.execute("""SELECT username, last_login
                                  FROM Users
                                  WHERE group_id=?""", (group_id,))
            result = self.__cur.fetchall()
            result_list = [list(row) for row in result]
            return result_list

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: group id: {group_id}")
            return []

    def get_group_owner_username_by_group_id(self, group_id: int) -> str:
        try:
            self.__cur.execute("""SELECT u.username 
                                  FROM Users u 
                                  JOIN Groups g ON u.telegram_id = g.owner
                                  WHERE g.id = ?""", (group_id,))
            res = self.__cur.fetchone()
            if res:
                return str(res[0])
            else:
                return ""

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: group id: {group_id}")
            return ""

    def check_record_id_is_exist(self, group_id: int, record_id: int) -> bool:
        table_name = f"budget_{group_id}"
        try:
            self.__cur.execute(f"""SELECT *
                                   FROM {table_name}
                                   WHERE id = ?""", (record_id,))
            res = self.__cur.fetchone()
            if res:
                return True
            return False

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: group id: {group_id}, record id: {record_id}, "
                                  f"table name: {table_name}")
            return False

    def check_username_is_exist(self, username: str) -> bool:
        try:
            self.__cur.execute("""SELECT *
                                  FROM Users
                                  WHERE username = ?""", (username,))
            res = self.__cur.fetchone()
            if res:
                return True
            return False

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: username: {username}")
            return False

    def check_telegram_id_is_exist(self, telegram_id: int) -> bool:
        try:
            self.__cur.execute("""SELECT *
                                  FROM Users
                                  WHERE telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                return True
            return False

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: telegram ID: {telegram_id}")
            return False

    """
    Functions for checking uniqueness are necessary to avoid problems when inserting data into a unique column
    """
    def check_token_is_unique(self, token: str) -> bool:  # necessary if you want to reduce the token length
        try:
            self.__cur.execute("""SELECT *
                                  FROM Groups
                                  WHERE token = ?""", (token,))
            res = self.__cur.fetchone()
            if res:
                return False
            else:
                return True

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: new token: {token}")
            return False

    def check_username_is_group_owner(self, username: str, group_id: int) -> bool:
        try:
            owner_username: str = self.get_group_owner_username_by_group_id(group_id)
            if owner_username == username:
                return True
            return False

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: username: {username}, group_id: {group_id}")
            return False

    def check_limit_users_in_group(self, group_id: int) -> bool:
        """
        Returns: True if there are empty seats in the group.
        by token checks the group's filling limit.

        if there is no group with such a token, it will return False.
        """
        try:
            self.__cur.execute("""SELECT COUNT(telegram_id)
                                  FROM Users
                                  WHERE group_id = ?""", (group_id,))
            res = self.__cur.fetchone()
            if 0 < int(res[0]) < 20:  # condition > 0 is used for secondary checking for group existence
                return True
            return False

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: group #{group_id}")
            return False  # to prevent a user from being written to a non-existent group

    def get_user_language(self, telegram_id) -> str:
        """
        Gets the user's (telegram_id) language from the database.
        If there is no entry for the user in the database, the default language is used.
        By default, the user will be offered text in English.
        """
        try:
            self.__cur.execute("""SELECT language
                                  FROM UserLanguages
                                  WHERE telegram_id = ?""", (telegram_id,))
            res = self.__cur.fetchone()
            if res:
                return str(res[0])
            return "en"

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: telegram_id: {telegram_id}")
            return "en"

    def get_last_sum_in_group(self, group_id: int) -> int:
        """
        Gets the last total amount in the group table to then add/subtract the amount of the new transaction.
        Returns 0 if there are no records.
        """
        table_name = f"budget_{group_id}"
        try:
            self.__cur.execute(f"""SELECT total
                                   FROM {table_name}
                                   ORDER BY id DESC
                                   LIMIT 1""")
            res = self.__cur.fetchone()
            if res:
                return int(res[0])
            return 0

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: Group #{group_id}")
            return 0

# Methods for inserting data into a database (INSERT / REPLACE)

    def add_user_language(self, telegram_id, language: str) -> bool:
        try:
            self.__cur.execute("REPLACE INTO UserLanguages (telegram_id, language) VALUES (?, ?)",
                               (telegram_id, language))
            self.__db.commit()

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: telegram_id: {telegram_id}, language: {language}")
            return False

        else:
            return True

    def add_user_to_db(self, username: str, psw_salt: str, psw_hash: str, group_id: int, telegram_id: int) -> bool:
        """
        Insert a new user to the Users table
        """
        try:
            self.__cur.execute("""INSERT INTO Users
                                  VALUES(?, ?, ?, ?, ?, strftime('%d/%m/%Y', 'now', 'utc'))""",
                               (telegram_id, username, psw_salt, psw_hash, group_id,))
            self.__db.commit()

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: username: {username}, psw_salt: {psw_salt}, "
                                  f"psw_hash: {psw_hash}, group_id: {group_id}, telegram_id: {telegram_id}")
            return False

        else:
            return True

    @timeit
    def add_monetary_transaction_to_db(self, username: str, value: int, record_date: str, category,
                                       description: str) -> bool:
        """
        submits the "add_expense" and "add_income" forms to the database.
        :param username: the name of the user is making the changes.
        :param value: value of the deposited amount.
        :param category:
        :param description: optional parameter.
        :param record_date:
        """
        group_id: int = self.get_group_id_by_username(username)
        table_name = f"budget_{group_id}"
        total = self.get_last_sum_in_group(group_id)
        # In the table must be entered with the user's name in the text format because the user can later be deleted,
        # but their entries must remain in the table until it is deleted or cleared by the group owner.
        try:
            self.__cur.execute(f"""INSERT INTO {table_name} 
                                   VALUES (NULL, ? + ?, ?, ?, ?, ?, ?)""",
                (total, value, username, value, category, record_date, description))
            self.__db.commit()
        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: group id: {group_id}, table name: {table_name}, "
                                  f"username: {username}, value: {value}, description: {description}")
            return False
        else:
            return True

    def create_new_group(self, owner: int) -> str:
        """
        creating a new group in the Groups table and generate a new token for this group.
        :param owner: link to the telegram of the user who initiates the creation of the group.
        :return: token | empty string
        """
        token = get_token()
        token_is_unique: bool = self.check_token_is_unique(token)

        while not token_is_unique:  # checking the token for uniqueness
            token = get_token()
            token_is_unique = self.check_token_is_unique(token)

        try:
            self.__cur.execute("""INSERT INTO Groups 
                                  VALUES(NULL, ?, ?)""", (owner, token,))
            self.__db.commit()
        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: owner (telegram id): {owner}")
            return ""
        else:
            return token

# Methods for updating data in a database (UPDATE)

    def update_user_last_login(self, username: str) -> None:
        """
        Changes the user's last login time in the last_login column in the Users table.
        :return: None
        """
        try:
            self.__cur.execute("""UPDATE Users 
                                  SET last_login = strftime('%d/%m/%Y', 'now', 'utc')
                                  WHERE username = ?""", (username,))
            self.__db.commit()
        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: username: {username}")

    def update_group_owner(self, username: str, group_id: int) -> bool:
        """
        Changes the owner of a group to another user from that group.

        Additionally, there is a check for the presence of the specified user in the group.
        """
        try:
            telegram_id: int = self.get_telegram_id_by_username(username)
            if telegram_id and self.get_group_id_by_username(username) == group_id:
                self.__cur.execute("""UPDATE Groups 
                                      SET owner = ? 
                                      WHERE id = ?""", (telegram_id, group_id,))
                self.__db.commit()
                return True
            else:
                logger_database.error(f"! Update group owner, but the new owner is not in this group: "
                                      f"username: {username}, group id: {group_id}, telegram ID: {telegram_id}")
                return False
        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: username: {username}, group_id: {group_id}")
            return False

# Methods for deleting database data (DELETE)

    def delete_budget_entry_by_id(self, group_id: int, record_id: int) -> bool:
        """
        Removes an entry from the group budget table.
        :param group_id:
        :param record_id: Row id in the table
        :return: True - if the entry is found and successfully deleted, else - False
        """
        table_name = f"budget_{group_id}"
        try:
            self.__cur.execute(f"""DELETE FROM {table_name} 
                                   WHERE id = ?""", (record_id,))
            self.__db.commit()
        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Params: group id: {group_id}, record id: {record_id}, "
                                  f"table name: {table_name}")
            return False
        else:
            return True

    def delete_user_from_project(self, username: str) -> bool:
        """
        Removes a user from a group (not the owner)
        """
        try:
            group_id: int = self.get_group_id_by_username(username)
            if group_id:
                if not self.check_username_is_group_owner(username, group_id):
                    self.__cur.execute("""DELETE FROM Users 
                                          WHERE username = ?""", (username,))
                    self.__db.commit()
                else:
                    logger_database.error(f"Attempting to remove group owner separately from group, "
                                          f"username: {username}")
                    return False
        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: username: {username}")
            return False
        else:
            logger_database.info(f"User {username} has been removed from the database and from group #{group_id}")
            return True

    def delete_group_with_users(self, group_id: int) -> bool:
        """
        Deletes the group table along with all its members (including the owner)
        """
        try:
            self.__cur.execute("""DELETE FROM Users 
                                  WHERE group_id = ?""", (group_id,))
            self.__cur.execute("""DELETE FROM Groups 
                                  WHERE id = ?""", (group_id,))
            self.__cur.execute(f"""DROP TABLE budget_{group_id}""")
            self.__db.commit()

        except sqlite3.Error as err:
            logger_database.error(f"{str(err)}, Param: group id: {group_id}")
            return False

        else:
            logger_database.info(f"Group #{group_id} has been completely deleted")
            return True


def connect_db():
    """
    Connect to a database.
    :return: connection | None
    """
    try:
        conn = sqlite3.connect(db_path)  # type: ignore
        conn.row_factory = sqlite3.Row
        return conn

    except sqlite3.Error as err:
        logger_database.critical(f"Error connecting to database (app): {str(err)}")


def create_db() -> None:
    """
    Creates tables, using create_db.sql file describing their structures.
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()  # type: ignore

        with open("create_db.sql", 'r') as file:
            cursor.executescript(file.read())

        conn.commit()  # type: ignore
        close_db_main(conn)

    except sqlite3.Error as err:
        logger_database.error(f"{str(err)}")


def get_db():
    """
    connect to a database using a Flask application object.
    :return: connection
    """
    if not hasattr(g, "link_db"):
        g.link_db = connect_db()
    return g.link_db


def close_db_g(error) -> None:  # DO NOT REMOVE the parameter - without it the function generates an error
    """
    Closing a database connection using a Flask application object.
    """
    if hasattr(g, "link_db"):
        g.link_db.close()


def close_db_main(conn):
    """
    Closing a database connection.
    :return: None
    """
    if conn:
        conn.close()


def create_table_group(table_name: str) -> None:
    """
    creates a table in the database called budget_?
    (id, total, username, transfer, date_time, description)

    contains table_name_validator -> to protect against sql injection, validation of the table_name parameter is needed
    :param table_name: "budget_?"
    """
    try:
        if not re.match(r"^budget_[1-9]\d{0,4}$", table_name):
            raise ValueError("Possible SQL injection attempt")

        conn = sqlite3.connect(db_path)  # type: ignore
        cursor = conn.cursor()

        query = (f"CREATE TABLE IF NOT EXISTS {table_name} "
                 f"(id integer PRIMARY KEY AUTOINCREMENT, "
                 f"total integer NOT NULL, "
                 f"username text NOT NULL, "
                 f"transfer integer NOT NULL, "
                 f"category text NOT NULL, "
                 f"date text NOT NULL, "
                 f"description text CHECK(LENGTH(description) <= 50));")  # ?
        cursor.execute(query)

        conn.commit()
        conn.close()

    except sqlite3.Error as err:
        logger_database.error(f"{str(err)}, Table name: {table_name}")

    except ValueError as err:
        logger_database.error(f"{str(err)}, Value (table name): {table_name}")

    else:
        logger_database.info(f"Successful table creation: {table_name}")
