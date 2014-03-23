from hashlib import md5
from app import db
from app import app
from config import WHOOSH_ENABLED
import re

ROLE_USER = 0
ROLE_ADMIN = 1

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class NameValidator:
    @staticmethod
    def make_valid_name(nickname):
        return re.sub('[^a-zA-Z0-9_\.\ ]', '', nickname)
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    nickname = db.Column(db.String(64), unique = True)
    email = db.Column(db.String(120), index = True, unique = True)
    role = db.Column(db.SmallInteger, default = ROLE_USER)
    organizations = db.relationship('Organization', backref = 'user', lazy = 'dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime)

    @staticmethod
    def make_valid_nickname(nickname):
        return NameValidator.make_valid_name(nickname)

    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(nickname = nickname).first() == None:
            return nickname
        version = 2
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname = new_nickname).first() == None:
                break
            version += 1
        return new_nickname
        
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def avatar(self, size):
        return 'http://www.gravatar.com/avatar/' + md5(self.email).hexdigest() + '?d=mm&s=' + str(size)
        

    def __repr__(self): # pragma: no cover
        return '<User %r>' % (self.nickname)    


class Organization(db.Model):
    __searchable__ = ['name']
    
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(140), unique = True)
    timestamp = db.Column(db.DateTime)
    hosts = db.relationship('Node', backref = 'org', lazy = 'dynamic')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    @staticmethod
    def make_valid_name(nickname):
        return NameValidator.make_valid_name(nickname)

    def __repr__(self): # pragma: no cover
        return '<Organization %r>' % (self.name)

class Node(db.Model):
    __searchable__ = ['name']

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(140), unique = True)
    fd_space = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime)
    ip = db.Column(db.String(45), unique = True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    @staticmethod
    def make_valid_name(nickname):
        return NameValidator.make_valid_name(nickname)

    def __repr__(self): # pragma: no cover
        return '<Node %r>' % (self.name)
	


if WHOOSH_ENABLED:
    import flask.ext.whooshalchemy as whooshalchemy
    whooshalchemy.whoosh_index(app, Node)
