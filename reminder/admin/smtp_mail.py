from flask import current_app, render_template, flash
from flask_login import current_user
import smtplib
from email.message import EmailMessage


def email_content(recipients_list, event, smtp_obj, msg):
    """
    Function called in send_email() func.
    Func is responsible for creating and sending emails to appropriate recipients.
    """
    for recipient in recipients_list:
        # Send emails.
        # Removes the previous recipient from the inside of the msg object.
        # Only the current recipient is visible in content.
        msg.__delitem__('To')
        # Assign new recipient.
        msg['To'] = [recipient.email]
        text = render_template("admin/email.txt", recipient=recipient, event=event)
        html = render_template("admin/email.html", recipient=recipient, event=event)
        # Send msg in text/plain and text/html versions.
        msg.clear_content()
        msg.set_content(text)
        msg.add_alternative(html, subtype='html')
        smtp_obj.send_message(msg)
        current_app.logger_admin.info(f'Email service: msg has been sent to "{recipient}"')
    current_app.logger_admin.info(f'Email service: all emails have been sent out')


def send_email(subject, recipients, event):
    """
    Function establish connection with SNMP server and send emails to selected recipients.
    """
    recipients_list = recipients
    mail_sender = current_app.config['MAIL_USERNAME']
    mail_pass = current_app.config['MAIL_PASSWORD']
    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']
    mail_security = current_app.config['MAIL_SECURITY']
    # Create the container email message.
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_sender
    # Connects to SMTP server. All emails will be sent during one connection.
    if mail_security == 'tls':
        with smtplib.SMTP(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
            # smtp_obj.set_debuglevel(1)
            smtp_obj.ehlo()
            smtp_obj.starttls()
            smtp_obj.ehlo()
            smtp_obj.login(mail_sender, mail_pass)
            current_app.logger_admin.info(f'Email service: connected with "{mail_server}:{mail_port}"')
            email_content(recipients_list, event, smtp_obj, msg)
        current_app.logger_admin.info(f'Email service: disconected with "{mail_server}:{mail_port}"')
    elif mail_security == 'ssl':
        with smtplib.SMTP_SSL(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
            # smtp_obj.set_debuglevel(1)
            smtp_obj.ehlo()
            smtp_obj.login(mail_sender, mail_pass)
            current_app.logger_admin.info(f'Email service: connected with "{mail_server}:{mail_port}"')
            email_content(recipients_list, event, smtp_obj, msg)
        current_app.logger_admin.info(f'Email service: disconected with "{mail_server}:{mail_port}"')


def test_email():
    """
    Test mail server config.
    """
    mail_sender = current_app.config['MAIL_USERNAME']
    mail_pass = current_app.config['MAIL_PASSWORD']
    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']
    mail_security = current_app.config['MAIL_SECURITY']
    try:
        if mail_security == 'tls':
            with smtplib.SMTP(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
                # smtp_obj.set_debuglevel(1)
                smtp_obj.ehlo()
                smtp_obj.starttls()
                smtp_obj.ehlo()
                smtp_obj.login(mail_sender, mail_pass)
                # flash('Connection with mail server established correctly! The notify service is running!', 'success')
                return True
        elif mail_security == 'ssl':
            with smtplib.SMTP_SSL(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
                # smtp_obj.set_debuglevel(1)
                smtp_obj.ehlo()
                smtp_obj.login(mail_sender, mail_pass)
                # flash('Connection with mail server established correctly! The notify service is running!', 'success')
                return True
    except smtplib.SMTPAuthenticationError:
        flash('Connection issue. Check your credentials!', 'danger')
        current_app.logger_admin.info('Email service test: connection issue, wrong credentials')
        return False
    except Exception as error:
        flash('Connection issue. Check mail configurration!', 'danger')
        current_app.logger_admin.info('Email service test: connection issue, wrong configuration')
        return False



