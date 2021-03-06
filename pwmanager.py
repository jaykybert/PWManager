from cryptography.fernet import Fernet
import getpass
import os
import pyperclip
import sqlite3
import sys


# TODO: Add print statement if ls is used and returns no results.

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


def encrypt(pw):
    """ Encrypt a password using the stored key.

    :param pw: the password to encrypt.
    :return: the encrypted password.
    """
    cursor.execute("""SELECT key FROM encryption;""")
    key = cursor.fetchone()[0]
    cipher = Fernet(key)
    return cipher.encrypt(str.encode(pw))


def decrypt(enc_pw):
    """ Decrypt a password using the stored key.

    :param enc_pw: the password to be decrypted.
    :return: the decrypted password (in bytes).
    """
    cursor.execute("""SELECT key FROM encryption;""")
    key = cursor.fetchone()[0]
    cipher = Fernet(key)
    return cipher.decrypt(enc_pw)


def tables_exist():
    """ Check if the database tables exist inside the database.

    :return: true if they exist, false otherwise.
    """

    cursor.execute("""SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'encryption';""")
    return len(cursor.fetchall()) > 0


# ---------- Main Menu ---------- #


def menu():
    """ Menu - use cl arguments to go to specific functions.
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

            elif sys.argv[2].lower() == "-b":
                remove_backup(sys.argv[3])
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
                create(connection)
            else:
                print("Type CONFIRM after CREATE.")
        else:
            print("Invalid number of arguments. Type CONFIRM after CREATE.")

    # Drop the database tables.
    elif sys.argv[1].upper() == "DROP":
        if len(sys.argv) == 3:
            if sys.argv[2].upper() == "CONFIRM":
                drop(connection)
            else:
                print("Table deletion requires confirmation. Type CONFIRM after DROP.")
        else:
            print("Invalid number of arguments. Type CONFIRM after DROP.")

    elif sys.argv[1].upper() == "BACKUP":
        if len(sys.argv) == 2:
            backup()
        elif len(sys.argv) == 3:
            backup(sys.argv[2])
        elif len(sys.argv) == 4 & sys.argv[2].upper() == "REMOVE":
            # TODO: Remove the backup at the specified file path.
            #  CM-Line Form 1: pw backup remove filepath   - verbose
            #  CM-Line Form 2: pw remove -b filepath   - makes use of the remove keyword already defined.
            #    ... so, just alter the "if arg == remove" part.
            #    ... consider the db connection, what happens if the filepath doesn't have a db?
            #    - we dont want to create a new one.
            print("")

        else:
            print("Invalid number of arguments.")

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
    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

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
    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

    cursor.execute("""SELECT service_name FROM service WHERE service_name = ? OR shorthand_name == ?;""",
                   (service, service))
    rec = cursor.fetchone()

    if rec is None:
        print("Service doesn't exist. Define a service using the DEFINE keyword.")
    else:
        username = input("Enter Username\n > ")
        # Check email doesn't already exist for the service..
        cursor.execute("""SELECT * FROM account WHERE account_name = ? AND service_name = ?;""", (username, rec[0]))

        if len(cursor.fetchall()) == 0:  # Account doesn't exist.
            pw = getpass.getpass("Enter Password\n > ")
            # Encrypt password, convert type into string.
            enc_pw = encrypt(pw)

            # Add account.
            cursor.execute("""INSERT INTO account VALUES (?, ?, ?);""", (username, enc_pw, rec[0]))
            connection.commit()
            print("Account added.")

        else:
            print("An account with this username already exists.")


def get(service):
    """ Get the account for a specific service using its name or shorthand.
    Multiple accounts require input to determine what account's password to return.

    :param service: name or shorthand of the service.
    """
    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

    ser = get_service_name(service)
    if ser is None:
        print("Service doesn't exist.")
    else:
        rec = get_accounts_from_service(service)
        if rec is None:
            print("This service doesn't have any associated accounts.")
        elif len(rec) == 1:
            pw_bytes = decrypt(rec[0][1])
            pyperclip.copy(pw_bytes.decode("utf-8", "strict"))
            print("Password copied to clipboard. (username: %s)" % rec[0][0])
        else:
            print("Which account? (enter number)")
            for i in range(0, len(rec)):
                print("[%d] %s" % (i+1, rec[i][0]))
            try:
                acc = int(input(" > "))
                try:
                    pw_bytes = decrypt(rec[acc-1][1])
                    pyperclip.copy(pw_bytes.decode("utf-8", "strict"))
                    print("Password copied to clipboard.")
                except IndexError:
                    print("Invalid choice.")
            except ValueError:
                print("Invalid input.")


def update_account(service):
    """ Update an account with a new username and password.

    :param service: the service to which the account belongs.
    """

    def write_update(new_name, pw, old_name):
        """ Write the updated information to the database.

        :param new_name: The new account username.
        :param pw: The new account password.
        :param old_name: The old account username.
        """
        cursor.execute("UPDATE account SET account_name = ?, account_pw = ? WHERE account_name = ?;",
                       (new_name, pw, old_name))
        connection.commit()
        print("Account updated. (%s -> %s)" % (old_name, new_name))

    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

    rec = get_accounts_from_service(service)
    if rec is None:
        print("Account or service doesn't exist.")
    elif len(rec) == 1:
        # One account exists. No need to check for conflicts.
        username = input("Enter Username\n > ")
        pw = getpass.getpass("Enter Password\n > ")
        enc_pw = encrypt(pw)

        write_update(username, enc_pw, rec[0][0])

    else:  # Multiple accounts.
        print("Which account? (enter number)")
        for i in range(0, len(rec)):
            print("[%d] %s" % (i+1, rec[i][0]))

        try:
            acc = int(input(" > "))
            # Check it exists.
            if acc-1 <= len(rec):
                username = input("Enter Username\n > ")

                # If the username is different from the current one, check that it doesn't conflict.
                if username != rec[acc-1][0]:  # entered different username.
                    cursor.execute("""SELECT * FROM account WHERE account_name = ? AND service_name = ?;""",
                                   (username, service))
                    check_account = cursor.fetchone()
                    if check_account is not None:
                        print("This username is already associated with another account.")
                        return

                pw = getpass.getpass("Enter Password\n > ")
                enc_pw = encrypt(pw)
                write_update(username, enc_pw, rec[acc-1][0])
        except ValueError:
            print("Invalid input.")


def update_service(service):
    """ Update a service with a new name and (optional) shorthand.

    :param service: the service to be updated.
    """
    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

    service_info = get_service_info(service)

    if service_info is None:
        print("Service doesn't exist.")
        return

    # Unpack stored service information.
    stored_name, stored_short = service_info

    new_name = input("New Service Name:\n > ").lower()
    # Avoid running elif. Indicative of poor structure but works for now.
    if new_name == stored_short:
        pass

    elif new_name != stored_name:
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
    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

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

    def execute_remove(account_name):
        """ Remove the provided account from the database.

        :param account_name: the account to be deleted.
        """
        cursor.execute("DELETE FROM account WHERE account_name = ?;", (account_name,))
        connection.commit()
        print("Account deleted. (%s)" % account_name)

    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

    accounts = get_accounts_from_service(service)
    if accounts is None:
        print("No related account.")

    elif len(accounts) == 1:
        execute_remove(accounts[0][0])

    else:
        print("Which account? (enter number)")
        for i in range(0, len(accounts)):
            print("[%d] %s" % (i+1, accounts[i][0]))
        try:
            acc = int(input(" > "))
            execute_remove(accounts[acc-1][0])
        except ValueError:
            print("Invalid input.")
        except IndexError:
            print("Number out of bounds.")


def remove_backup(filepath):
    """ Delete the database file at the specified filepath.

    :param filepath: the filepath to the .db file.
    """
    backup_path = os.path.join(filepath, "store_backup.db")
    try:
        os.remove(backup_path)
        print("Backup removed successfully.")
    except FileNotFoundError:
        print("The file doesn't exist at the specified filepath.")


def ls(alphabetical=False, acc=False):
    """ List all services and relevant information.

    :param alphabetical: display services alphabetically (on service name).
    :param acc: display all related account usernames.
    """
    if not tables_exist():
        print("Tables do not exist. Type CREATE CONFIRM to create the tables.")
        return

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
        print(" A simple command line-based password management system.\n"
              " To get started, use the CREATE keyword to setup the database along with CONFIRM.\n Then, define"
              " a service using DEFINE, add accounts to a service using ADD, and get the password to an account"
              " using GET.\n Below are all keywords. Type HELP KEYWORD for more information on a particular keyword."
              "\n  - DEFINE\n  - ADD\n  - GET\n  - UPDATE\n  - REMOVE\n  - LS\n  - CLEAR\n  - CREATE\n  - DROP"
              "\n  - BACKUP")

    elif keyword == "DEFINE":
        print("-----> %s Help\n Add a service with a name and optional shorthand keyword. Service name"
              " and shorthand must not already be defined.\n Service name and shorthand can be the same.\n"
              " Form: DEFINE servicename\n Form: DEFINE servicename shorthand" % keyword)

    elif keyword == "ADD":
        print("-----> %s Help\n Add an account for a specific service. Provide a username and password.\n"
              " The username must not already be associated with the specific service.\n"
              " Form: ADD (service name or shorthand)" % keyword)

    elif keyword == "GET":
        print("-----> %s Help\n Copy the password of an account to the clipboard using the service name or shorthand.\n"
              " Multiple accounts for a service require the user to choose the account.\n"
              " Form: GET (service name or shorthand)" % keyword)

    elif keyword == "UPDATE":
        print("-----> %s Help\n Modify a service's or account's information. Service modification updates associated"
              " accounts.\n Service Form: UPDATE -s (servicename or shorthand)\n"
              " Account Form: UPDATE -a (servicename or shorthand)" % keyword)

    elif keyword == "REMOVE":
        print("-----> %s Help\n Remove a service or account. Removing a service deletes all associated accounts.\n"
              " Deleting an account from a service with multiple accounts will require the user to specify the account."
              "\n Service Form: REMOVE -s (servicename or shorthand)\n"
              " Account Form: REMOVE -a (servicename or shorthand)" % keyword)

    elif keyword == "LS":
        print("-----> %s Help\n List all services and their respective shorthands.\n Provide -a to order alphabetically"
              " by service name, and -u to list all respective account usernames.\n"
              " Form: LS (optional -s and/or -u)" % keyword)

    elif keyword == "CLEAR":
        print("-----> %s Help\n Clear the clipboard.\n"
              " Form: CLEAR" % keyword)

    elif keyword == "CREATE":
        print("-----> %s Help\n Create the database tables in the PWManager directory."
              " Requires confirmation upon use.\n"
              " Form: CREATE confirm" % keyword)

    elif keyword == "DROP":
        print("-----> %s Help\n Drop the database tables. Requires confirmation upon use.\n"
              " Form: DROP confirm" % keyword)

    elif keyword == "BACKUP":
        print("-----> %s Help\nBackup the database. Pass an optional filepath. Otherwise defaults to same directory.\n"
              "Form: BACKUP (optional filepath)" % keyword)

    else:
        print("Invalid keyword.")


# ---------- Database Functions ---------- #

def create(db_connection):
    """ Create the tables. Generate a key, store in db.

    :param db_connection: the database connection which will store the tables."""
    db_cursor = db_connection.cursor()
    try:
        db_cursor.execute("""CREATE TABLE service (
                        service_name  text PRIMARY KEY,
                        shorthand_name text);""")

        db_cursor.execute("""CREATE TABLE account (
                        account_name text,
                        account_pw text,
                        service_name text NOT NULL,
                        FOREIGN KEY (service_name) REFERENCES service(service_name));""")

        db_cursor.execute("""CREATE TABLE encryption (key text);""")

        # Generate and store key.
        key = Fernet.generate_key()
        db_cursor.execute("""INSERT INTO encryption VALUES(?)""", (key,))

        db_connection.commit()
        print("Tables created.")

    except sqlite3.OperationalError:
        print("Tables already exist.")


def drop(db_connection):
    """ Drop the tables.

     :param db_connection: the database connection which will drop the tables."""
    db_cursor = db_connection.cursor()

    try:
        db_cursor.execute("DROP TABLE account;")
        db_cursor.execute("DROP TABLE service;")
        db_cursor.execute("DROP TABLE encryption;")
        db_connection.commit()
        print("Tables deleted.")

    except sqlite3.OperationalError:
        print("Tables don't exist.")


def backup(filepath=None):
    """
    Create a copy of the database at the provided filepath.
    :param filepath: The filepath where the backup will be created.
    """

    if filepath is None:
        # Default to the PWManager directory.
        b_file_path = os.path.realpath(__file__)
        filepath = os.path.split(b_file_path)[0]
    try:
        b_connection = sqlite3.connect(os.path.join(filepath, "store_backup.db"))
        create(b_connection)  # Create the tables in the backup database.
        b_cursor = b_connection.cursor()

        # Copy data from SERVICE table.
        cursor.execute("SELECT * FROM service;")
        for row in cursor.fetchall():
            b_cursor.execute("INSERT INTO service VALUES(?, ?)", (row[0], row[1]))
        print("Copied service data... ", end="")

        # Copy data from ACCOUNT table.
        cursor.execute("SELECT * FROM account;")
        for row in cursor.fetchall():
            b_cursor.execute("INSERT INTO account VALUES(?, ?, ?)", (row[0], row[1], row[2]))
        print("Copied account data... ", end="")

        # Copy data from ENCRYPTION table.
        cursor.execute("SELECT * FROM encryption;")
        for row in cursor.fetchall():
            b_cursor.execute("INSERT INTO encryption VALUES(?)", (row[0],))
        print("Copied encryption data...")

        b_connection.commit()
        print("Backup complete.")

    except sqlite3.OperationalError:
        print("Invalid filepath provided.")
        # This is a catch-all. Also excepts when you backup without having created the store.db tables.


# ---------- Run ---------- #

if __name__ == "__main__":
    full_path = os.path.realpath(__file__)
    path = os.path.split(full_path)[0]  # [0] is path, [1] is file.
    connection = sqlite3.connect(os.path.join(path, "store.db"))
    cursor = connection.cursor()
    menu()
