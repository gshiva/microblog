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

    
def follower_notification(followed, follower):
    send_email("[Deployinator] %s is now following you!" % follower.nickname,
        ADMINS[0],
        [followed.email],
        render_template("follower_email.txt", 
            user = followed, follower = follower),
        render_template("follower_email.html", 
            user = followed, follower = follower))

def customer_notification(customer, user):
    send_email("You are all set to go!",
        user.email,
        [customer.email],
        render_template("customer_email.txt",
             customer = customer, user = user),
        render_template("customer_email.html",
             customer = customer, user = user))
