from flask import Blueprint, Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.models import db


api_bp = Blueprint("api", __name__, url_prefix="")

load_dotenv()


@api_bp.route('/')
def hello_world():
    return 'Hello, World this is an update!!'

