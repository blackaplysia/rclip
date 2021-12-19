#!/usr/bin/env python3

from pydantic import BaseModel
from typing import Optional

class MessageModel(BaseModel):
    message: str
    category: Optional[str] = None
    ttl: Optional[int] = None
