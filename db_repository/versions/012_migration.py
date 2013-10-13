from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
mc_setting = Table('mc_setting', pre_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String),
    Column('physics_verbosity', Integer),
    Column('physics_SetList', String),
    Column('timestamp', DateTime),
    Column('user_id', Integer),
    Column('language', String),
)

customer = Table('customer', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=255)),
    Column('email', String(length=140)),
    Column('aws_acct_id', Integer),
    Column('timestamp', DateTime),
    Column('user_id', Integer),
    Column('language', String(length=5)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['mc_setting'].drop()
    post_meta.tables['customer'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['mc_setting'].create()
    post_meta.tables['customer'].drop()
