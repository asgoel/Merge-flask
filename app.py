from flask import Flask, request, redirect, url_for, flash, render_template, json, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask_heroku import Heroku
import string
import random
from datetime import datetime, timedelta
import time
import os
from twilio.rest import TwilioRestClient
import twilio.twiml
app = Flask(__name__)
heroku = Heroku(app)
db = SQLAlchemy(app)

universal = os.environ['UNIVERSAL_API']
account_sid = "AC32798c5f8600bb6d158e63181eb705e1"
auth_token = "3ba6672b64fb89178bfeaef60ce34061"
def id_generator(size=32, chars=(string.ascii_uppercase + string.ascii_lowercase
  + string.digits)):
  return ''.join(random.choice(chars) for x in range(size))

class Person(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  fbid = db.Column(db.String, unique=True)
  name = db.Column(db.String(128)) # user's name on Facebook
  mobile = db.Column(db.String(16)) # consecutive digits, no dashes / parens
  apikey = db.Column(db.String(32), unique=True)
  university_id = db.Column(db.Integer, db.ForeignKey('university.id'))
  verified = db.Column(db.Boolean, default=False)

  def events():
    return Event.query.filter_by(or_(initiator=self.id, partner=self.id))

  def __init__(self, fbid, name, apikey, university_id):
    self.fbid = fbid
    self.name = name
    self.apikey = apikey
    self.university_id = university_id

class University(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String, unique=True)
  users = db.relationship('Person', backref='university', lazy='dynamic')

  def __init__(self, name):
    self.name = name

class Event(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  category = db.Column(db.String(32))
  init_id = db.Column(db.Integer, db.ForeignKey('person.id'))
  proposer_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True)
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

#returns empty string if there is a db error, or api is wrong
@app.route('/person/new', methods=['POST'])
def create_user():
  data = request.json
  checkapi = data["apikey"]
  if not checkapi == universal:
    data = {
      "error" : "could not authenticate API key"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  fbid = data["fbid"]
  uni = University.query.filter_by(name=data["university"]).first()
  if uni is None:
    data = {
      "error" : "could not find University"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  apikey = id_generator()
  user = Person(fbid, data["name"], apikey, uni.id)
  db.session.add(user)
  try:
    db.session.commit()
    data = {
      "apikey" : apikey,
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "error" : "could not create user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

# grabs user based on API key
@app.route('/person', methods=['GET'])
def get_user():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "error" : "could not find user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  jsondict = {}
  jsondict["id"] = str(user.id)
  jsondict["fbid"] = user.fbid
  jsondict["mobile"] = user.mobile
  jsondict["university_id"] = str(user.university_id)
  jsondict["verified"] = str(user.verified)
  resp = jsonify(jsondict)
  resp.status_code = 200
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
      "error" : "could not find user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp  
  user.mobile = num
  db.session.add(user)
  try:
    db.session.commit()
    data = {
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    client = TwilioRestClient(account_sid, auth_token)
    message = client.sms.messages.create(body="Welcome to Merge! Please text back 'Yes' to confirm", to=num,
      from_="+15616669720")
    return resp
  except:
    data = {
      "error" : "could not update mobile"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

#used for twilio confirmation
@app.route('/person/twilio', methods=['POST'])
def receive_confirmation():
  print 'here'
  from_number = request.values.get('From', None)
  print 'here2'
  user = Person.query.filter_by(mobile=from_number).first()
  if user is None:
    data = {
      "error" : "could not verify number"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  body = request.values.get('Body', None)
  if not body == "Yes":
    data = {
      "error" : "could not verify number"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  user.verified = True
  db.session.add(user)
  try:
    db.session.commit()
    message = "Confirmed! We hope you enjoy our service!"
    resp = twilio.twiml.Response()
    resp.sms(message)
    return str(resp)
  except:
    data = {
      "error" : "could not update number"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

@app.route('/person/verified', methods=['GET'])
def check_confirmation():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "error" : "could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  if user.verified == True:
    data = {
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  data = {
    "error" : "user is not verified"
  }
  resp = jsonify(data)
  resp.status_code = 500
  return resp

#returns empty string if you get a db error
#TODO: add app API authentication. DONE
@app.route('/university/new', methods=['POST'])
def create_uni():
  data = request.json
  checkapi = data["apikey"]
  if not checkapi == universal:
    data = {
      "error" : "could not authenticate API key"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  name = data["name"]
  uni = University(name)
  db.session.add(uni)
  try:
    db.session.commit()
    data = {
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "error" : "could not create university"
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
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "error" : "could not create event"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

# the current user proposes to join an event
@app.route('/event/propose', methods=['POST'])
def propose_join():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event = Event.query.filter_by(id=int(data["event_id"])).first()
  if event is None:
    data = {
      "error" : "Could not find event"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event.proposer_id = user.id
  db.session.add(event)
  try:
    db.session.commit()
    data = {
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "error" : "could not add proposed user"
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
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event = Event.query.filter_by(id=int(data["event_id"])).first()
  if event is None:
    data = {
      "error" : "Could not find event"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  event.partner_id = user.id
  event.proposer_id = None
  db.session.add(event)
  try:
    db.session.commit()
    data = {
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "error" : "could not join event"
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
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  category = data["category"]
  events = Event.query.filter_by(university_id=user.university_id, category=category).filter(Event.partner_id == None, Event.enddate > datetime.now())
  jsondict = {}
  jsondict["events"] = []
  for event in events:
    eventjson = {}
    eventjson["id"] = str(event.id)
    eventjson["category"] = event.category
    initiator = Person.query.filter_by(id = event.init_id).first()
    initJSON = {}
    initJSON["id"] = str(initiator.id)
    initjSON["fbid"] = initiator.fbid
    initjSON["mobile"] = initiator.mobile
    initjSON["university_id"] = str(initiator.university_id)
    initJSON["verified"] = str(initiator.verified)
    #eventjson["initiator"] = initJSON
    eventjson["startdate"] = time.mktime(event.startdate.timetuple())
    eventjson["enddate"] = time.mktime(event.enddate.timetuple())
    if event.messagedate:
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
  if event is None or event.proposer_id is None:
    data = {
      "error" : "Could not find event"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp

  user = Person.query.filter_by(apikey=apikey, id=int(event.proposer_id)).first()
  if user is None:
    data = {
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
      "error" : ""
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
  except:
    data = {
      "error" : "could not add message info"
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
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  events = Event.query.filter(Event.partner_id==user.id, Event.messagedate < datetime.now() - timedelta(minutes=5)) # remind if prompted > 5 minutes ago
  jsondict = {}
  jsondict["events"] = []
  for event in events:
    eventjson = {}
    eventjson["category"] = event.category
    initiator = Person.query.filter_by(id = event.init_id).first()
    eventjson["init"] = initiator.fbid
    partner = Person.query.filter_by(id=event.partner_id).first()
    if partner:
      eventjson["partner"] = partner.fbid
    eventjson["startdate"] = time.mktime(event.startdate.timetuple())
    eventjson["enddate"] = time.mktime(event.enddate.timetuple())
    if event.messagedate:
      eventjson["messagedate"] = time.mktime(event.messagedate.timetuple())
    jsondict["events"].append(eventjson);
  resp = jsonify(jsondict)
  resp.status_code = 200
  return resp

#get news feed
@app.route('/event/newsfeed', methods=['GET'])
def newsfeed():
  data = request.json
  apikey = data["apikey"]
  user = Person.query.filter_by(apikey=apikey).first()
  if user is None:
    data = {
      "error" : "Could not authenticate user"
    }
    resp = jsonify(data)
    resp.status_code = 500
    return resp
  events = Event.query.filter_by(university_id=user.university_id).filter(Event.partner_id != None).order_by(Event.enddate.desc()).limit(10).all()
  jsondict = {}
  jsondict["events"] = []
  for event in events:
    eventjson = {}
    eventjson["category"] = event.category
    initiator = Person.query.filter_by(id = event.init_id).first()
    initJSON = {}
    initJSON["id"] = str(initiator.id)
    initjSON["fbid"] = initiator.fbid
    initjSON["mobile"] = initiator.mobile
    initjSON["university_id"] = str(initiator.university_id)
    initJSON["verified"] = str(initiator.verified)
    eventjson["initiator"] = initJSON
    partner = Person.query.filter_by(id=event.partner_id).first()
    if partner:
      partJSON = {}
      partJSON["id"] = str(partner.id)
      partjSON["fbid"] = partner.fbid
      partjSON["mobile"] = partner.mobile
      partjSON["university_id"] = str(partner.university_id)
      partJSON["verified"] = str(partner.verified)
      eventjson["partner"] = partJSON
    eventjson["startdate"] = time.mktime(event.startdate.timetuple())
    eventjson["enddate"] = time.mktime(event.enddate.timetuple())
    if event.messagedate:
      eventjson["messagedate"] = time.mktime(event.messagedate.timetuple())
    jsondict["events"].append(eventjson);
  resp = jsonify(jsondict)
  resp.status_code = 200
  return resp
  
if __name__ == '__main__':
    app.run(debug=True)
