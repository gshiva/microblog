from flask import render_template
from flask.ext.mail import Message
from app import mail
from decorators import async
from config import ADMINS

@async    
def send_async_email(msg):
    mail.send(msg)
    
def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender = sender, recipients = recipients)
    msg.body = text_body
    msg.html = html_body
    send_async_email(msg)
    #thr = threading.Thread(target = send_async_email, args = [msg])
    #thr.start()

    
def deploy_notification(org, msg):
    send_email("ownCloud has been launched in %s!" % org,
        ADMINS[0],
        ["shivakumar.gopalakrishnan@varian.com"],
        render_template("deploy_email.txt", 
            org = org, msg = msg),
        render_template("deploy_email.html", 
            org = org, msg = msg))
        