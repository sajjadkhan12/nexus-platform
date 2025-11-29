from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.notification import NotificationType

class NotificationBase(BaseModel):
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    link: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: str

class NotificationUpdate(BaseModel):
    is_read: bool

from uuid import UUID

class NotificationResponse(NotificationBase):
    id: str
    user_id: UUID
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
