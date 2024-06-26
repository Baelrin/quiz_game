import binascii
import getpass
import hashlib
import logging
import os
import sqlite3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class QuizGame:
    """A simple quiz game that interacts with a SQLite database to store questions, answers, and user scores."""

    def __init__(self, db_path):
        """Initializes the game by connecting to the specified SQLite database and creating required tables."""
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def __enter__(self):
        """Enables the use of the class in a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensures database connection is closed when exiting the context manager."""
        self.close()

    def create_tables(self):
        """Creates questions, users, and scores tables in the database if they don't already exist."""
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS questions
                               (question TEXT, answer TEXT)""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS users
                               (username TEXT PRIMARY KEY, password TEXT)""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS scores
                               (username TEXT, score INTEGER, FOREIGN KEY(username) REFERENCES users(username))""")
        self.conn.commit()

    def add_question(self, question, answer):
        """Inserts a new question and its answer into the database."""
        try:
            self.cursor.execute(
                "INSERT INTO questions (question, answer) VALUES (?, ?)",
                (question, answer),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error adding question: {e}")

    def register_user(self, username, password):
        """Registers a new user with the provided username and password after validating them."""
        if not username or not password:
            logging.error("Username or password cannot be empty.")
            return False
        if len(username) < 3 or len(password) < 8:
            logging.error(
                "Username must be at least 3 characters long, and password must be at least 8 characters long."
            )
            return False
        if not username.isalnum() or not password.isalnum():
            logging.error(
                "Username and password must contain only alphanumeric characters."
            )
            return False
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode("ascii")
        pwdhash = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, (salt + pwdhash).decode("ascii")),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.error(
                "Username already exists. Please choose a different username."
            )
            return False

    def login_user(self, username, password):
        """Attempts to log in a user with the provided username and password."""
        try:
            self.cursor.execute(
                "SELECT * FROM users WHERE username=?",
                (username,),
            )
            if user := self.cursor.fetchone():
                salt = user[1][:64]
                stored_password = user[1][64:]
                pwdhash = hashlib.pbkdf2_hmac(
                    "sha512", password.encode("utf-8"), salt.encode("ascii"), 100000
                )
                pwdhash = binascii.hexlify(pwdhash).decode("ascii")
                return pwdhash == stored_password
            else:
                return False
        except sqlite3.Error as e:
            logging.error(f"Error logging in user: {e}")
            return False

    def ask_question(self, question, correct_answer):
        """Prompts the player with a question and returns the result of their answer."""
        user_answer = input(question).lower().strip()
        if user_answer == correct_answer:
            print("Correct!")
            return 1
        else:
            print("Incorrect!")
            return 0

    def play(self, username):
        """Runs the quiz game, asking each stored question and recording the user's score."""
        print("Welcome to Digital_Odyssey!")
        self.cursor.execute("SELECT question, answer FROM questions")
        questions = self.cursor.fetchall()
        score = sum(
            self.ask_question(question, answer) for question, answer in questions
        )
        self.cursor.execute(
            "INSERT INTO scores (username, score) VALUES (?, ?)", (username, score)
        )
        self.conn.commit()
        print(f"You got {score} questions correct!")
        print(f"You got {str(score / len(questions) * 100)}%.")

    def close(self):
        """Closes the database connection."""
        self.conn.close()


if __name__ == "__main__":
    with QuizGame("quiz_game.db") as game:
        game.add_question("What does CPU stand for? ", "central processing unit")
        game.add_question("What does GPU stand for? ", "graphics processing unit")
        game.add_question("What does RAM stand for? ", "random access memory")
        game.add_question("What does PSU stand for? ", "power supply")
        game.add_question("What does SSD stand for? ", "solid state drive")
        game.add_question("What does HDD stand for? ", "hard disk drive")
        game.add_question("What does USB stand for? ", "universal serial bus")

        username = input("Enter your username: ")
        password = getpass.getpass("Enter your password: ")
        if not game.login_user(username, password):
            print("User not found. Registering new user.")
            game.register_user(username, password)

        game.play(username)
