import os 
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError


from app.database import get_db
from app.models import User
from app.schemas import LoginRequest,TokenResponse

import jwt 
from dotenv import load_dotenv
from pwdlib import PasswordHash
load_dotenv()

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM ="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES =30

password_hash = PasswordHash.recommended()


def hash_password(password:str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password:str,
                    hashed_password:str) -> bool:
    return password_hash.verify(plain_password,hashed_password)



def create_access_token(user_id:int) -> str:
    expire =datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload={
        "sub":str(user_id),
        "exp":expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )



router = APIRouter(tags=["Authentication"])

@router.post("/login",response_model=TokenResponse)
def login(
    data:LoginRequest,
    db:Session=Depends(get_db)
):
    user=db.scalar(select(User).where(User.email == data.email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid email or password")
    if not verify_password(data.password,user.passwaord_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="INvalid email id or password")


    token = create_access_token(user.id)

    return TokenResponse(access_token=token,token_type="bearer")




security = HTTPBearer()
def get_current_user(credentials:HTTPAuthorizationCredentials = Depends(security),db:Session= Depends(get_db))->User:
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )


        user_id = int(payload["sub"])

    except(InvalidTokenError,KeyError,ValueError):
        raise HTTPException(status_code=401,detail="invalid or expire token",headers={"WWW-Authenticate":"Bearer"})


    user = db.get(User,user_id)
    if user is None:
        raise HTTPException(status_code=401,detail="user not found",headers={"WWW-Authenticate":"Bearer"})



    return user


    



    