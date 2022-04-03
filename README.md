# 1. Overview

rclip is a simple message clipboard.

# 2. Usage

## 2-1. Send a message or a file

* Subcommand `send` (or `s`) sends a message or a file to the server and print a key which you need when you will receive it.
* You can give rclip the message by an arguemt, file or stdin.

```
$ rclip s -t hello1 # text message
f0ef6a40
$ rclip s -f srcfile # file
a4d8354c
$ echo hello2 | rclip s # text message from /dev/stdin
b53dcfa1
$ rclip s -f srcfile -T 6000 # TTL 6000sec
a4d8354c
```

## 2-2. Receive the message

* Subcommand `receive` (or `r`) receives the message related to the given key.
* Messages has the time-to-live (TTL) defined by the server.  So you cannot receive any messages after the TTL.

```
$ rclip r b53dcfa1
hello2
$ rclip r b53dcfa1 > destfile # for text message
$ rclip r b53dcfa1 -o destfile # for text message
$ rclip r a4d8354c # for file
$ sleep 60
$ rclip r b53dcfa1 # expired after TTL
404 Not Found
```

## 2-3. Delete the message

* Subcommand `delete` (or `d`) deletes the message related to the given key.
* Usually there is no need to delete messages because they has the TTL.

```
$ rclip d b53dcfa1 # delete text message or file successfully
200
$ rclip d b53dcfa1 # failed to delete text message or file
404 Not Found
```

## 2-4. Flush all messages

* Subcommand `flush` flushes the message database on the server.
* Usually there is no need to flush database because their data has the TTL.

```
$ rclip flush
200 OK
```

## 2-5. Test connection to the server

* Subcommand `ping` sends ping message to the server.

```
$ rclip ping
pong
$ rclip ping -c # Show client information (IP address and port)
pong 123.45.67.89 56789
```

# 3. Technology

## 3-1. Server

* API Server: Unicorn + FastAPI
* DB: redis

## 3-2. Client

* Python requests

# 4. API list

## 4-1. API list

* GET /api/v1/clipboard (rclip ping)
* DELETE /api/v1/clipboard (rclip flush)
* POST /api/v1/messages (rclip send)
* POST /api/v1/files (rclip send)
* GET /api/v1/messages/`key` (rclip receive)
* GET /api/v1/files/`key` (rclip receive)
* DELETE /api/v1/messages/`key` (rclip delete)

# 5. Build servers

## 5-1. .env

Copy _env to .env.

```
$ cp _env .env
```

Edit .env.

* `REDIS_TTL`: Message TTL (sec) by default
* `KEY_WIDTH`: key length (`KEY_WIDTH` * 2 characters)
* `PORT`: port number of api container
* `EXPOSED_PORT`: exposed port number of api container to host

## 5-2. Start servers

```
$ sudo docker-compose up -d
```

## 5-3. Test

```
$ curl http://localhost:****/api/v1/clipboard # response as rclip ping, **** means EXPOSED_PORT
```

# 6. Client tools

## 6-1. Install rclip client

```
$ pip3 install .
$ rclip -h
```
## 6-2. Environment

```
$ export RCLIP_API=http://your_host:your_port/
$ rlip -h # Help message includes your message api url defined by ${RCLIP_API}
```

## 6-3. Test

```
$ rclip ping
```

# License

[Apache2.0 License](https://github.com/mkyutani/rclip/blob/main/LICENSE)
