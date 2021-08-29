#!/usr/bin/env python3

from pydantic import BaseModel

class MessageModel(BaseModel):
    message: str
