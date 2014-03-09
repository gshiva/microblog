from flask.ext.wtf import Form, TextField, BooleanField, TextAreaField, IntegerField
from flask.ext.wtf import Required, Length, NumberRange
from flask.ext.babel import gettext
from app.models import User, Organization, Env, Group, Node, Customer

class LoginForm(Form):
    openid = TextField('openid', validators = [Required()])
    remember_me = BooleanField('remember_me', default = False)

class EditForm(Form):
    nickname = TextField('nickname', validators = [Required()])
    about_me = TextAreaField('about_me', validators = [Length(min = 0, max = 140)])
    
    def __init__(self, original_nickname, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_nickname = original_nickname
        
    def validate(self):
        if not Form.validate(self):
            return False
        if self.nickname.data == self.original_nickname:
            return True
        if self.nickname.data != User.make_valid_nickname(self.nickname.data):
            self.nickname.errors.append(gettext('This nickname has invalid characters. Please use letters, numbers, dots and underscores only.'))
            return False
        user = User.query.filter_by(nickname = self.nickname.data).first()
        if user != None:
            self.nickname.errors.append(gettext('This nickname is already in use. Please choose another one.'))
            return False
        return True
        
class PostForm(Form):
    post = TextField('post', validators = [Required()])
    
class SearchForm(Form):
    search = TextField('search', validators = [Required()])

class CustomerEditForm(Form):
    name = TextField('name', validators = [Required()])
    email = TextField('email', validators = [Required()])
    aws_acct_id = IntegerField('aws_acct_id', default = 999999999999, 
                                 validators = [Required(), NumberRange(min = 100000000000, max = 999999999999, message = "AWS account id must have 12 digits")])

    def __init__(self, user, original_name, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_name = original_name
        self.user_name = user.nickname

    def validate(self):
        if not Form.validate(self):
            return False
        # simple check to see if there are 12 digits in the number
        if self.aws_acct_id.data < 100000000000 or self.aws_acct_id.data > 999999999999:
            self.aws_acct_id.errors.append(gettext('AWS account id must have 12 digits'))
            return False
        if self.name.data == self.original_name:
            return True
        if self.name.data != Customer.make_valid_name(self.name.data):
            self.name.errors.append(gettext('This name has invalid characters. Please use letters, numbers, dots and underscores only.'))
            return False
        user = User.query.filter_by(nickname = self.user_name).first()
        if user == None:
            self.name.errors.append(gettext('The user name was not found'))
            return False
        customer = user.customers.filter_by(name = self.name.data).first()
        if customer != None:
            self.name.errors.append(gettext('The customer already exists'))
            return False
        return True

class OrgEditForm(Form):
    name = TextField('name', validators = [Required()])

    def __init__(self, user, original_name, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_name = original_name
        self.user_name = user.nickname

    def validate(self):
        if not Form.validate(self):
            return False
        if self.name.data == self.original_name:
            return True
        if self.name.data != Organization.make_valid_name(self.name.data):
            self.name.errors.append(gettext('This name has invalid characters. Please use letters, numbers, dots and underscores only.'))
            return False
        user = User.query.filter_by(nickname = self.user_name).first()
        if user == None:
            self.name.errors.append(gettext('The user name was not found'))
            return False
        org = user.settings.filter_by(name = self.name.data).first()
        if org != None:
            self.name.errors.append(gettext('The Organization name already exists'))
            return False
        return True

class EnvEditForm(Form):
    name = TextField('name', validators = [Required()])

    def __init__(self, org, original_name, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_name = original_name
        self.org_name = org.name

    def validate(self):
        if not Form.validate(self):
            return False
        if self.name.data == self.original_name:
            return True
        if self.name.data != Env.make_valid_name(self.name.data):
            self.name.errors.append(gettext('This name has invalid characters. Please use letters, numbers, dots and underscores only.'))
            return False
        org = Organization.query.filter_by(name = self.org_name).first()
        if org == None:
            self.name.errors.append(gettext('The organization name was not found'))
            return False
        env = org.envs.filter_by(name = self.name.data).first()
        if env != None:
            self.name.errors.append(gettext('The environment name already exists'))
            return False
        return True
        
class GrpEditForm(Form):
    name = TextField('name', validators = [Required()])

    def __init__(self, org, env, original_name, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_name = original_name
        self.org_name = org.name
        self.env_name = env.name

    def validate(self):
        if not Form.validate(self):
            return False
        if self.name.data == self.original_name:
            return True
        if self.name.data != Group.make_valid_name(self.name.data):
            self.name.errors.append(gettext('This name has invalid characters. Please use letters, numbers, dots and underscores only.'))
            return False
        org = Organization.query.filter_by(name = self.org_name).first()
        if org == None:
            self.name.errors.append(gettext('The organization name was not found'))
            return False
        env = org.envs.filter_by(name = self.env_name).first()
        if env == None:
            self.name.errors.append(gettext('The environment name was not found'))
            return False
        grp = env.groups.filter_by(name = self.name.data).first()
        if grp != None:
            self.name.errors.append(gettext('The group name already exists'))
            return False
        return True

class NodeEditForm(Form):
    name = TextField('name', validators = [Required()])
    ip = TextField('ip', validators = [Required()])

    def __init__(self, org, env, grp, original_name, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_name = original_name
        self.org_name = org.name
        self.env_name = env.name
        self.grp_name = grp.name

    def validate(self):
        if not Form.validate(self):
            return False
        if self.name.data == self.original_name:
            return True
        if self.name.data != Node.make_valid_name(self.name.data):
            self.name.errors.append(gettext('This name has invalid characters. Please use letters, numbers, dots and underscores only.'))
            return False
        org = Organization.query.filter_by(name = self.org_name).first()
        if org == None:
            self.name.errors.append(gettext('The organization name was not found'))
            return False
        env = org.envs.filter_by(name = self.env_name).first()
        if env == None:
            self.name.errors.append(gettext('The environment name was not found'))
            return False
        grp = env.groups.filter_by(name = self.grp_name).first()
        if grp == None:
            self.name.errors.append(gettext('The group name was not found'))
            return False
        node = grp.nodes.filter_by(name = self.name.data).first()
        if node != None:
            self.name.errors.append(gettext('The node name already exists'))
            return False
        return True
