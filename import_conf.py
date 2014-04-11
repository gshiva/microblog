from app.models import ConferenceRoom
from app import db
from sqlalchemy.orm.session import make_transient
rooms = ConferenceRoom.query.all()
for room in rooms:
     db.session.delete(room)
db.session.commit()
for room in rooms:
     make_transient(room)
     room.id = None
     db.session.add(room)
db.session.commit()
