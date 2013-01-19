from flask import Flask, request, redirect, url_for, flash, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from flask_heroku import Heroku
app = Flask(__name__)
heroku = Heroku(app)
db = SQLAlchemy(app)

def id_generator(size=32, chars=(string.ascii_uppercase + string.ascii_lowercase
  + string.digits)):
  return ''.join(random.choice(chars) for x in range(size))

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  fbid = db.Column(db.String)
  mobile = db.Column(db.String(9)) #9 straight digits (no dashes)
  apikey = db.Column(db.String(32), unique=True)
  university_id = db.Column(db.Integer, db.ForeignKey('university.id'))

  def events():
    return Event.query.filter_by(or_(initiator=self.id, partner=self.id))

class University(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String)
  users = db.relationship('User', backref='university', lazy='dynamic')

class Event(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  category = db.Column(db.String(32))
  init_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
  startdate = db.Column(db.DateTime)
  enddate = db.Column(db.DateTime)
  messagedate = db.Column(db.DateTime)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user/new', methods=['POST'])
def create_user():
  fbid = request.args['fbid']
  uni = University.query.filter_by(name=request.args['name']).first()
  apikey = id_generator()

if __name__ == '__main__':
    app.run()
