from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.dependencies import get_db
from app.models import User
from app.schemas import LoginRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        username=user.username,
        password_hash=hash_password(user.password),
    )

    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    db.refresh(db_user)

    return db_user


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    db_user = (
        db.query(User)
        .filter(User.username == request.username)
        .first()
    )
    if db_user is None or not verify_password(request.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return Token(access_token=create_access_token(db_user.user_id))
