"""
User model - Core authentication and authorization
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .base import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """
    Core user table backing auth flow.
    Extended with role-based access control.
    """
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # OAuth identifier (from Manus OAuth or JWT-based system)
    open_id = Column("openId", String(64), unique=True, nullable=False, index=True)

    # User information
    name = Column(String(255), nullable=True)
    email = Column(String(320), nullable=True, index=True)
    login_method = Column("loginMethod", String(64), nullable=True)

    # Role-based access control
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_signed_in = Column("lastSignedIn", DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def is_admin(self) -> bool:
        """Check if user has admin privileges"""
        return self.role == UserRole.ADMIN

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "openId": self.open_id,
            "name": self.name,
            "email": self.email,
            "loginMethod": self.login_method,
            "role": self.role.value,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "lastSignedIn": self.last_signed_in.isoformat() if self.last_signed_in else None,
        }
