# Event Reminder

The **Event Reminder** is a simple web application based on **[Flask](https://flask.palletsprojects.com/en/1.1.x/)** framework, **[Bootstrap](https://getbootstrap.com/)** user interface framework and **[FullCalendar](https://fullcalendar.io/)** full-sized JavaScript calendar. 
 
The main purpose of the **Event Reminder** application is to send notifications about upcoming events to selected users. The application allows a standard user to enter event data, process it and display with the **FullCalendar** API. Moreover, the application has a built-in admin panel for the management of users, events, notification service and display app related logs. Sending reminders through the notification service is performed by the SMTP e-mail server provided by the admin user and by the APScheduler library.

***

## Getting Started

Below instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 


### Requirements

* [Flask](https://flask.palletsprojects.com/en/1.1.x/)
* [Flask-SQLalchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/)
* [Flask-WTF](https://flask-wtf.readthedocs.io/en/stable/)
* [Flask-APSchedular](https://github.com/viniciuschiele/flask-apscheduler)
* [Flask-login](https://flask-login.readthedocs.io/en/latest/)

### Installation

The application can be build locally with `virtualenv` tool. Run following commands in order to create virtual environment and install the required packages.

```bash
$ virtualenv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

### Environment varaibles

To run application successfully please provide the following environment variables (example for Linux):
```
export SECRET_KEY='use-some-random-key'
export USER_DEFAULT_PASS='provide-some-default-pass'
export MAIL_SERVER=smtp.example.com
export MAIL_PORT=587
export MAIL_USERNAME=xxx.yyy@example.com    # account which will be used for SMTP email service
export MAIL_PASSWORD=xxxxxxx                # password for above account
```
If you are using MS Windows, you need to replace `export` with `set` in each of the statements above.

***

## Running the App

Before running the Event Reminder app you can use script `init_db.py` to initialize database and add some dummy data that can be used later in the processing.
```bash
(venv) $ cd reminder
(venv) $ python init_db.py
```

After adding dummy data, you can start the application. First of all set the `FLASK_APP` environment variable to point `run.py` script and then invoke `flask run` command.
```bash
(venv) $ export FLASK_APP=run.py
# in MS Windows OS run 'set FLASK_APP=run.py'
(venv) $ cd ..
(venv) $ flask run
```