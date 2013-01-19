from flask import Flask, request, redirect, url_for, flash, render_template, json, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask_heroku import Heroku
import string
import random
from datetime import datetime
import time
app = Flask(__name__)
heroku = Heroku(app)
db = SQLAlchemy(app)

def id_generator(size=32, chars=(string.ascii_uppercase + string.ascii_lowercase
  + string.digits)):
  return ''.join(random.choice(chars) for x in range(size))

class Person(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  fbid = db.Column(db.String, unique=True)
  mobile = db.Column(db.String(16)) # consecutive digits, no dashes / parens
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
  users = db.relationship('Person', backref='university', lazy='dynamic')

  def __init__(self, name):
    self.name = name

class Event(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  category = db.Column(db.String(32))
  init_id = db.Column(db.Integer, db.ForeignKey('person.id'))
  partner_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True)
  university_id = db.Column(db.Integer, db.ForeignKey('university.id'))
  startdate = db.Column(db.DateTime)
  enddate = db.Column(db.DateTime)
  messagedate = db.Column(db.DateTime, nullable=True)

  def __init__(self, category, init_id, university_id, startdate, enddate):
    self.category = category
    self.init_id = init_id
    self.university_id = university_id
    self.startdate = startdate
    self.enddate = enddate

@app.route('/')
def index():
    return render_template('index.html')

#returns empty string if there is a db error
@app.route('/person/new', methods=['POST'])
def create_user():
  data = request.json
  fbid = data["fbid"]
  uni = University.query.filter_by(name=data["name"]).first()
  apikey = id_generator()
  user = Person(fbid, apikey, uni.id)
  db.session.add(user)
  try:
    db.session.commit()
    data = {
      "apikey" : apikey,
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "apikey" : "",
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

#updates a user's phone number
@app.route('/person/mobile', methods=['POST'])
def update_mobile():
  data = request.json
  apikey = data["apikey"]
  num = data["mobile"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "apikey" : ""
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
    
  user.mobile = num
  db.session.add(user)
  try:
    db.session.commit()
    data = {
      "apikey" : apikey
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "apikey" : ""
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

#returns empty string if you get a db error
#TODO: add app API authentication
@app.route('/university/new', methods=['POST'])
def create_uni():
  data = request.json
  name = data["name"]
  uni = University(name)
  db.session.add(uni)
  try:
    db.session.commit()
    data = {
      "name" : name,
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "name" : "",
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

# creates a new event for a given user
# TODO: fix start and end dates to cooperate
@app.route('/event/new', methods=['POST'])
def create_event():
  data = request.json
  apikey = data["apikey"]
  initiator = Person.query.filter_by(apikey=apikey).first()
  if initiator is None:
    data = {
      "apikey" : "",
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  category = data["category"]
  start = datetime.fromtimestamp(int(data["startdate"]))
  end = datetime.fromtimestamp(int(data["enddate"]))
  event = Event(category, initiator.id, initiator.university_id, start, end)
  
  db.session.add(event)
  try:
    db.session.commit()
    data = {
      "apikey" : apikey,
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "apikey" : ""
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

# the current user joins an event
@app.route('/event/join', methods=['POST'])
def join_event():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "apikey" : "",
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event = Event.query.filter_by(id=int(data["event_id"])).first()
  if event is None:
    data = {
      "apikey" : "",
      "error" : "could not find event"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event.partner_id = user.id
  db.session.add(event)
  try:
    db.session.commit()
    data = {
      "apikey" : apikey
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "apikey" : ""
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

# grabs all events currently going on from the user's university in a given category
@app.route('/event', methods=['GET'])
def get_events():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "apikey" : "",
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  category = data["category"]
  events = Event.query.filter_by(university_id=user.university_id, category=category).all()
  jsondict = {}
  jsondict["events"] = []
  for event in events:
    eventjson = {}
    eventjson["id"] = str(event.id)
    eventjson["category"] = event.category
    initiator = Person.query.filter_by(id = event.init_id).first()
    eventjson["init"] = initiator.fbid
    partner = Person.query.filter_by(id=event.partner_id).first()
    if partner is not None:
      eventjson["partner"] = partner.fbid
    eventjson["startdate"] = time.mktime(event.startdate.timetuple())
    eventjson["enddate"] = time.mktime(event.enddate.timetuple())
    if event.messagedate is not None:
      eventjson["messagedate"] = time.mktime(event.messagedate.timetuple())
    jsondict["events"].append(eventjson);
  resp = jsonify(jsondict)
  resp.status_code = 200
  return resp

# our participant text messaged the event host
@app.route('/event/text', methods=['POST'])
def event_text():
  data = request.json
  apikey = data["apikey"]
  event = Event.query.filter_by(id=int(data["event_id"])).first()
  if event is None:
    data = {
      "apikey" : "",
      "error" : "Could not find event"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  user = Person.query.filter_by(apikey=apikey, id=int(event.partner_id)).first()
  if user is None:
    data = {
      "apikey" : "",
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event.messagedate = datetime.now()
  db.session.add(event)
  try:
    db.session.commit()
    data = {
      "apikey" : apikey
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "apikey" : ""
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

# return a hash of all events for which a user must be prompted on
@app.route('/event/prompt', methods=['GET'])
def prompt_on_event():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "apikey" : "",
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  events = Event.query.filter_by(partner_id=user.id, messagedate < datetime.now() - datetime.timedelta(minutes=5)).all() # remind if prompted > 5 minutes ago
  jsondict = {}
  jsondict["events"] = []
  for event in events:
    eventjson = {}
    eventjson["category"] = event.category
    initiator = Person.query.filter_by(id = event.init_id).first()
    eventjson["init"] = initiator.fbid
    partner = Person.query.filter_by(id=event.partner_id).first()
    if partner is not None:
      eventjson["partner"] = partner.fbid
    eventjson["startdate"] = time.mktime(event.startdate.timetuple())
    eventjson["enddate"] = time.mktime(event.enddate.timetuple())
    if event.messagedate is not None:
      eventjson["messagedate"] = time.mktime(event.messagedate.timetuple())
    jsondict["events"].append(eventjson);
  resp = jsonify(jsondict)
  resp.status_code = 200
  return resp
  
if __name__ == '__main__':
    app.run(debug=True)
