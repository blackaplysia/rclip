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

* POST /api/v1/messages
* GET /api/v1/messages/`key`
* DELETE /api/v1/messages/`key`

## 4-2. API documents

* You can see the Swagger document in /docs at any time while the service is running.

# 5. Build preparation

## 5-1. Define site local names

```
export APP_NAME=__YOUR_WEB_APP_NAME__
export DOCKER_ID=__YOUR_DOCKER_ID__

export RCLIPAPI_REPO=${DOCKER_ID}/rclipapi
export RCLIPAPI_IMAGE=${RCLIPAPI_REPO}:latest
cat docker-compose.yml | envsubst > docker-compose.site.yml
cat app.yml | envsubst > app.site.yml
```

# 5-2. Build and push rclipapi server image in your docker hub

```
docker build -t ${RCLIPAPI_IMAGE} .
docker push ${RCLIPAPI_IMAGE}
```

# 6. Run and test on local docker-compose

```
# run
docker-compose -f docker-compose.site.yml up -d

# test
sh -c 'RCLIP_API=http://localhost; KEY=$(rclip s -t hello); rclip r $KEY'

# clean up
docker-compose down
```

# 7. Run and test on local k8s (port=30120)

```
# run
kubectl apply -f app.site.yml

# test
sh -c 'KEY=$(RCLIP_API=http://localhost:30120 rclip s -t hello); RCLIP_API=http://localhost:30120 rclip r ${KEY}'

# clean up
kubectl delete -f app.site.yml
```

# 8. Run and test on Azure Web App

## 8-1. Create a web service

```
export AZ_GROUP=${APP_NAME}g
export AZ_PLAN=${APP_NAME}p
export AZ_ACR=${APP_NAME}r
export AZ_LOC=japaneast

az login
az group create -n ${AZ_GROUP} -l ${AZ_LOC}
az appservice plan create -g ${AZ_GROUP} -n ${AZ_PLAN} -l ${AZ_LOC} --sku B1 --is-linux
cat docker-compose.yml | envsubst > docker-compose.site.yml
az webapp create -g ${AZ_GROUP} -p ${AZ_PLAN} -n ${APP_NAME} --multicontainer-config-type compose --multicontainer-config-file docker-compose.site.yml
```

* The last task (`as webapp create`) will take a few minutes for the server to start properly.

## 8-2. Test with cURL and jq

```
curl -s -v -X POST -d '{"message": "hello"}' https://${APP_NAME}.azurewebsites.net/api/v1/messages | jq .response.key
curl -s -v -X POST -d '{"message": "hello"}' https://${APP_NAME}.azurewebsites.net/api/v1/messages | jq .response.key | sed 's/"//g' > tmp/key
curl -s -v https://${APP_NAME}.azurewebsites.net/api/v1/messages/$(cat tmp/key)
curl -s -v https://${APP_NAME}.azurewebsites.net/api/v1/messages/$(cat tmp/key) | jq .response.message
curl -s -v -X DELETE https://${APP_NAME}.azurewebsites.net/api/v1/messages/$(cat tmp/key)
```

## 8-3. Use rclip client tool

```
export RCLIP_API=https://${APP_NAME}.azurewebsites.net
rclip -h
echo hello | rclip s
sh -c 'KEY=$(rclip s -t hello); rclip r $KEY'
sh -c 'KEY=$(rclip s -t hello); rclip d $KEY'
sh -c 'KEY=$(rclip s -t hello); rclip r $KEY; rclip d $KEY; rclip r $KEY'
```

## 8-4. Clean up

```
az webapp delete -g ${AZ_GROUP} -n ${APP_NAME}
az appservice plan delete -g ${AZ_GROUP} -n ${AZ_PLAN}
az group delete -n ${AZ_GROUP}
```


