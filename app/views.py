from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required
from flask.ext.sqlalchemy import get_debug_queries
from flask.ext.babel import gettext
from app import app, db, lm, oid, babel
from run import Command
from forms import LoginForm, EditForm, PostForm, SearchForm, CustomerEditForm, OrgEditForm, EnvEditForm, GrpEditForm, NodeEditForm
from models import User, ROLE_USER, ROLE_ADMIN, Post, Organization, Env, Group, Node, Customer, ConferenceRoom
from datetime import datetime
from emails import follower_notification, customer_notification
from ec2 import share_image
from guess_language import guessLanguage
from translate import microsoft_translate
from config import POSTS_PER_PAGE, MAX_SEARCH_RESULTS, LANGUAGES, DATABASE_QUERY_TIMEOUT, WHOOSH_ENABLED

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
    form = PostForm()
    if form.validate_on_submit():
        language = guessLanguage(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body = form.post.data,
            timestamp = datetime.utcnow(),
            author = g.user,
            language = language)
        db.session.add(post)
        db.session.commit()
        flash(gettext('Your post is now live!'))
        return redirect(url_for('index'))
    posts = g.user.followed_posts().paginate(page, POSTS_PER_PAGE, False)
    customers = g.user.customers.all()
    return render_template('index.html',
        title = 'Home',
        form = form,
        posts = posts,
        customers = customers)

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
        # make the user follow him/herself
        db.session.add(user.follow(user))
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
    posts = user.posts.paginate(page, POSTS_PER_PAGE, False)
    return render_template('user.html',
        user = user,
        posts = posts)

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


def share_to_aws(aws_acct_id):
        image_id = 'ami-3c79e60c'
        return share_image(aws_acct_id, image_id)
    
@app.route('/cust_add', methods = ['POST'])
@login_required
def cust_add():
    form = CustomerEditForm(g.user, "")
    if form.validate_on_submit():
        cust = Customer(name = form.name.data, email = form.email.data, aws_acct_id = form.aws_acct_id.data, user = g.user, timestamp = datetime.utcnow())
        db.session.add(cust)
        db.session.commit()
        customer_notification(cust, g.user)
        share_to_aws(cust.aws_acct_id)
        flash(gettext('The customer information has been saved.'))
        return redirect(url_for('index'))
    return render_template('cust_edit.html', form = form)

@app.route('/cust_edit/<name>', methods = ['GET', 'POST'])
@login_required
def cust_edit(name):
    cust = g.user.customers.filter_by(name = name).first()
    form = CustomerEditForm(g.user, cust.name)
    if form.validate_on_submit():
        cust.name = form.name.data
        cust.email = form.email.data
        cust.aws_acct_id = form.aws_acct_id.data
        db.session.add(cust)
        db.session.commit()
        share_to_aws(cust.aws_acct_id)
        
        customer_notification(cust, g.user)
        flash(gettext('The customer information changes have been saved.'))
        return redirect(url_for('cust_edit', name = cust.name))
    elif request.method != "POST":
        form.name.data = cust.name
        form.email.data = cust.email
        form.aws_acct_id.data = cust.aws_acct_id
    return render_template('cust_edit.html',
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

@app.route('/env_add/<org_name>', methods = ['POST'])
@login_required
def env_add(org_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    form = EnvEditForm(org, "")
    if form.validate_on_submit():
        env = Env(name = form.name.data, org = org, timestamp = datetime.utcnow())
        db.session.add(env)
        db.session.commit()
        flash(gettext('Your settings have been saved.'))
        return redirect(url_for('org_deploy', name = org.name))
    return render_template('org_deploy.html', form = form)

@app.route('/grp_add/<org_name>/<env_name>', methods = ['POST'])
@login_required
def grp_add(org_name, env_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    env = org.envs.filter_by(name = env_name).first()
    form = GrpEditForm(org, env, "")
    if form.validate_on_submit():
        grp = Group(name = form.name.data, env = env, timestamp = datetime.utcnow())
        db.session.add(grp)
        db.session.commit()
        flash(gettext('Your settings have been saved.'))
        return redirect(url_for('org_deploy', name = org.name))
    return render_template('grp_edit.html', form = form)

@app.route('/node_add/<org_name>/<env_name>/<grp_name>', methods = ['POST'])
@login_required
def node_add(org_name, env_name, grp_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    env = org.envs.filter_by(name = env_name).first()
    grp = env.groups.filter_by(name = grp_name).first()
    form = NodeEditForm(org, env, grp, "")
    if form.validate_on_submit():
        node = Node(name = form.name.data, grp =grp, timestamp = datetime.utcnow(), ip = form.ip.data)
        db.session.add(node)
        db.session.commit()
        flash(gettext('Your settings have been saved.'))
        return redirect(url_for('org_deploy', name = org.name))
    return render_template('node_edit.html', form = form)

@app.route('/node_edit/<org_name>/<env_name>/<grp_name>/<node_name>', methods = ['GET', 'POST'])
@login_required
def node_edit(org_name, env_name, grp_name, node_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    env = org.envs.filter_by(name = env_name).first()
    grp = env.groups.filter_by(name = grp_name).first()
    node = grp.nodes.filter_by(name = node_name).first()
    form = NodeEditForm(org, env, grp, node.name)
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
def run(name):
    command = Command("echo 'Process started'; sleep 2; echo 'Process finished'")
    output = command.run(timeout=1, shell=True)
    return render_template('output.html',
        output = output)

@app.route('/bootstrap/<ip>/<grp_name>', methods = ['GET', 'POST'])
@login_required
def bootstrap(ip, grp_name):
    command = Command("c:\\Users\\sgopalak\\chef-repo\\bootstrap.bat " + ip + " " + grp_name)
    output = command.run(timeout=None, shell=True)
    return render_template('output.html',
        output = output)

@app.route('/deploy/<node_name>/<grp_name>', methods = ['GET', 'POST'])
@login_required
def deploy(node_name, grp_name):
    command = Command("c:\\Users\\sgopalak\\chef-repo\\deploy.bat " + node_name + " " + grp_name)
    output = command.run(timeout=None, shell=True)
    return render_template('output.html',
        output = output)
        
@app.route('/update_grp/<org_name>/<env_name>/<grp_name>', methods = ['POST'])
@login_required
def update_grp(org_name, env_name, grp_name):
    org = g.user.organizations.filter_by(name = org_name).first()
    env = org.envs.filter_by(name = env_name).first()
    envs = org.envs.all()
    grp = env.groups.filter_by(name = grp_name).first()
    nodes = grp.nodes.all()
    for node in nodes:
        deploy(node.name, grp.name)
    return render_template('org_deploy.html', org = org, envs = envs)

@app.route('/follow/<nickname>')
@login_required
def follow(nickname):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    if user == g.user:
        flash(gettext('You can\'t follow yourself!'))
        return redirect(url_for('user', nickname = nickname))
    u = g.user.follow(user)
    if u is None:
        flash(gettext('Cannot follow %(nickname)s.', nickname = nickname))
        return redirect(url_for('user', nickname = nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You are now following %(nickname)s!', nickname = nickname))
    follower_notification(user, g.user)
    return redirect(url_for('user', nickname = nickname))

@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    if user == g.user:
        flash(gettext('You can\'t unfollow yourself!'))
        return redirect(url_for('user', nickname = nickname))
    u = g.user.unfollow(user)
    if u is None:
        flash(gettext('Cannot unfollow %(nickname)s.', nickname = nickname))
        return redirect(url_for('user', nickname = nickname))
    db.session.add(u)
    db.session.commit()
    flash(gettext('You have stopped following %(nickname)s.', nickname = nickname))
    return redirect(url_for('user', nickname = nickname))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    post = Post.query.get(id)
    if post == None:
        flash('Post not found.')
        return redirect(url_for('index'))
    if post.author.id != g.user.id:
        flash('You cannot delete this post.')
        return redirect(url_for('index'))
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.')
    return redirect(url_for('index'))
    
@app.route('/search', methods = ['POST'])
@login_required
def search():
    if not g.search_form.validate_on_submit():
        return redirect(url_for('index'))
    return redirect(url_for('search_results', query = g.search_form.search.data))

@app.route('/find', methods = ['GET', 'POST'])
@login_required
def find():
    rooms = ConferenceRoom.query.all()
    return render_template('rooms.html', rooms = rooms)

@app.route('/search_results/<query>')
@login_required
def search_results(query):
    results = Customer.query.whoosh_search(query, MAX_SEARCH_RESULTS).all()
    room_results = ConferenceRoom.query.whoosh_search(query, MAX_SEARCH_RESULTS).all()
    return render_template('search_results.html',
        query = query,
        results = results,
        room_results = room_results)

@app.route('/translate', methods = ['POST'])
@login_required
def translate():
    return jsonify({
        'text': microsoft_translate(
            request.form['text'],
            request.form['sourceLang'],
            request.form['destLang']) })
