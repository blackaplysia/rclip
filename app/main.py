#!/usr/bin/env python3

import hashlib
import os
import time
from redis import Redis
from fastapi import FastAPI, Request, Response, File, UploadFile, HTTPException

from models import MessageModel

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = os.environ.get("REDIS_PORT", "6379")
redis_ttl = os.environ.get("REDIS_TTL", "60")
redis_ttl_file = os.environ.get("REDIS_TTL_FILE", "1800")
key_width = os.environ.get("KEY_WIDTH", "4")

redis = Redis(host=redis_host, port=redis_port)

app = FastAPI(redoc_url=None, openapi_url="/api/v1/openapi.json",
              title="rclip", description="Remote clipboard")

@app.get('/api/v1/clipboard')
async def ping(request: Request):
    return {'request': '(ping)',
            'response': {
                'acq': 'pong',
                'client': {
                    'host': request.client.host,
                    'port': request.client.port
                }
            }
    }

@app.delete('/api/v1/clipboard')
async def delete_clippboard(request: Request):
    result = 'OK' if redis.flushdb() == True else 'NG'
    return {'request': '(flush)',
            'response': {'result': result}}

@app.post('/api/v1/messages')
async def post_message(message_data: MessageModel):
    message = message_data.message
    if message_data.category is not None:
        category = message_data.category
    else:
        category = '__message__'
    if message_data.ttl is not None:
        ttl = message_data.ttl
    else:
        ttl = redis_ttl
    key_time = str(time.time())
    key_src = message + ':' + key_time
    key_src_shadow = '*:' + key_time
    key = hashlib.blake2s(key_src.encode(), digest_size=int(key_width)).hexdigest()
    redis.set(key, message)
    redis.hset(key+'+hash', 'key_src', key_src_shadow)
    redis.hset(key+'+hash', 'category', category)
    redis.hset(key+'+hash', 'size', len(message))
    redis.expire(key, ttl)
    redis.expire(key+'+hash', ttl)
    return {'request': {'message': message},
            'response': {'key': key, 'message': message}}

@app.get('/api/v1/messages/{key}')
async def get_message(key: str):
    if redis.exists(key) == 0:
        raise HTTPException(status_code=404)
    message = redis.get(key)
    category = redis.hget(key+'+hash', 'category')
    return {'request': {'key': key},
            'response': {'key': key, 'category': category, 'message': message}}

@app.delete('/api/v1/messages/{key}')
async def delete_message(key: str):
    if redis.exists(key) == 0:
        raise HTTPException(status_code=404)
    redis.delete(key)
    redis.delete(key+'+hash')
    return {'request': {'key': key},
            'response': {'key': key}}

@app.post('/api/v1/files')
async def post_file(file: UploadFile = File(...)):
    data = file.file.read()
    size = len(data)
    ttl = redis_ttl_file
    key_src = str(file.filename) + ':' + str(time.time())
    key = hashlib.blake2s(key_src.encode(), digest_size=int(key_width)).hexdigest()
    redis.set(key, data)
    redis.hset(key+'+hash', 'key_src', key_src)
    redis.hset(key+'+hash', 'category', '__file__')
    redis.hset(key+'+hash', 'size', size)
    redis.expire(key, ttl)
    redis.expire(key+'+hash', ttl)
    return {'request': {'size': size},
            'response': {'key': key, 'size': size}}

@app.get('/api/v1/files/{key}')
async def get_file(key: str):
    if redis.exists(key) == 0:
        raise HTTPException(status_code=404)
    data = redis.get(key)
    return Response(content=data, media_type='application/octet-stream')
