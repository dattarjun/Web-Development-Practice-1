from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management and flash messages
bcrypt = Bcrypt(app)

def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",  # MySQL username
            password="root",  # MySQL password
            database="user_registration2"
        )
        if connection.is_connected():
            print("Connected to MySQL database")
    except Error as e:
        print(f"The error '{e}' occurred")
        flash(f"Database connection failed: {e}", "danger")
    
    return connection

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        connection = create_connection()
        if connection is None:
            flash("Failed to connect to the database. Please try again later.", "danger")
            return redirect(url_for('register'))
        
        cursor = connection.cursor()

        try:
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("Email is already registered. Please use a different email or login.", "danger")
                return redirect(url_for('register'))

            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", 
                           (username, email, hashed_password))
            connection.commit()
            flash("User registered successfully!", "success")
            return redirect(url_for('login'))
        except Error as e:
            flash(f"Error: {e}", "danger")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash("Please fill out both fields", "danger")
            return redirect(url_for('login'))

        connection = create_connection()
        if connection is None:
            flash("Failed to connect to the database. Please try again later.", "danger")
            return redirect(url_for('login'))
        
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and bcrypt.check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash("Login successful!", "success")
                return redirect(url_for('welcome'))
            else:
                flash("Invalid credentials", "danger")
        except Error as e:
            flash(f"Database error: {e}", "danger")
        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')


@app.route('/welcome')
def welcome():
    if 'user_id' in session:
        username = session['username']
        return render_template('welcome.html', username=username)
    else:
        flash("You need to log in first!", "danger")
        return redirect(url_for('login'))


@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/community')
def community():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
    posts = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('community.html', posts=posts)

@app.route('/create-post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']

        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s)", 
                       (user_id, title, content))
        connection.commit()
        cursor.close()
        connection.close()
        
        return redirect(url_for('community'))
    return render_template('create_post.html')

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    if request.method == 'POST':
        if 'comment' in request.form:
            content = request.form['comment']
            user_id = session['user_id']
            cursor.execute("INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)", 
                           (post_id, user_id, content))
            connection.commit()
        elif 'vote' in request.form:
            vote_type = request.form['vote']
            user_id = session['user_id']
            cursor.execute("INSERT INTO votes (post_id, user_id, vote_type) VALUES (%s, %s, %s)", 
                           (post_id, user_id, vote_type))
            connection.commit()

    cursor.execute("SELECT * FROM comments WHERE post_id = %s", (post_id,))
    comments = cursor.fetchall()
    
    cursor.execute("SELECT SUM(vote_type = 'upvote') - SUM(vote_type = 'downvote') AS score FROM votes WHERE post_id = %s", 
                   (post_id,))
    vote_score = cursor.fetchone()['score']

    cursor.close()
    connection.close()
    
    return render_template('post_detail.html', post=post, comments=comments, vote_score=vote_score)

@app.route('/profile')
def profile():
    user_id = session['user_id']
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM posts WHERE user_id = %s", (user_id,))
    posts = cursor.fetchall()
    
    cursor.execute("SELECT * FROM comments WHERE user_id = %s", (user_id,))
    comments = cursor.fetchall()
    
    cursor.execute("SELECT * FROM votes WHERE user_id = %s", (user_id,))
    votes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('profile.html', posts=posts, comments=comments, votes=votes)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
