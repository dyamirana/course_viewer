from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash
import uuid

from ..models import User
from ..utils.core import get_db, tokens

router = APIRouter()

@router.post('/login')
def login(data: dict, db: Session = Depends(get_db)):
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        raise HTTPException(status_code=400, detail='Missing credentials')
    user = db.query(User).filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = str(uuid.uuid4())
    tokens[token] = user.id
    return {'token': token}
