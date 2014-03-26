from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required
from flask.ext.sqlalchemy import get_debug_queries
from flask.ext.babel import gettext
from app import app, db, lm, oid, babel
from run import Command
from forms import LoginForm, EditForm, DeployForm, SearchForm, OrgEditForm, NodeEditForm
from models import User, ROLE_USER, ROLE_ADMIN, Organization, Node
from datetime import datetime
from guess_language import guessLanguage
from translate import microsoft_translate
from config import MAX_SEARCH_RESULTS, LANGUAGES, DATABASE_QUERY_TIMEOUT, WHOOSH_ENABLED

from flask import Markup
from emails import deploy_notification

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(LANGUAGES.keys())
    
@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = get_locale()
    g.search_enabled = WHOOSH_ENABLED

@app.after_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= DATABASE_QUERY_TIMEOUT:
            app.logger.warning("SLOW QUERY: %s\nParameters: %s\nDuration: %fs\nContext: %s\n" % (query.statement, query.parameters, query.duration, query.context))
    return response

@app.errorhandler(404)
def internal_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/', methods = ['GET', 'POST'])
@app.route('/index', methods = ['GET', 'POST'])
@app.route('/index/<int:page>', methods = ['GET', 'POST'])
@login_required
def index(page = 1):
    orgs = g.user.organizations.all()
    form = DeployForm()
    if form.validate_on_submit():
        mmfs = ', '.join(form.mmfs.data)
        org = form.org.data
        tag = "owncloud"
        if "feed" in mmfs:
             tag = tag + "_feeds"
        if "note" in mmfs:
             tag = tag + "_notes"
        tag =tag + "_" + org
        cmd = Command("c:\\vms\\agiledemo\\dockerdeploy\\bin\\deploy.bat start " + org + " " + tag);
        output = cmd.run(shell=True)
        msg = gettext('The MMFs %(mmfs)s have been deployed to %(org)s:', mmfs = mmfs, org = org)
        flash(msg)
        for line in output[1].splitlines():
            if "<a href" in line:
                flash(gettext('%(clink)s', clink = line))
                msg = msg + line
        # send an email notification
        deploy_notification(org, msg)
        flash("Email sent to the master")
    return render_template('index.html',
        title = 'Deploy',
        orgs = orgs,
        form = form
        )

@app.route('/login', methods = ['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for = ['nickname', 'email'])
    return render_template('login.html', 
        title = 'Sign In',
        form = form,
        providers = app.config['OPENID_PROVIDERS'])

@oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash(gettext('Invalid login. Please try again.'))
        return redirect(url_for('login'))
    user = User.query.filter_by(email = resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        nickname = User.make_valid_nickname(nickname)
        nickname = User.make_unique_nickname(nickname)
        user = User(nickname = nickname, email = resp.email, role = ROLE_USER)
        db.session.add(user)
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember = remember_me)
    return redirect(request.args.get('next') or url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
    
@app.route('/user/<nickname>')
@app.route('/user/<nickname>/<int:page>')
@login_required
def user(nickname, page = 1):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
        flash(gettext('User %(nickname)s not found.', nickname = nickname))
        return redirect(url_for('index'))
    return render_template('user.html',
        user = user
        )

@app.route('/edit', methods = ['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.nickname)
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.about_me = form.about_me.data
        db.session.add(g.user)
        db.session.commit()
        flash(gettext('Your changes have been saved.'))
        return redirect(url_for('edit'))
    elif request.method != "POST":
        form.nickname.data = g.user.nickname
        form.about_me.data = g.user.about_me
    return render_template('edit.html',
        form = form)

@app.route('/org_add', methods = ['POST'])
@login_required
def org_add():
    form = OrgEditForm(g.user, "")
    if form.validate_on_submit():
        org = Organization(name = form.name.data, user = g.user, timestamp = datetime.utcnow())
        db.session.add(org)
        db.session.commit()
        flash(gettext('Your settings have been saved.'))
        return redirect(url_for('index'))
    return render_template('org_edit.html', form = form)

@app.route('/org_edit/<name>', methods = ['GET', 'POST'])
@login_required
def org_edit(name):
    org = g.user.organizations.filter_by(name = name).first()
    form = OrgEditForm(g.user, org.name)
    if form.validate_on_submit():
        org.name = form.name.data
        db.session.add(org)
        db.session.commit()
        flash(gettext('Your changes have been saved.'))
        return redirect(url_for('org_edit', name = org.name))
    elif request.method != "POST":
        form.name.data = org.name
    return render_template('org_edit.html',
        form = form)


@app.route('/org_deploy/<name>', methods = ['GET', 'POST'])
@login_required
def org_deploy(name):
    org = g.user.organizations.filter_by(name = name).first()
    envs = org.envs.all()
    return render_template('org_deploy.html',
        org = org,
        envs = envs)

@app.route('/node_add/<org_name>', methods = ['POST'])
@login_required
def node_add(org_name, env_name, grp_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    form = NodeEditForm(org, "")
    if form.validate_on_submit():
        node = Node(name = form.name.data, org =org, timestamp = datetime.utcnow(), ip = form.ip.data)
        db.session.add(node)
        db.session.commit()
        flash(gettext('Your settings have been saved.'))
        return redirect(url_for('org_deploy', name = org.name))
    return render_template('node_edit.html', form = form)

@app.route('/node_edit/<org_name>/<node_name>', methods = ['GET', 'POST'])
@login_required
def node_edit(org_name, node_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    node = org.nodes.filter_by(name = node_name).first()
    form = NodeEditForm(org, node.name)
    if form.validate_on_submit():
        node.name = form.name.data
        node.ip = form.ip.data
        db.session.add(node)
        db.session.commit()
        flash(gettext('Your changes have been saved.'))
        return redirect(url_for('org_deploy', name = org.name))
    elif request.method != "POST":
        form.name.data = node.name
        form.ip.data = node.ip
    return render_template('node_edit.html',
        form = form)

@app.route('/run/<name>', methods = ['GET', 'POST'])
@login_required
def run(mmfs, org):
    command = Command("echo 'Process started'; sleep 2; echo 'Process finished'")
    output = command.run(timeout=1, shell=True)
    return render_template('output.html',
        output = output)

@app.route('/deploy/<node_name>/<org_name>', methods = ['GET', 'POST'])
@login_required
def deploy(node_name, grp_name):
    command = Command("c:\\Users\\sgopalak\\chef-repo\\deploy.bat " + node_name + " " + org_name)
    output = command.run(timeout=None, shell=True)
    return render_template('output.html',
        output = output)
        
    
@app.route('/search', methods = ['POST'])
@login_required
def search():
    if not g.search_form.validate_on_submit():
        return redirect(url_for('index'))
    return redirect(url_for('search_results', query = g.search_form.search.data))

@app.route('/search_results/<query>')
@login_required
def search_results(query):
    results = Node.query.whoosh_search(query, MAX_SEARCH_RESULTS).all()
    return render_template('search_results.html',
        query = query,
        results = results)

@app.route('/translate', methods = ['POST'])
@login_required
def translate():
    return jsonify({
        'text': microsoft_translate(
            request.form['text'],
            request.form['sourceLang'],
            request.form['destLang']) })

