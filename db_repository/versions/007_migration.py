from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
env = Table('env', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
)

group = Table('group', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
)

node = Table('node', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('ip', String(length=45)),
)

organization = Table('organization', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['env'].create()
    post_meta.tables['group'].create()
    post_meta.tables['node'].create()
    post_meta.tables['organization'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['env'].drop()
    post_meta.tables['group'].drop()
    post_meta.tables['node'].drop()
    post_meta.tables['organization'].drop()
