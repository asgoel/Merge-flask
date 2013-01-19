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
  fbid = db.Column(db.String, unique=True)
  mobile = db.Column(db.String(9)) #9 straight digits (no dashes)
  apikey = db.Column(db.String(32), unique=True)
  university_id = db.Column(db.Integer, db.ForeignKey('university.id'))

  def events():
    return Event.query.filter_by(or_(initiator=self.id, partner=self.id))

  def __init__(self, fbid, apikey, university_id):
    self.fbid = fbid
    self.apikey = apikey
    self.university_id = university_id

class University(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String)
  users = db.relationship('User', backref='university', lazy='dynamic')

  def __init__(self, name):
    self.name = name

class Event(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  category = db.Column(db.String(32))
  init_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
  startdate = db.Column(db.DateTime)
  enddate = db.Column(db.DateTime)
  messagedate = db.Column(db.DateTime)

  def __init__(self, category, init_id, startdate, enddate):
    self.category = category
    self.init_id = init_id
    self.startdate = startdate
    self.enddate = enddate

@app.route('/')
def index():
    return render_template('index.html')

#returns empty string if there is a db error
@app.route('/user/new', methods=['POST'])
def create_user():
  fbid = request.args['fbid']
  uni = University.query.filter_by(name=request.args['name']).first()
  apikey = id_generator()
  user = User(fbid, apikey, uni)
  db.session.add(user)
  try:
    db.session.commit()
    return user.apikey
  except:
    return ""

#returns empty string if you get a db error
@app.route('university/new', methods=['POST'])
def create_uni():
  name = request.args['name']
  uni = University(name)
  db.session.add(uni)
  try:
    db.session.commit()
    return uni.name
  except:
    return ""


if __name__ == '__main__':
    app.run()
