# 1. Overview

rclip is a simple message clipboard.

# 2. Usage

## 2-1. Send a message

* Subcommand `send` (or `s`) sends a message to the server and print a key which you need when you will receive it.
* You can give rclip the message by an arguemt, file or stdin.

```
$ rclip s -t hello1
f0ef6a40
$ echo hello2 | rclip s
b53dcfa1
$ rclip s -f message.txt
9b8bc78c
```

## 2-2. Receive the message

* Subcommand `receive` (or `r`) receives the message related to the given key.
* Messages has the time-to-live (TTL) defined by the server.  So you cannot receive any messages after the TTL.

```
$ rclip r b53dcfa1
hello2
$ sleep 60
$ rclip r b53dcfa1
404 Not Found
```

## 2-3. Delete the message

* Subcommand `delete` (or `d`) deletes the message related to the given key.
* Usually there is no need to delete messages because they has the TTL.

```
$ rclip d b53dcfa1
200
$ rclip d b53dcfa1
404 Not Found
```

# 3. Technology

## 3-1. Server

* Azure Web App
* Azure Container Registry
* API Server: Unicorn + FastAPI
* DB: redis

## 3-2. Client

* Python requests

# 4. API

## 4-1. API list

* POST /message
* GET /message/`key`
* DELETE /message/`key`

## 4-2. API documents

* You can see the Swagger document in /docs at any time while the service is running.

# 5. Local install

```
# build and run
docker-compose up -d

# test
sh -c 'RCLIP_API=http://localhost; KEY=$(rclip s -t hello); rclip r $KEY'
```

# 6. Azure Webapp

## 6-1. Define site local names

```
export APP_NAME=__YOUR_WEB_APP_NAME__
export DOCKER_ID=__YOUR_DOCKER_ID__
```

## 6-2. Create site local files

```
cat docker-compose.yml | envsubst > docker-compose.site.yml
```

## 6-3. Build and test locally

```
export DOCKER_REPO=${DOCKER_ID}/rclipapi
export DOCKER_IMAGE=${DOCKER_REPO}:latest

docker build -t ${DOCKER_IMAGE} ./api
docker push ${DOCKER_IMAGE}

# Test locally
docker-compose -f tmp/docker-compose.site.yml up -d
```

## 6-4. Create a web service

```
export AZ_GROUP=${APP_NAME}g
export AZ_PLAN=${APP_NAME}p
export AZ_ACR=${APP_NAME}r
export AZ_LOC=japaneast

az login
az group create -n ${AZ_GROUP} -l ${AZ_LOC}
az appservice plan create -g ${AZ_GROUP} -n ${AZ_PLAN} -l ${AZ_LOC} --sku B1 --is-linux
az webapp create -g ${AZ_GROUP} -p ${AZ_PLAN} -n ${APP_NAME} --multicontainer-config-type compose --multicontainer-config-file docker-compose.site.yml
az webapp config container set -g ${AZ_GROUP} -n ${APP_NAME} -r ${ACR_REPO} -u ${ACR_USER} -p ${ACR_PASS}
```

* It will take a few minutes for the server to start properly.

## 6-5. Test with cURL and jq

```
curl -s -v -X POST -d '{"message": "hello"}' https://${AZ_APP}.azurewebsites.net/message | jq .response.key
curl -s -v -X POST -d '{"message": "hello"}' https://${AZ_APP}.azurewebsites.net/message | jq .response.key | sed 's/"//g' > tmp/key
curl -s -v https://${AZ_APP}.azurewebsites.net/message/$(cat tmp/key)
curl -s -v https://${AZ_APP}.azurewebsites.net/message/$(cat tmp/key) | jq .response.message
curl -s -v -X DELETE https://${AZ_APP}.azurewebsites.net/message/$(cat tmp/key)
```

## 6-6. Use rclip client tool

```
RCLIP_API=https://${AZ_APP}.azurewebsites.net
rclip -h
echo hello | rclip s
sh -c 'KEY=$(rclip s -t hello); rclip r $KEY'
sh -c 'KEY=$(rclip s -t hello); rclip d $KEY'
sh -c 'KEY=$(rclip s -t hello); rclip r $KEY; rclip d $KEY; rclip r $KEY'
```
