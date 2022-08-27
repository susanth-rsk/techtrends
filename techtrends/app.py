import sqlite3
import logging
import sys
from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort


# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    metrics_dict['db_connection_count'] +=1
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Function to check if the db connection exists
def verify_db_connection():
    try:
        connection = get_db_connection()
        connection.close()
    except:
        raise Exception("Connection to database failed")

# Function to check if posts table exists
def verify_posts_table():
    try:  
        connection = get_db_connection()
        connection.execute('SELECT 1 FROM posts').fetchone()
        connection.close()
    except:
        raise Exception("'posts' table does not exists" )

# Function to get the number of articles and number of connections in use
def get_no_of_posts(metrics_dict):
    connection = get_db_connection()
    posts_count = connection.execute("""
                                     SELECT count(*)
                                     FROM posts
                                     """).fetchone()
    metrics_dict['posts_count'] = posts_count[0]
    connection.close()
        

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.error('Error 404: Article id {} does not exist'.format(post_id))
        return render_template('404.html'), 404
    else:
        app.logger.info('Retrieved requested article: %s', post['title'])
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info('About Us page was successfully retrieved')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            app.logger.error('Article could not be created as no title was provided')
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()
            app.logger.info('New article created: %s', title)
            return redirect(url_for('index'))

    return render_template('create.html')

# Define the health check
@app.route('/healthz')
def healthz():
    health_response = {'result' : 'OK - healthy',
                       'details' : 'None'}
    health_status_code = 200
    
    try:
        verify_db_connection()
        verify_posts_table()
    except Exception as excep:
        health_response['result'] = 'ERROR - unhealthy'
        health_response['details'] = str(excep)
        health_status_code = 500
    
    response = app.response_class(
        response = json.dumps(health_response),
        status = health_status_code,
        mimetype = 'application/json')

    app.logger.info('Healthz request successfull')    
    return response

# Define metrics
@app.route('/metrics')
def metrics():
    get_no_of_posts(metrics_dict)
    response = app.response_class(
        response = json.dumps(metrics_dict),
        status = 200,
        mimetype = 'application/json')
    app.logger.info('Metrics request successfull')
    return response

# start the application on port 3111
if __name__ == "__main__":
    logging.basicConfig(level = logging.DEBUG,
                        format='%(asctime)s : %(name)s : %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    dual_handlers = [stdout_handler, stderr_handler]
    metrics_dict = {'db_connection_count' : 0,
                    'posts_count' : None}
    app.run(host='0.0.0.0', port='3111')
