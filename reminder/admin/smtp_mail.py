from flask import current_app, render_template, flash
import smtplib
from email.message import EmailMessage


def email_content(recipients_list, event, smtp_obj, msg):
    """
    Function called in send_email() func.
    Func is responsible for creating and sending emails to appropriate recipients.
    Returns notified users.
    """
    recipients_rx, recipients_not_rx = [], []
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
        # Additional protection in case the email does not exist
        try:
            smtp_obj.send_message(msg)
            current_app.logger_admin.info(f'Email service: msg has been sent to "{recipient}"')
            # only for test
            # print(f'Mail sent to {recipient}')
            recipients_rx.append(recipient)
        except smtplib.SMTPRecipientsRefused:
            current_app.logger_admin.info(f'Email service: The problem occurred while sending a message '
                                          f'to "{recipient}". Probably email doesn\'t exist')
            # only for test
            # print(f'Problem with {recipient}')
            recipients_not_rx.append(recipient)
    current_app.logger_admin.info(f'Email service: all emails have been sent out')
    return recipients_rx


def send_email(subject, recipients, event, mail_server, mail_port, mail_security, mail_sender, mail_pass):
    """
    Function establish connection with SMTP server and send emails to selected recipients.
    """
    recipients_list = recipients
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
            notified_users = email_content(recipients_list, event, smtp_obj, msg)
        current_app.logger_admin.info(f'Email service: disconnected with "{mail_server}:{mail_port}"')
    # SSL
    else:
        with smtplib.SMTP_SSL(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
            # smtp_obj.set_debuglevel(1)
            smtp_obj.ehlo()
            smtp_obj.login(mail_sender, mail_pass)
            current_app.logger_admin.info(f'Email service: connected with "{mail_server}:{mail_port}"')
            notified_users = email_content(recipients_list, event, smtp_obj, msg)
        current_app.logger_admin.info(f'Email service: disconnected with "{mail_server}:{mail_port}"')
    return notified_users


def test_email(mail_server, mail_port, mail_security, mail_sender, mail_pass):
    """
    Test mail server config.
    """
    try:
        if mail_security == 'tls':
            with smtplib.SMTP(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
                # smtp_obj.set_debuglevel(1)
                smtp_obj.ehlo()
                smtp_obj.starttls()
                smtp_obj.ehlo()
                smtp_obj.login(mail_sender, mail_pass)
                return True
        elif mail_security == 'ssl':
            with smtplib.SMTP_SSL(host=mail_server, port=mail_port, timeout=5) as smtp_obj:
                # smtp_obj.set_debuglevel(1)
                smtp_obj.ehlo()
                smtp_obj.login(mail_sender, mail_pass)
                return True
    except smtplib.SMTPAuthenticationError:
        flash('Connection issue. Check your credentials!', 'danger')
        current_app.logger_admin.info('Email service test: connection issue, wrong credentials')
        return False
    except Exception as error:
        # smtplib.SMTPConnectError
        flash('Connection issue. Check mail configuration!', 'danger')
        current_app.logger_admin.info(f'Email service test: connection issue, wrong configuration. {error}')
        return False