from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
node = Table('node', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('ip', String(length=45)),
    Column('grp_id', Integer),
)

group = Table('group', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('env_id', Integer),
)

env = Table('env', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=140)),
    Column('org_id', Integer),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['node'].columns['grp_id'].create()
    post_meta.tables['group'].columns['env_id'].create()
    post_meta.tables['env'].columns['org_id'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['node'].columns['grp_id'].drop()
    post_meta.tables['group'].columns['env_id'].drop()
    post_meta.tables['env'].columns['org_id'].drop()
