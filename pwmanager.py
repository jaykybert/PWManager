import getpass
import pyperclip
import sqlite3
import sys
import os

from cryptography.fernet import Fernet


TEMP_KEY = "fIhZ5DvAx-2sh18VLvRjt9WDiZll5ficgaP8GcfNJh4="
cipher = Fernet(TEMP_KEY)

# TODO: Allow update -s func to accept a shorthand name as the new service name where it is already defined as the shorthand.
# TODO: Clean up function structure - the get function needs to be made more efficient.
# TODO: Move encryption key to separate file.

# ---------- Query Functions ---------- #

def get_service_info(name):
    """ Return the service name (key) and shorthand using the input to
    find a row match in either the service name or shorthand columns.

    :param name: service name or shorthand.
    :return: the service name and shorthand stored in the db.
    """
    cursor.execute("SELECT service_name, shorthand_name FROM service WHERE service_name = ? OR shorthand_name = ?;",
                   (name, name))

    rec = cursor.fetchone()
    if rec is None:
        return None
    else:  # Record exists.
        return rec[0], rec[1]  # [0] = name, [1] = shorthand.


def get_service_name(name):
    cursor.execute("SELECT service_name FROM service WHERE service_name = ? OR shorthand_name = ?;", (name, name))

    rec = cursor.fetchone()
    if rec is None:
        return None
    else:
        return rec[0]


def check_service_unique(name):
    """ Check that the service name isn't already in use as
    another service name or shorthand.

    :param name: the name of the service.
    :return: true if no occurrences, false otherwise
    """
    cursor.execute("SELECT * FROM service WHERE service_name = ? OR shorthand_name = ?;", (name, name))

    return len(cursor.fetchall()) < 1


def check_shorthand_unique(shorthand):
    """ Check that the shorthand name isn't already in use as
    a service name or another shorthand.

    :param shorthand: the shorthand name.
    :return: true if no occurrences, false otherwise.
    """
    cursor.execute("SELECT * FROM service WHERE service_name = ? OR shorthand_name = ?;", (shorthand, shorthand))

    return len(cursor.fetchall()) < 1


def get_accounts_from_service(service):
    """ Get the account name(s) and password(s) for a specified service
    via name or shorthand.

    :param service: the service name or shorthand.
    :return: accounts, or None if there are no accounts.
    """
    cursor.execute("""SELECT account_name, account_pw FROM account WHERE service_name = (
                    SELECT service_name FROM service WHERE service_name = ? OR shorthand_name = ?);""",
                   (service, service))

    accounts = cursor.fetchall()
    if len(accounts) == 0:
        return None
    else:
        return accounts

# ---------- Main Menu ---------- #


def menu():
    """
    Menu - use cl arguments to go to specific functions.
    Service name and shorthand arguments are made lower case - avoids case sensitivity.
    """
    # Help screen if no arguments provided.
    if len(sys.argv) == 1:
        info()

    # Define a service.
    elif sys.argv[1].upper() == "DEFINE":
        if len(sys.argv) == 4:
            define(service=sys.argv[2].lower(),
                   shorthand=sys.argv[3].lower())  # Name and shorthand.
        elif len(sys.argv) == 3:
            define(sys.argv[2].lower())  # Just name.
        else:
            print("Invalid number of arguments. Provide a name and optional shorthand.")

    # Add an account for a specific service.
    elif sys.argv[1].upper() == "ADD":
        if len(sys.argv) != 3:
            print("Invalid number of arguments. Provide the name of the service for the account.")
        else:
            add(sys.argv[2].lower())

    # Update an existing service or account.
    elif sys.argv[1].upper() == "UPDATE":
        if len(sys.argv) == 4:
            if sys.argv[2].lower() == "-a":
                update_account(sys.argv[3].lower())
            elif sys.argv[2].lower() == '-s':
                update_service(sys.argv[3].lower())
            else:
                print("Invalid key. Use -a or -s.")
        else:
            print("Invalid number of arguments. Provide the key -s or -a, and the service.")

    # Retrieve the password of an account.
    elif sys.argv[1].upper() == "GET":
        if len(sys.argv) == 3:
            get(sys.argv[2].lower())
        else:
            print("Invalid number of arguments. Provide the service of the account.")

    # Delete an account or service.
    elif sys.argv[1].upper() == "REMOVE":
        if len(sys.argv) == 4:
            if sys.argv[2].lower() == "-a":
                remove_account(sys.argv[3].lower())
            elif sys.argv[2].lower() == "-s":
                remove_service(sys.argv[3].lower())
            else:
                print("Invalid key. Use -a or -s.")
        else:
            print("Invalid number of arguments. Provide the key -s or -a, and the service.")

    # List all services (and other information).
    elif sys.argv[1].upper() == "LS":
        alpha = False
        acc = False
        if "-a" in sys.argv:
            alpha = True
        if "-u" in sys.argv:
            acc = True
        ls(alpha, acc)

    # Clear the clipboard.
    elif sys.argv[1].upper() == "CLEAR":
        clear()

    # Display help information.
    elif sys.argv[1].upper() == "HELP":
        if len(sys.argv) == 3:  # Extra argument for specific information.
            info(sys.argv[2].upper())
        else:
            info()

    # Create the database tables.
    elif sys.argv[1].upper() == "CREATE":
        if len(sys.argv) == 3:
            if sys.argv[2].upper() == "CONFIRM":
                create()
            else:
                print("Type CONFIRM after CREATE.")
        else:
            print("Invalid number of arguments. Type CONFIRM after CREATE.")

    # Drop the database tables.
    elif sys.argv[1].upper() == "DROP":
        if len(sys.argv) == 3:
            if sys.argv[2].upper() == "CONFIRM":
                drop()
            else:
                print("Table deletion requires confirmation. Type CONFIRM after DROP.")
        else:
            print("Invalid number of arguments. Type CONFIRM after DROP.")

    # Rollback the database to the previous commit.
    elif sys.argv[1].upper() == "ROLLBACK":
        if len(sys.argv) == 3:
            if sys.argv[2].upper() == "CONFIRM":
                rollback()
            else:
                print("Rollback requires confirmation. Type CONFIRM after ROLLBACK.")
        else:
            print("Invalid number of arguments. Type CONFIRM after ROLLBACK.")

    else:
        print("Invalid keyword. Type HELP for more information.")


# ---------- Utility Functions ---------- #


def define(service, shorthand=None):
    """ Define a service using a name and optional shorthand.
    Add it to the database if there are no naming conflicts.
    Service name and shorthand are converted to lowercase to avoid case sensitivity.

    :param service: the name of the service.
    :param shorthand: the (optional) shorthand of the name, for ease of use.
    """

    if shorthand is None:  # Only check for name conflicts.
        cursor.execute("""SELECT * FROM service WHERE
                        service_name = ?
                        OR shorthand_name = ?;""", (service, service))
    else:  # Check for name and shorthand conflicts.
        cursor.execute("""SELECT * FROM service WHERE
                        service_name = ?
                        OR shorthand_name = ?
                        OR service_name = ?
                        OR shorthand_name = ?;""", (service, service, shorthand, shorthand))

    if len(cursor.fetchall()) != 0:  # Name/shorthand exist elsewhere.
        print("Name/shorthand already in use.")
    else:  # Service name and shorthand don't conflict. Create entry.
        if shorthand is None:
            cursor.execute("INSERT INTO service VALUES(?, null );", (service,))
            print("Service '%s' added." % service)
        else:
            cursor.execute("INSERT INTO service VALUES(?, ?);", (service, shorthand))
            print("Service '%s' (%s) added." % (service, shorthand))
        connection.commit()


def add(service):
    """ Check a service exists. Ask for username and password. Store the account.

    :param service: the service to create an account for (either name or shorthand).
    """
    cursor.execute("""SELECT service_name FROM service WHERE service_name = ? OR shorthand_name == ?;""",
                   (service, service))
    rec = cursor.fetchone()  # fetchone() returns tuple, not list of tuples. Indexing changes.

    if rec is None:
        print("Service doesn't exist. Define a service using the DEFINE keyword.")
    else:
        username = input("Enter Username\n > ")
        # Check email doesn't already exist for the service..
        cursor.execute("""SELECT * FROM account WHERE account_name = ? AND service_name = ?;""", (username, rec[0]))

        if len(cursor.fetchall()) == 0:  # Account doesn't exist.
            pw = getpass.getpass("Enter Password\n > ")
            # Encrypt password, convert type into string.
            encrypted = cipher.encrypt(str.encode(pw))
            encrypted_str = encrypted.decode("utf-8", "strict")
            # Add account.
            cursor.execute("""INSERT INTO account VALUES (?, ?, ?);""", (username, encrypted_str, rec[0]))
            connection.commit()
            print("Account added.")

        else:
            print("An account with this username already exists.")


def get(service):
    """ Get the account for a specific service using its name or shorthand.
    Multiple accounts require input to determine what account's password to return.

    :param service: name or shorthand of the service.
    """
    ser = get_service_name(service)
    if ser is None:
        print("Service doesn't exist.")
    else:
        rec = get_accounts_from_service(service)
        if rec is None:
            print("This service doesn't have any associated accounts.")
        elif len(rec) == 1:
            encrypted_pw = str.encode(rec[0][1])
            decrypted_pw = cipher.decrypt(encrypted_pw)
            pyperclip.copy(decrypted_pw.decode("utf-8", "strict"))
            print("Password copied to clipboard. (username: %s)" % rec[0][0])
        else:
            print("Which account? (enter number)")
            for i in range(0, len(rec)):
                print("[%d] %s" % (i+1, rec[i][0]))
            try:
                acc = int(input(" > "))
                try:
                    # Get encrypted password (string), convert to bytes, decrypt, convert back to string.
                    encrypted_pw = str.encode(rec[acc-1][1])
                    decrypted_pw = cipher.decrypt(encrypted_pw)
                    pyperclip.copy(decrypted_pw.decode("utf-8", "strict"))
                    print("Password copied to clipboard.")
                except IndexError:
                    print("Invalid choice.")
            except ValueError:
                print("Invalid input.")


def update_account(service):
    rec = get_accounts_from_service(service)
    if rec is None:
        print("Account or service doesn't exist.")
    elif len(rec) == 1:
        # One account exists. No need to check for conflicts.
        username = input("Enter Username\n > ")
        pw = getpass.getpass("Enter Password\n > ")
        cursor.execute("UPDATE account SET account_name = ?, account_pw = ? WHERE account_name = ?;",
                       (username, pw, rec[0][0]))
        connection.commit()
        print("Account updated. (%s)" % rec[0][0])

    else:  # Multiple accounts.
        print("Which account? (enter number)")
        for i in range(0, len(rec)):
            print("[%d] %s" % (i+1, rec[i][0]))

        try:
            acc = int(input(" > "))
            # check it exists.
            if acc-1 <= len(rec):
                username = input("Enter Username\n > ")

                service = get_service_name(service)

                # check other accounts don't have the same name - avoid the actual current one tho.
                if username != rec[acc-1][0]:  # entered different username.
                    cursor.execute("""SELECT * FROM account WHERE account_name = ? AND service_name = ?;""",
                                   (username, service))

                    check_account = cursor.fetchone()
                    if check_account is not None:
                        print("This username is already associated with another account.")
                        return

                pw = getpass.getpass("Enter Password\n > ")
                # Encrypt password, convert type into string.
                encrypted = cipher.encrypt(str.encode(pw))
                encrypted_str = encrypted.decode("utf-8", "strict")
                cursor.execute("UPDATE account SET account_name = ?, account_pw = ? WHERE account_name = ?;",
                               (username, encrypted_str, rec[acc-1][0]))
                connection.commit()
                print("Account updated. (%s -> %s)" % (rec[acc-1][0], username))

        except ValueError:
            print("Invalid input.")


def update_service(service):
    service_info = get_service_info(service)

    if service_info is None:
        print("Service doesn't exist.")
        return

    # Unpack stored service information.
    stored_name, stored_short = service_info

    new_name = input("New Service Name:\n > ").lower()

    """issue is here. we're checking that the entered name is different from the one stored.
    if it's the same, don't run the query to check its unique.
    but that means if the user enters the shorthand here, it will be checked in the query, and found (not unique)."""
    if new_name != stored_name:
        if not check_service_unique(new_name):  # New name conflicts with stored data.
            print("Name already in use elsewhere.")
            return

    new_short = input("New Shorthand Name: (press enter to skip)\n > ").lower()
    if new_short != stored_short:
        if not check_shorthand_unique(new_short):  # New shorthand conflicts with stored data.
            print("Shorthand already in use elsewhere.")
            return

    if new_short == "":  # Update without shorthand.
        cursor.execute("UPDATE service SET service_name = ?, shorthand_name = NULL WHERE service_name = ?;",
                       (new_name, stored_name))
        connection.commit()

    else:  # Update with shorthand.
        cursor.execute("UPDATE service SET service_name = ?, shorthand_name = ? WHERE service_name = ?;",
                       (new_name, new_short, stored_name))
        connection.commit()

    # Update references to the old name in the account table.
    cursor.execute("UPDATE account SET service_name = ? WHERE service_name = ?;", (new_name, stored_name))
    connection.commit()
    print("Service updated.")


def remove_service(service_lookup):
    """ Remove a service and any associated accounts.

    :param service_lookup: the service's name or shorthand.
    """
    service = get_service_name(service_lookup)
    if service is None:
        print("Service doesn't exist.")

    else:
        # Delete the accounts associated with the service and the service itself.
        cursor.execute("DELETE FROM account WHERE service_name = ?;", (service,))
        cursor.execute("DELETE FROM service WHERE service_name = ?;", (service,))
        connection.commit()
        print("Service (and associated accounts) deleted.")


def remove_account(service):
    """ Remove the account for a service. If there are multiple, let the user choose.

    :param service: the account's service name/shorthand.
    """
    accounts = get_accounts_from_service(service)
    if accounts is None:
        print("No related account.")
    elif len(accounts) == 1:
        cursor.execute("DELETE FROM account WHERE account_name = ?; ", (accounts[0][0],))
        connection.commit()
        print("Account deleted. (%s)" % accounts[0][0])
    else:
        print("Which account? (enter number)")
        for i in range(0, len(accounts)):
            print("[%d] %s" % (i+1, accounts[i][0]))
        try:
            acc = int(input(" > "))
            cursor.execute("DELETE FROM account WHERE account_name = ?;", (accounts[acc-1][0],))
            connection.commit()
            print("Account deleted. (%s)" % accounts[acc-1][0])

        except (ValueError, IndexError):
            print("Invalid input.")


def ls(alphabetical=False, acc=False):
    """ List all services and relevant information.

    :param alphabetical: display services alphabetically (on service name).
    :param acc: display all related account usernames.
    """

    # Display services and the related accounts.
    if acc:
        # Services (repeated) with all account usernames.
        cursor.execute("""SELECT service.service_name, service.shorthand_name, account.account_name
         FROM service INNER JOIN account ON service.service_name = account.service_name;""")

        rec = cursor.fetchall()
        if alphabetical:
            rec = sorted(rec, key=lambda tup: tup[0])

        for row in rec:
            name, shorthand, username = row
            if shorthand is None:
                print("  - %s: %s" % (name, username))
            else:
                print("  - %s (%s): %s" % (name, shorthand, username))

    # Just display services.
    else:
        cursor.execute("SELECT service_name, shorthand_name FROM service")
        rec = cursor.fetchall()
        if alphabetical:
            rec = sorted(rec, key=lambda tup: tup[0])

        for row in rec:
            name, shorthand = row
            if shorthand is None:
                print("  - %s" % name)
            else:
                print("  - %s (%s)" % (name, shorthand))


def clear():
    """ Empty the clipboard. """
    pyperclip.copy('')
    print("Clipboard cleared.")


def info(keyword=None):
    """ Display overview help information,
     or information for an optional keyword.
     """
    if keyword is None:  # Overview information.
        print("A  simple command line-based password management system."
              "To get started, use the CREATE keyword to setup the database.\n - Keywords:"
              "\n  - DEFINE\n  - ADD\n  - GET\n  - UPDATE\n  - REMOVE\n  - LS\n  - CLEAR\n  - CREATE\n  - DROP\n"
              "  - ROLLBACK\nType HELP KEYWORD for information on a specific keyword.")

    elif keyword == "DEFINE":
        print("-----> %s Help\nAdd a service with a name and optional shorthand keyword. Service name"
              " and shorthand must not already be defined.\n"
              "Form: DEFINE servicename\nForm: DEFINE servicename sn" % keyword)

    elif keyword == "ADD":
        print("-----> %s Help\nAdd an account for a specific service. Provide an email and password.\n"
              "The email must not already be associated with the specific service.\n"
              "Form: ADD (service name or shorthand)" % keyword)

    elif keyword == "GET":
        print("-----> %s Help\nCopy the password of an account to the clipboard using the service name or shorthand.\n"
              "Multiple accounts for a service require the user to choose the account.\n"
              "Form: GET (service name or shorthand)" % keyword)

    elif keyword == "UPDATE":
        print("-----> %s Help\nModify a service's or account's information. Service modification updates related"
              " accounts.\nService Form: UPDATE -s (servicename or shorthand)\n"
              "Account Form: UPDATE -a (servicename or shorthand)" % keyword)

    elif keyword == "REMOVE":
        print("-----> %s Help\nRemove a service or account. Removing a service deletes all associated accounts.\n"
              "Deleting an account from a service with multiple accounts will require the user to specify which one.\n"
              "Service Form: REMOVE -s (servicename or shorthand)\n"
              "Account Form: REMOVE -a (servicename or shorthand)" % keyword)

    elif keyword == "LS":
        print("-----> %s Help\nList all services and their respective shorthands.\nProvide -a to order alphabetically"
              " by service name, and -u to list all respective account usernames.\n"
              "Form: LS (optional -s and/or -u)" % keyword)

    elif keyword == "CLEAR":
        print("-----> %s Help\nClear the clipboard.\n"
              "Form: CLEAR" % keyword)

    elif keyword == "CREATE":
        print("-----> %s Help\nCreate the database tables in the current working directory."
              " Requires confirmation upon use.\n"
              "Form: CREATE confirm" % keyword)

    elif keyword == "DROP":
        print("-----> %s Help\nDrop the database tables. Requires confirmation upon use.\n"
              "Form: DROP confirm" % keyword)

    elif keyword == "ROLLBACK":
        print("-----> %s Help\nRollback the database to the previous commit.\n"
              "Form: ROLLBACK" % keyword)

    else:
        print("Invalid keyword.")


# ---------- Database Functions ---------- #

def create():
    """ Create the tables. """
    try:
        cursor.execute("""CREATE TABLE service (
                        service_name  text PRIMARY KEY,
                        shorthand_name text);""")

        cursor.execute("""CREATE TABLE account (
                        account_name text,
                        account_pw text,
                        service_name text NOT NULL,
                        FOREIGN KEY (service_name) REFERENCES service(service_name));""")

        connection.commit()
        print("Tables created.")
    except sqlite3.OperationalError:
        print("Tables already exist.")


def drop():
    """ Drop the tables. """
    try:
        cursor.execute("DROP TABLE account;")
        cursor.execute("DROP TABLE service;")
        connection.commit()
        print("Tables deleted.")

    except sqlite3.OperationalError:
        print("Tables don't exist.")


def rollback():
    """ Rollback the database. """
    connection.rollback()
    print("Database rollback successful.")


# ---------- Run ---------- #

if __name__ == "__main__":
    # Store the .db in the same folder as the pwmanager.py script.
    full_path = os.path.realpath(__file__)
    path = os.path.split(full_path)[0]  # [0] is path, [1] is file.
    os.path.join(path, "store.db")
    connection = sqlite3.connect(os.path.join(path, "store.db"))
    cursor = connection.cursor()
    menu()
