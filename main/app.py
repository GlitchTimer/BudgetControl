from flask import Flask, render_template, request, session, redirect, url_for, flash, abort
import os
from datetime import timedelta
from dotenv import load_dotenv
from password_hashing import getting_hash, get_salt
import asyncio

# Database
from database_control import get_db, close_db_g, create_table_group, DatabaseQueries

# Validators
from validators.registration import registration_validation
from validators.description import description_validation
from validators.date import date_validation
from validators.correction_number import correction_number
from validators.token import token_validation

# Logging
from log_settings import setup_logger

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config.from_object(__name__)

# Get the secret key to encrypt the Flask session from an environment variable
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

app.teardown_appcontext(close_db_g)  # Disconnects the database connection after a query

# session lifetime in browser cookies
app.permanent_session_lifetime = timedelta(days=14)  # timedelta from datetime module

logger_app = setup_logger("logs/AppLog.log", "app_loger")


@app.route('/')
def homepage():
    """
    site's home page
    """
    return render_template("homepage.html", title="Budget control - Home page")


@app.route('/registration', methods=["GET", "POST"])
def registration():
    """
    user registration page
    """
    if request.method == "POST":
        username: str = request.form["username"]
        psw: str = request.form["password"]
        telegram_id: str = request.form["telegram-id"]
        token: str = request.form["token"]

        # If the token field is empty
        if len(request.form['token']) == 0:  # user creates a new group
            if asyncio.run(registration_validation(username, psw, telegram_id)):
                telegram_id: int = int(telegram_id)  # if registration_validator is passed, then it is int
                psw_salt: str = get_salt()  # generating salt for a new user
                dbase = DatabaseQueries(get_db())
                user_token: str = dbase.create_new_group(telegram_id)  # we get token of the newly created group

                if user_token:
                    group_id: int = token_validation(user_token)
                    create_table_group(f"budget_{group_id}")

                    if dbase.add_user_to_db(username, psw_salt, getting_hash(psw, psw_salt), group_id, telegram_id):
                        session.pop("userLogged", None)
                        logger_app.info(f"Successful registration: {username}. New group created: id={group_id}.")
                        flash("Registration completed successfully!", category="success")
                        flash(f"{username}, your token: {user_token}", category="success_token")

        # User is added to an existing group
        if len(token) == 32:
            if asyncio.run(registration_validation(username, psw, telegram_id)):
                dbase = DatabaseQueries(get_db())
                group_id: int = token_validation(token)  # getting group id by token
                group_not_full = dbase.check_limit_users_in_group(token)  # checking places in the group

                if group_id and group_not_full:
                    telegram_id: int = int(telegram_id)  # if registration_validator is passed, then it is int
                    psw_salt: str = get_salt()  # generating salt for a new user

                    if dbase.add_user_to_db(username, psw_salt, getting_hash(psw, psw_salt), group_id, telegram_id):

                        flash("Registration completed successfully!", category="success")
                        logger_app.info(f"Successful registration: {username}. Group: id={group_id}.")
                    else:
                        logger_app.info(f"Failed authorization  attempt: username = {username}, token = {token}.")
                        flash("Error creating user. Please try again and if the problem persists, "
                              "contact technical support.", category="error")
                else:
                    logger_app.info(f"The user entered an incorrect token or group is full: "
                                    f"username = {username}, token = {token}.")

                    flash("There is no group with this token or it is full. "
                          "Contact the group members for more information, or create your own group!",
                          category="error")

        # User made a mistake when entering the token
        if len(token) > 0 and len(token) != 32:
            logger_app.info(f"The user entered a token of incorrect length: {token}.")
            flash("Error - token length must be 32 characters", category="error")

    return render_template("registration.html", title="Budget control - Registration")


@app.route('/login', methods=["GET", "POST"])  # send password in POST request and in hash
def login():
    """
    user login page
    """
    session.permanent = True

    if "userLogged" in session:  # If the client has logged in before
        dbase = DatabaseQueries(get_db())
        username = session["userLogged"]
        user_is_exist: bool = dbase.check_username_is_exist(username)
        if user_is_exist:
            logger_app.info(f"Successful authorization (cookies): {session['userLogged']}.")
            return redirect(url_for("household", username=session["userLogged"]))
        else:
            session.pop("userLogged", None)  # removing the "userLogged" key from the session (browser cookies)
            flash("Your account was not found in the database. It may have been deleted.", category="error")
            logger_app.warning(f"Failed registration attempt from browser cookies: {username}.")

    # here the POST request is checked, and the presence of the user in the database is checked
    if request.method == "POST":
        username: str = request.form["username"]
        psw: str = request.form["password"]
        dbase = DatabaseQueries(get_db())
        psw_salt: str = dbase.get_salt_by_username(username)

        if psw_salt and dbase.auth_by_username(username, getting_hash(psw, psw_salt)):
            session["userLogged"] = username
            dbase.update_user_last_login(username)
            logger_app.info(f"Successful authorization: {username}.")
            return redirect(url_for("household", username=session["userLogged"]))
        else:
            flash("This user doesn't exist.", category="error")
        # request.args - GET, request.form - POST

    return render_template("login.html", title="Budget control - Login")


@app.route('/household/<username>', methods=["GET", "POST"])  # user's personal account
def household(username):
    """
    user's personal account with his group table
    """
    if "userLogged" not in session or session["userLogged"] != username:
        abort(401)

    dbase = DatabaseQueries(get_db())
    token: str = dbase.get_token_by_username(username)
    group_id: int = dbase.get_group_id_by_token(token)  # if token = "" -> group_id = 0

    if request.method == "POST":
        if "submit-button-1" in request.form or "submit-button-2" in request.form:  # Processing "Add to table" button
            value: str = request.form.get("transfer")
            value: int = correction_number(value)
            value: int = value
            record_date: str = request.form.get("record-date")
            record_date_is_valid: bool = asyncio.run(date_validation(record_date))
            category: str = request.form.get("category")
            description = request.form.get("description")
            if "submit-button-2" in request.form:
                value: int = value * (-1)

            if value:
                if record_date_is_valid:
                    record_date: str = f"{record_date[-2:]}/{record_date[5:7]}/{record_date[:4]}"  # DD/MM/YYYY
                    if description_validation(description):
                        if dbase.add_monetary_transaction_to_db(username, value, record_date, category, description):
                            logger_app.info(f"Successfully adding data to database: "
                                            f"operation: {request.form}"
                                            f"table: budget_{group_id}")

                            flash("Data added successfully.", category="success")
                        else:
                            logger_app.error(f"Error adding data to database: "
                                             f"operation: {request.form}"
                                             f"table: budget_{group_id}")

                            flash("Error adding data to database", category="error")
                    else:
                        flash("Description format is invalid", category="error")
                else:
                    flash("Date format is invalid", category="error")
            else:
                flash("The value format is invalid", category="error")

        elif "delete-record-submit-button" in request.form:
            record_id: str = request.form.get("record-id")
            record_id: int = correction_number(record_id)

            if not record_id or not dbase.check_id_is_exist(group_id, record_id):
                flash("Error. The format of the entered data is incorrect.", category="error")
            else:
                if dbase.delete_budget_entry_by_id(group_id, record_id):
                    logger_app.info(f"Successful deletion record from database: table: budget_{group_id}, "
                                    f"username: {username}, record id: {record_id}.")
                    flash("Record successfully deleted", category="success")
                else:
                    logger_app.info(f"Error deletion record from database: table: budget_{group_id}, "
                                    f"username: {username}, record id: {record_id}.")
                    flash("Error deleting a record from the database. Check that the entered data is correct.",
                          category="error")

    category_list = ["Supermarkets", "Restaurants", "Clothes", "Medicine", "Transport", "Devices", "Education",
                     "Services", "Travel", "Housing", "Transfers", "Investments", "Hobby", "Jewelry", "Sale", "Salary",
                     "Other"]
    headers: list[str] = ["№", "Total", "Username", "Transfer", "Category", "Date", "Description"]
    data: list = dbase.select_data_for_household_table(group_id, 15)  # In case of error group_id == 0 -> data = []

    return render_template("household.html", title=f"Budget control - {username}",
                           token=token, username=username, data=data, headers=headers, category_list=category_list)


@app.route('/settings/<username>')
def settings(username):
    """
    page with account and group settings (view/edit/delete)
    """
    if "userLogged" not in session or session["userLogged"] != username:
        abort(401)

    dbase = DatabaseQueries(get_db())
    token: str = dbase.get_token_by_username(username)
    group_id: int = dbase.get_group_id_by_token(token)
    group_owner: str = dbase.get_username_group_owner_by_token(token)
    group_users_data: list = dbase.get_group_users_data(group_id)
    return render_template("settings.html", title=f"Settings - {username}", token=token,
                           group_owner=group_owner, group_users_data=group_users_data)


@app.route('/conditions')
def conditions():
    """
    privacy Policy page
    """
    return render_template("conditions.html", title="Usage Policy", site_name="", site_url="",
                           contact_email="", contact_url="")


@app.route('/logout', methods=['GET'])
def logout():
    """
    removing session from browser cookies
    """
    logger_app.info(f"Successful logout: {session['userLogged']}.")
    session.pop("userLogged", None)  # removing the "userLogged" key from the session (browser cookies)
    return redirect(url_for('login'))  # redirecting the user to another page, such as the homepage


@app.errorhandler(401)
def page_not_found(error):
    return render_template("error401.html", title="UNAUTHORIZED"), 401


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error404.html", title="PAGE NOT FOUND"), 404


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')  # change on False before upload on server
