from flask import Flask, request, redirect, url_for, flash, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from flask_heroku import Heroku
app = Flask(__name__)
heroku = Heroku(app)
db = SQLAlchemy(app)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run()
