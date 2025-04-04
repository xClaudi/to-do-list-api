from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  
from dotenv import load_dotenv
import os

load_dotenv()

from sqlalchemy.orm import Session
import database
from datetime import datetime, timedelta

def get_db():
    db = database.Session() 
    try:
        yield db
    finally:
        db.close()



# Information wheres the endpoint of token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


SECRET_KEY = os.getenv("SECRET_KEY")

# Algorithm used to encode the token
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30






# This function is used to get the current user from the token. It will be used in all endpoints that need to access the database.
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):

    try:

        # Decode the token using the secret key and algorithm
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Get the user ID from the token payload
        user_id_str = payload.get("sub")

        if user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
       
        user_id = int(user_id_str)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(database.User).filter(database.User.users_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    
    return user
    

# This function is used to authenticate the user. It will be used in the login endpoint.
def authenticate_user(username: str, password: str, db: Session):
    user = db.query(database.User).filter(database.User.users_username == username).first()
   
    if not user:
        return False
    
    if password == user.users_hashed_password:
        return {"sub": str(user.users_id), "scope": "items"}





    

# This function is used to create the access token. It will be used in the login endpoint.
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    # Set the expiration time for the token
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() +timedelta(minutes=15)

    to_encode.update({"exp": expire})

    # Encode the token using the secret key and algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


    
    