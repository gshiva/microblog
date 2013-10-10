from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
node = Table('node', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('timestamp', DateTime),
    Column('ip', String(length=45)),
    Column('grp_id', Integer),
)

organization = Table('organization', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('timestamp', DateTime),
    Column('user_id', Integer),
)

group = Table('group', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('timestamp', DateTime),
    Column('env_id', Integer),
)

env = Table('env', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('timestamp', DateTime),
    Column('org_id', Integer),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['node'].columns['timestamp'].create()
    post_meta.tables['organization'].columns['timestamp'].create()
    post_meta.tables['group'].columns['timestamp'].create()
    post_meta.tables['env'].columns['timestamp'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['node'].columns['timestamp'].drop()
    post_meta.tables['organization'].columns['timestamp'].drop()
    post_meta.tables['group'].columns['timestamp'].drop()
    post_meta.tables['env'].columns['timestamp'].drop()
