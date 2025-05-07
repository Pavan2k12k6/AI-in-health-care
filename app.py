import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_loaded = load_dotenv()
if not dotenv_loaded:
    print("Warning: .env file not found!")

# Debug print to confirm it's loaded
print("DATABASE_URL =", os.environ.get("DATABASE_URL"))

# Check for required env variable
if not os.environ.get("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL environment variable not set!")

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

app.login_manager = login_manager 

# Required for Flask-Login to work!
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))



app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
# import routes 

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}


