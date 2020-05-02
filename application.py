import requests
from bs4 import BeautifulSoup
import json
from flask import Flask, session, render_template, redirect, request, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bcrypt import Bcrypt
import datetime




app = Flask(__name__)
# Databse url goes here
DATABASE_URL = ""

GBOOKS_URL = "https://www.googleapis.com/books/v1/volumes?q="

# Configure session to use filesystem, it will be used later to contain login information
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# Secret key must be unique for every app
app.secret_key = ""

# Set up a module for hashing passwords
bcrypt = Bcrypt(app)

# Set up database
engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    books = db.execute('SELECT * FROM "books_list" LIMIT 24')
    return render_template("index.html",  books=books, session=session)


@app.route('/login', methods=["POST", "GET"])
def login():
    session.clear()
    if request.method == "POST":
        password = request.form.get("password")
        name = request.form.get("name")

        user = db.execute(
                'SELECT * FROM users WHERE  name=:name', {"name": name}
                ).fetchone()
        if bcrypt.check_password_hash(user.password, password):
            session["name"] = name
            return redirect(url_for('index'))
        else:
            return "Invalid credentials"

    if request.method == "GET":
        return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(request.referrer)

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name")

        user_name = db.execute(
                'SELECT * FROM users WHERE  name=:name', {"name": name}
                ).fetchone()

        user_email = db.execute(
                'SELECT * FROM users WHERE  email=:email', {"email": email}
                ).fetchone()
        #check if both email and login are avaliable
        if user_email is None and user_name is  None:
            hashed_password = bcrypt.generate_password_hash(password.encode('utf-8'))
            db.execute(
            "INSERT INTO users(email, password, name) VALUES (:email, :password, :name)", {"email":email, "password": hashed_password.decode('utf-8'), "name":name}
            )
            db.commit()
            session["name"] = name
            session["email"] = email
            return redirect(request.referrer)
        else:
            return "user already exists"
    if request.method == "GET":
        return render_template('register.html')

@app.route("/handler")
def handler():
    return "Thanks for registrating! Now you can leave comments!"


@app.route("/book/<id>")
def book(id):
    book = db.execute(
    f'SELECT * FROM books_list WHERE index={str(id)};'
    ).fetchone()

    #Get book description, thumbnail, categories and average rating from google books api
    r = requests.get(GBOOKS_URL + f'{ book.title }')
    j = json.loads(r.content)
    book_info = j["items"][0]["volumeInfo"]
    #If some info is missing handle it
    try:
        book_rating = book_info["averageRating"]
    except KeyError:
        book_rating = None
    try:
        book_description = book_info["description"]
    except KeyError:
        book_description ="No description"
    try:
        book_img = book_info["imageLinks"]["thumbnail"]
    except KeyError:
        book_img = "no image"
    try:
        book_categories = book_info["categories"]
    except KeyError:
        book_categories = []
    #form  a dict to structure all the info
    gbooks_data = {
        "book_info": book_info,
        "book_description" : book_description,
        "book_img" : book_img,
        "book_rating": book_rating,
        "book_categories": book_categories
    }

    books_comments = db.execute('SELECT * FROM comments WHERE book_id=:book_id', {"book_id": id}
    ).fetchall()
    return render_template("book.html", book=book, gbooks_data=gbooks_data, comments=books_comments)

@app.route("/addcomment", methods=["POST"])
def comment():
    comment_text = request.form.get("comment")
    book_id = request.form.get("book_id")
    if comment_text is not None:
        db.execute("INSERT INTO comments(text, book_id, author_name, date) VALUES (:text, :book_id, :author_id, :date)", {"text": comment_text, "book_id": book_id, "author_id": session["name"], "date":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        db.commit()
        return redirect(request.referrer)

@app.route("/authors")
def authors():
    authors = db.execute('SELECT author FROM "books_list" LIMIT 24').fetchall()
    return render_template("authors.html",  authors=authors)

@app.route("/author/<name>")
def author(name):
    author = db.execute('SELECT * FROM "books_list" WHERE author=:name', {"name": name}
    ).fetchall()
    return render_template("author.html",  author=author)

@app.route("/reviews")
def reviews():
    reviews = db.execute('SELECT * FROM "comments" LIMIT 50'
    ).fetchall()
    return render_template("reviews.html", reviews=reviews)

@app.route("/reviews/<name>")
def reviews_by_name(name):
    reviews = db.execute('SELECT * FROM "comments" WHERE "author_name"=:name LIMIT 50', {"name": name}
    ).fetchall()
    return render_template("reviews.html", reviews=reviews)


@app.route("/users/<name>")
def user(name):
    user = db.execute('SELECT * FROM "users" WHERE name=:name', {"name": name}
    ).fetchone()
    return render_template("user.html", user=user)


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("q")
    results = db.execute('SELECT * FROM "books_list" WHERE isbn=:query OR title=:query OR author=:query', {"query": query}
    ).fetchall()
    return render_template('search.html', results=results)



if __name__ == "__main__":
    app.run(debug=True)
