from sqlalchemy import create_engine
from typing import Optional
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column, Mapped
from sqlalchemy import Integer, String, Boolean,  ForeignKey, DateTime
from dotenv import load_dotenv
import os
load_dotenv()

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Create a connection to the database using the environment variables
engine = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"
)

# Create a session
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Create a base class for declarative models
Base = declarative_base()



# Create the tables in the database
class Task(Base):
    __tablename__ = 'task'

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True)
    task_title: Mapped[str] = mapped_column(String(30), nullable=False)
    task_description: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    task_is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    task_date: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    task_priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    
    users_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.users_id"), nullable=False)

   



# This is the user table
class User(Base):

    __tablename__ = 'users'

    users_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, autoincrement=True)
    users_username: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    users_hashed_password: Mapped[str] = mapped_column(String(50), nullable=False)
    