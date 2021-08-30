#!/usr/bin/env python3

import hashlib
import os
import time
from redis import Redis
from fastapi import FastAPI, Request, Response, File, HTTPException

from models import MessageModel

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = os.environ.get("REDIS_PORT", "6379")
redis_ttl = os.environ.get("REDIS_TTL", "60")

redis = Redis(host=redis_host, port=redis_port)

app = FastAPI(redoc_url=None, openapi_url="/api/v1/openapi.json",
              title="rclip", description="Remote clipboard")

@app.get('/ping')
async def ping(request: Request):
    return {'request': 'ping',
            'response': 'pong'}

@app.post('/api/v1/messages')
async def post_message(message_data: MessageModel):
    message = message_data.message
    if message_data.ttl is not None:
        ttl = message_data.ttl
    else:
        ttl = redis_ttl
    key_src = message + ':' + str(time.time())
    key = hashlib.blake2s(key_src.encode(), digest_size=4).hexdigest()
    redis.set(key, message)
    redis.expire(key, ttl)
    return {'request': {'message': message},
            'response': {'key': key, 'message': message}}

@app.get('/api/v1/messages/{key}')
async def get_message(key: str):
    if redis.exists(key) == 0:
        raise HTTPException(status_code=404)
    message = redis.get(key)
    return {'request': {'key': key},
            'response': {'key': key, 'message': message}}

@app.delete('/api/v1/messages/{key}')
async def delete_message(key: str):
    if redis.exists(key) == 0:
        raise HTTPException(status_code=404)
    redis.delete(key)
    return {'request': {'key': key},
            'response': {'key': key}}

@app.post('/api/v1/files')
async def post_file(file: bytes = File(...)):
    size = len(file)
    key_src = str(size) + ':' + str(time.time())
    key = hashlib.blake2s(key_src.encode(), digest_size=4).hexdigest()
    redis.set(key, file)
    redis.expire(key, redis_ttl)
    return {'request': {'size': size},
            'response': {'key': key, 'size': size}}

@app.get('/api/v1/files/{key}')
async def get_file(key: str):
    if redis.exists(key) == 0:
        raise HTTPException(status_code=404)
    data = redis.get(key)
    return Response(content=data, media_type='application/octet-stream')

