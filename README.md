# Event Reminder

[![Python 3.7.7](https://img.shields.io/badge/python-3.8.5-blue.svg)](https://www.python.org/downloads/release/python-377/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

The **Event Reminder** is a simple web application based on **[Flask](https://flask.palletsprojects.com/en/1.1.x/)** framework, **[Bootstrap](https://getbootstrap.com/)** user interface framework and **[FullCalendar](https://fullcalendar.io/)** full-sized JavaScript calendar. 
 
The main purpose of the **Event Reminder** application is to send notifications about upcoming events to selected users. The application allows a standard user to enter event data, process it and display with the **FullCalendar** API. Moreover, the application has a built-in admin panel for the management of users, events, notification service, display app related logs and basic system info on app dashboard partly based on **[Chart.js](https://www.chartjs.org/)**. Sending reminders through the notification service is performed by the SMTP e-mail server provided by the admin user and by the APScheduler library.
The application has implemented integration with the **Elasticsearch** search engine.
***

## Getting Started

Below instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 


### Requirements
Minimum version of python required to run the **Event Reminder** application - **Python 3.7.7**

Python third party packages:
* [Flask](https://flask.palletsprojects.com/en/1.1.x/)
* [Flask-SQLalchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/)
* [Flask-WTF](https://flask-wtf.readthedocs.io/en/stable/)
* [Flask-APScheduler](https://github.com/viniciuschiele/flask-apscheduler)
* [Flask-Login](https://flask-login.readthedocs.io/en/latest/)
* [Flask-Caching](https://flask-caching.readthedocs.io/en/latest/)
* [Requests](https://requests.readthedocs.io/en/master/)
* [elasticsearch](https://pypi.org/project/elasticsearch/)
* [python-dotenv](https://pypi.org/project/python-dotenv/)
* [psycopg2-binary](https://pypi.org/project/psycopg2-binary/)

***
## Installation with venv

The application can be build and run locally with `virtualenv` tool. Run following commands in order to create virtual environment and install the required packages.

```bash
$ virtualenv venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

### Environment variables

The **Event Reminder** application depends on some specific environment variables. 
To run application successfully the environment variables should be stored in `.env` file in the root application directory (`event-reminder` dir).

```
# '.env' file
SECRET_KEY=use-some-random-key
APPLICATION_MODE='development'                     # for development will use SQLite db
# APPLICATION_MODE='production'                    # for production will use PostgreSQL db
DEV_DATABASE_URL=sqlite:///app.db                  # example for SQLite
PROD_DATABASE_URL=postgresql://reminderuser:password@db:5432/reminderdb     # example for PostgreSQL
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=xxx.yyy@example.com               # account which will be used for SMTP email service
MAIL_PASSWORD=xxxxxxx                           # password for above account
ELASTICSEARCH_URL=http://localhost:9200         # optional
CHECK_EMAIL_DOMAIN='False'                      # if 'True' validate whether email domain/MX record exist 
```
The `.env` file will be imported by application on startup.

### Elasticsearch server
Elasticsearch is not required to run the **Event Reminder** application. Without the specified `ELASTICSEARCH_URL` variable and/or running the Elasticsearch node, the application will run, but no search function will be available.

The fastest and easiest way to start Elasticsearch node is to run it in Docker container.
You can obtain Elasticsearch for Docker issuing below command (examples for 7.7.0 version):
```bash
$ docker pull docker.elastic.co/elasticsearch/elasticsearch:7.7.0
``` 
Then start a single node cluster with Docker:
```bash
$ docker run --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -d docker.elastic.co/elasticsearch/elasticsearch:7.7.0
```

### Running the App

Before running the **Event Reminder** app you can use script `init_db.py` to initialize database and add some dummy data that can be used later in the processing.
```bash
# Below script will create default admin username 'admin' with password 'admin'
(venv) $ python init_db.py
# You can create a different user instead of the default one using proper options. Below example for username 'bob' with password 'LikePancakes123#'.
(venv) $ python init_db.py -u bob -p LikePancakes123#
# For more info please use:
(venv) $ python init_db.py --help
```

After adding dummy data, you can start the application. First of all set the `FLASK_APP` environment variable to point `run.py` script and then invoke `flask run` command.
```bash
(venv) $ cd reminder/
(venv) $ export FLASK_APP=run.py
# in MS Windows OS run 'set FLASK_APP=run.py'
(venv) $ flask run
```

***
## Installation with Docker-Compose
The application can be also build and run locally with Docker-Compose tool. Docker-Compose allows you to create working out-of-the-box example of **Event Reminder** application with Gunicorn, Elasticsearch and PostgreSQL with some dummy data on board.

### Running the App
To build and run app with Docker-Compose - clone the repo and follow the quick-start instructions below. 

In order to correctly start the application, you must run the following commands in the project root directory (`event-reminder`).

1. Before running `docker-compose` command you should create `.env-web` and `.env-db` files (ENVs for Flask app and PostgreSQL). The best solution is to copy the existing example files and edit the necessary data.
```bash
# Create .env-web and .env-db files using examples from repository
$ cp docker/web/.env-web-example docker/web/.env-web
$ cp docker/db/.env-db-example docker/db/.env-db
```
2. Build and start containers using the commands shown below:
```bash
# To build containers specified in docker-compose.yml file
$ docker-compose build
# To start containers (add -d to run them in the background)
$ docker-compose up -d
# To verify status of the application:
$ docker-compose ps
```
3. Open `http://localhost:8080` in your browser to see the application running. Login with default credentials:
   - admin user: `admin`
   - default pass: `admin`
   

4. To stop application run:
```bash
$ docker-compose stop
```