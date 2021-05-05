# Overview

rclip is a simple message clipboard.

# Client command.

## Send a message.

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

## Receive the message.

* Subcommand `receive` (or `r`) receives the message related to the given key.
* Messages has the time-to-live (TTL) defined by the server.  So you cannot receive any messages after the TTL.

```
$ rclip r b53dcfa1
hello2
$ sleep 60
$ rclip r b53dcfa1
404 Not Found
```

## Delete the message.

* Subcommand `delete` (or `d`) deletes the message related to the given key.
* Usually there is no need to delete messages because they has the TTL.

```
$ rclip d b53dcfa1
200
$ rclip d b53dcfa1
404 Not Found
```

# Technology

## Server

* Azure Web App
* Azure Container Registry
* API Server: Unicorn + FastAPI
* DB: redis

## Client

* Python requests

# Install

* Define names for azure resources.

```
export AZ_APP=__YOUR_WEB_APP_NAME__
export AZ_GROUP=${AZ_APP}g
export AZ_PLAN=${AZ_APP}p
export AZ_ACR=${AZ_APP}r
export AZ_LOC=japaneast
```

* Create a resource group.

```
az login
az group create -n ${AZ_GROUP} -l ${AZ_LOC}
```

* Create a container registry in ACR.

```
az acr create -g ${AZ_GROUP} -n ${AZ_ACR} --sku basic --admin-enabled true
export ACR_REPO=${AZ_ACR}.azurecr.io
export ACR_USER=${AZ_ACR}
export ACR_PASSWORD=`az acr credential show -n ${AZ_ACR} -g ${AZ_GROUP} --query passwords[0].value | sed 's/"//g'`
```

* Build and store images in ACR.

```
docker-compose build
docker tag rclipapi:latest ${AZ_ACR}.azurecr.io/rclipapi:latest
docker tag rclipredis:latest ${AZ_ACR}.azurecr.io/rclipredis:latest
az acr login -n ${AZ_ACR}
docker push ${AZ_ACR}.azurecr.io/rclipapi:latest
docker push ${AZ_ACR}.azurecr.io/rclipredis:latest
```

* Configure docker-compose.yml for ACR.

```
# Replace some environment variables.
cat docker-compose-azure.yml | envsubst > tmp/docker-compose-azure.site.yml

```

* Create a web service.
* It will take a few minutes for the server to start properly.

```
az appservice plan create -g ${AZ_GROUP} -n ${AZ_PLAN} -l ${AZ_LOC} --sku B1 --is-linux
az webapp create -g ${AZ_GROUP} -p ${AZ_PLAN} -n ${AZ_APP} --multicontainer-config-type compose --multicontainer-config-file tmp/docker-compose.site.yml
az webapp config container set -g ${AZ_GROUP} -n ${AZ_APP} -r ${ACR_REPO} -u ${ACR_USER} -p ${ACR_PASSWORD}
```

* Test 

```
curl -v -X POST -d '{"message": "hello"}' https://${AZ_APP}.azurewebsites.net/message | jsonpp
curl -v https://${AZ_APP}.azurewebsites.net/message/840ae020
curl -v -X DELETE https://${AZ_APP}.azurewebsites.net/message/840ae020
```

* Use client tool.

```
RCLIP_API=https://${AZ_APP}.azurewebsites.net
cd client
rclip -h
echo hello | rclip s
rclip s -t hello > ../tmp/key
rclip r `cat ../tmp/key`
rclip d `cat ../tmp/key`
rclip r `cat ../tmp/key`
```

* Stop and restart web service.

```
az webapp stop -g ${AZ_GROUP} -n ${AZ_APP}
az webapp start -g ${AZ_GROUP} -n ${AZ_APP}
```

* Delete all resources.

```
az webapp stop -g ${AZ_GROUP} -n ${AZ_APP}
az webapp delete -g ${AZ_GROUP} -n ${AZ_APP}
az acr delete -g ${AZ_GROUP} -n ${AZ_ACR}
az group delete -g ${AZ_GROUP}
```
