from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import database, auth
from enum import Enum
from dateutil.parser import isoparse

from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy import desc, asc
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Annotated
from datetime import timedelta, datetime, timezone



# Initialize the FastAPI application
app = FastAPI() 

# Configuration of OAuth2. It shows the endpoint of token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# TaskPriority is an Enum class that defines the priority levels for tasks
class TaskPriority(Enum):
    Low = 3
    Medium = 2
    High = 1


# TaskSchemaInput is the input model for creating and updating tasks
class TaskSchemaInput(BaseModel):
    task_title: str = Field(max_length=30, description="Task title, maximum 30 characters")# The titles of Pydanitc models must match the column names in the database
    task_description: Optional[str] = Field(None, max_length=50, description="Task description, maximum 50 characters") # Optional fields must be set to None if they are set to NULL in the database
    task_is_complete: bool = False
    task_date: Optional[datetime] = datetime.now()+timedelta(days=1)
    task_priority: TaskPriority = TaskPriority.Low.value
    
    #field_validator is used to validate the task_date field
    @field_validator("task_date", mode="before")
    def parse_and_validate_datetime(cls, value):
        
        if value is None:
            return None
        
        try:
            dt = isoparse(value) if isinstance(value, str) else value
        except Exception as e:
            raise ValueError("Task date must be in ISO format (e.g. YYYY-MM-DDTHH:MM)")

       # Convert to UTC and remove timezone info
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
       
            
        # Check if the date is in the future
        if dt <= datetime.now():
            raise ValueError("Task date must be in the future")
        return dt
    

    # This will allow us to return Task objects directly
    model_config = ConfigDict(from_attributes=True)
       

#TaskSchemaOutput is the output model for getting tasks
class TaskSchemaOutput(BaseModel):
    task_id: int
    task_title: str 
    task_description: Optional[str] = None
    task_is_complete: bool
    task_date: Optional[datetime]
    task_priority: TaskPriority = TaskPriority.Low.value
    

    model_config = ConfigDict(from_attributes=True)


# This function is used to get the database session. It will be used in all endpoints that need to access the database.
def get_db():
    db = database.Session() 
    try:
        yield db
    finally:
        db.close()



#get_tasks is the endpoint to get all tasks. It can filter by title, is_complete, order, sort_by, skip and limit
@app.get("/tasks", response_model=List[TaskSchemaOutput]) 
async def get_tasks(token: Annotated[str, Depends(oauth2_scheme)], title: Optional[str] = None,  is_complete: Optional[bool] = None, order: Optional[str] = "asc", sort_by: Optional[str] = None, skip: int = 0, limit: int = 10, db: Session = Depends(get_db), current_user: database.User = Depends(auth.get_current_user)):


    task = db.query(database.Task).filter(database.Task.users_id == current_user.users_id)

    if title is not None:
        task = task.filter(database.Task.task_title.ilike(f"%{title}%"))

    if is_complete is not None:
        task = task.filter(database.Task.task_is_complete == is_complete)

    #
    if sort_by is not None:
        sort_attribute = getattr(database.Task, sort_by, None)
        if sort_attribute is None:
            raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")
        if order.lower() == "desc":
            task = task.order_by(desc(sort_attribute))
        else:
            task = task.order_by(asc(sort_attribute))

    
    # Return the tasks with pagination
    return task.offset(skip).limit(limit).all()


# get_task is the endpoint to get a specific task by its ID
@app.get("/tasks/{task_id}", response_model=TaskSchemaOutput)
async def get_task(token: Annotated[str, Depends(oauth2_scheme)], task_id: int, db: Session = Depends(get_db), current_user: database.User = Depends(auth.get_current_user)):
    task = db.query(database.Task).filter(database.Task.users_id == current_user.users_id, database.Task.task_id == task_id).first()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task



# create_task is the endpoint to create a new task
@app.post("/tasks", response_model=TaskSchemaInput, status_code=status.HTTP_201_CREATED,  responses={
    201: {
    "description": "Task Created",
    "content": {"application/json": {
    }}}})
async def create_task(token: Annotated[str, Depends(oauth2_scheme)], task: TaskSchemaInput,  db: Session = Depends(get_db), current_user: database.User = Depends(auth.get_current_user)):
    

    
    new_task = database.Task(
        task_title=task.task_title, 
        task_description=task.task_description, 
        task_is_complete= False, 
        task_date=task.task_date, 
        users_id = current_user.users_id, 
        task_priority = task.task_priority.value if not isinstance(task.task_priority, int) else task.task_priority
    )   
    
    
    db.add(new_task)
    db.commit() 
    db.refresh(new_task)
    return new_task



# update_task is the endpoint to update a specific task by its ID
@app.put("/tasks/{task_id}", response_model=TaskSchemaInput ,  status_code=status.HTTP_201_CREATED,  responses={
    201: {
    "description": "Task Created",
    "content": {"application/json": {
    }}}})
async def update_task(token: Annotated[str, Depends(oauth2_scheme)], task_id: int, task: TaskSchemaInput, db: Session = Depends(get_db), current_user: database.User = Depends(auth.get_current_user)):
    db_task = db.query(database.Task).filter(
        database.Task.task_id == task_id,
        database.Task.users_id == current_user.users_id).first()

    
    # Check if the task exists
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.task_title = task.task_title
    db_task.task_description = task.task_description
    db_task.task_is_complete = task.task_is_complete
    db_task.task_date = task.task_date
    db_task.users_id = current_user.users_id
    db_task.task_priority = task.task_priority.value if not isinstance(task.task_priority, int) else task.task_priority
    db.commit()
    db.refresh(db_task)
    return db_task

# delete_task is the endpoint to delete a specific task by its ID
@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT,  responses={
    204: {
    "description": "No Content",
    "content": {"application/json": {
    "example": {"message": "Task deleted"}}}}})
async def delete_task(token: Annotated[str, Depends(oauth2_scheme)], task_id: int, db: Session = Depends(get_db), current_user: database.User = Depends(auth.get_current_user)):
    db_task = db.query(database.Task).filter(database.Task.users_id == current_user.users_id, database.Task.task_id == task_id).first()
  
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task) #Delete a specific record in database
    db.commit()
    


#login is the endpoint to login a user and get a token
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(form_data.username, form_data.password, db)
    if not user:
        # If the user is not found, raise an HTTPException with status code 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
            )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Create an access token with the user ID and scope
    access_token = auth.create_access_token(data=user, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}