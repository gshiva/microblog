#!flask/bin/python
# -*- coding: utf8 -*-

from coverage import coverage
cov = coverage(branch = True, omit = ['flask/*', 'tests.py'])
cov.start()

import os
import unittest
from datetime import datetime, timedelta

from config import basedir
from app import app, db
from app.models import User, Post, MCSetting
from app.translate import microsoft_translate

class TestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test.db')
        db.create_all()
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        
    def add_four_users(self):
        u1 = User(nickname = 'john', email = 'john@example.com')
        u2 = User(nickname = 'susan', email = 'susan@example.com')
        u3 = User(nickname = 'mary', email = 'mary@example.com')
        u4 = User(nickname = 'david', email = 'david@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.add(u3)
        db.session.add(u4)
        return u1, u2, u3, u4

    def test_user(self):
        # make valid nicknames
        n = User.make_valid_nickname('John_123')
        assert n == 'John_123'
        n = User.make_valid_nickname('John_[123]\n')
        assert n == 'John_123'
        # create a user
        u = User(nickname = 'john', email = 'john@example.com')
        db.session.add(u)
        db.session.commit()
        assert u.is_authenticated() == True
        assert u.is_active() == True
        assert u.is_anonymous() == False
        assert u.id == int(u.get_id())
        
    def test_avatar(self):
        # create a user
        u = User(nickname = 'john', email = 'john@example.com')
        avatar = u.avatar(128)
        expected = 'http://www.gravatar.com/avatar/d4c74594d841139328695756648b6bd6'
        assert avatar[0:len(expected)] == expected

    def test_make_unique_nickname(self):
        # create a user and write it to the database
        u = User(nickname = 'john', email = 'john@example.com')
        db.session.add(u)
        db.session.commit()
        nickname = User.make_unique_nickname('susan')
        assert nickname == 'susan'
        nickname = User.make_unique_nickname('john')
        assert nickname != 'john'
        # make another user with the new nickname
        u = User(nickname = nickname, email = 'susan@example.com')
        db.session.add(u)
        db.session.commit()
        nickname2 = User.make_unique_nickname('john')
        assert nickname2 != 'john'
        assert nickname2 != nickname
        
    def test_follow(self):
        u1 = User(nickname = 'john', email = 'john@example.com')
        u2 = User(nickname = 'susan', email = 'susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        assert u1.unfollow(u2) == None
        u = u1.follow(u2)
        db.session.add(u)
        db.session.commit()
        assert u1.follow(u2) == None
        assert u1.is_following(u2)
        assert u1.followed.count() == 1
        assert u1.followed.first().nickname == 'susan'
        assert u2.followers.count() == 1
        assert u2.followers.first().nickname == 'john'
        u = u1.unfollow(u2)
        assert u != None
        db.session.add(u)
        db.session.commit()
        assert u1.is_following(u2) == False
        assert u1.followed.count() == 0
        assert u2.followers.count() == 0
        
    def test_follow_posts(self):
        # make four users
        u1, u2, u3, u4 = self.add_four_users()
        # make four posts
        utcnow = datetime.utcnow()
        p1 = Post(body = "post from john", author = u1, timestamp = utcnow + timedelta(seconds = 1))
        p2 = Post(body = "post from susan", author = u2, timestamp = utcnow + timedelta(seconds = 2))
        p3 = Post(body = "post from mary", author = u3, timestamp = utcnow + timedelta(seconds = 3))
        p4 = Post(body = "post from david", author = u4, timestamp = utcnow + timedelta(seconds = 4))
        db.session.add(p1)
        db.session.add(p2)
        db.session.add(p3)
        db.session.add(p4)
        db.session.commit()
        # setup the followers
        u1.follow(u1) # john follows himself
        u1.follow(u2) # john follows susan
        u1.follow(u4) # john follows david
        u2.follow(u2) # susan follows herself
        u2.follow(u3) # susan follows mary
        u3.follow(u3) # mary follows herself
        u3.follow(u4) # mary follows david
        u4.follow(u4) # david follows himself
        db.session.add(u1)
        db.session.add(u2)
        db.session.add(u3)
        db.session.add(u4)
        db.session.commit()
        # check the followed posts of each user
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        assert len(f1) == 3
        assert len(f2) == 2
        assert len(f3) == 2
        assert len(f4) == 1
        assert f1[0].id == p4.id
        assert f1[1].id == p2.id
        assert f1[2].id == p1.id
        assert f2[0].id == p3.id
        assert f2[1].id == p2.id
        assert f3[0].id == p4.id
        assert f3[1].id == p3.id
        assert f4[0].id == p4.id

    def test_delete_post(self):
        # create a user and a post
        u = User(nickname = 'john', email = 'john@example.com')
        p = Post(body = 'test post', author = u, timestamp = datetime.utcnow())
        db.session.add(u)
        db.session.add(p)
        db.session.commit()
        # query the post and destroy the session
        p = Post.query.get(1)
        db.session.remove()
        # delete the post using a new session
        db.session = db.create_scoped_session()
        db.session.delete(p)
        db.session.commit()

    def test_mcsetting(self):
        # make valid nicknames
        n = MCSetting.make_valid_name('Config_123')
        assert n == 'Config_123'
        n = MCSetting.make_valid_name('Config_[123]\n')
        assert n == 'Config_123'
        # create the users
        u1, u2, u3, u4 = self.add_four_users()
        # add four configs
        utcnow = datetime.utcnow()
        c1 = MCSetting(name = "u1_config", physics_verbosity = 0, physics_SetList = "u1 set list", author = u1, timestamp = utcnow + timedelta(seconds = 1))
        c2 = MCSetting(name = "u2_config", physics_verbosity = 0, physics_SetList = "u2 set list", author = u2, timestamp = utcnow + timedelta(seconds = 2))
        c3 = MCSetting(name = "u3_config", physics_verbosity = 0, physics_SetList = "u3 set list", author = u3, timestamp = utcnow + timedelta(seconds = 3))
        c4 = MCSetting(name = "u4_config", physics_verbosity = 0, physics_SetList = "u4 set list", author = u4, timestamp = utcnow + timedelta(seconds = 4))
        db.session.add(c1)
        db.session.add(c2)
        db.session.add(c3)
        db.session.add(c4)
        #check if the user is assigned the right config
        mc1 = u1.settings.all()
        mc2 = u2.settings.all()
        mc3 = u3.settings.all()
        mc4 = u4.settings.all()
        assert len(mc1) == 1
        assert len(mc2) == 1
        assert len(mc3) == 1
        assert len(mc4) == 1
        assert mc1[0] == c1
        assert mc2[0] == c2
        assert mc3[0] == c3
        assert mc4[0] == c4
        assert mc1[0] != c2

    def test_translation(self):
        assert microsoft_translate(u'English', 'en', 'es') == u'Inglés'
        assert microsoft_translate(u'Español', 'es', 'en') == u'Spanish'
        
if __name__ == '__main__':
    try:
        unittest.main()
    except:
        pass
    cov.stop()
    cov.save()
    print "\n\nCoverage Report:\n"
    cov.report()
    print "\nHTML version: " + os.path.join(basedir, "tmp/coverage/index.html")
    cov.html_report(directory = 'tmp/coverage')
    cov.erase()
