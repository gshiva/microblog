from flask.ext.wtf import Form
from wtforms import TextField, widgets, BooleanField, TextAreaField, SelectMultipleField, SelectField
from wtforms.validators import Required, Length

from flask.ext.babel import gettext
from app.models import User, Organization, Node

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

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

class DeployForm(Form):
    mmfs = MultiCheckboxField('MMFs to be deployed', choices = [('notes','Notes'), ('feeds', 'News')])
    org = SelectField('Organization', choices = [('qa','QA'), ('prod','Staging'), ('prod','Production')])

class SearchForm(Form):
    search = TextField('search', validators = [Required()])

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
        org = user.organizations.filter_by(name = self.name.data).first()
        if org != None:
            self.name.errors.append(gettext('The Organization name already exists'))
            return False
        return True


class NodeEditForm(Form):
    name = TextField('name', validators = [Required()])
    ip = TextField('ip', validators = [Required()])

    def __init__(self, org, original_name, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_name = original_name
        self.org_name = org.name

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
        node = org.nodes.filter_by(name = self.name.data).first()
        if node != None:
            self.name.errors.append(gettext('The node name already exists'))
            return False
        return True
