# Run and test on local k8s (port=30120)

```
# run
kubectl apply -f app.site.yml

# test
sh -c 'RCLIP_API=http://localhost:30120; KEY=$(rclip s -t hello); rclip r ${KEY}'

# clean up
kubectl delete -f app.site.yml
```

# Run and test on Azure Kubernetes Service (AKS)

Notice: https is not supported yet.

```
export AZ_CLUSTER=${APP_NAME}c

# create cluster
az aks create -g ${AZ_GROUP} -l ${AZ_LOC} -n ${AZ_CLUSTER} -c 2
az aks get-credentials -g ${AZ_GROUP} -n ${AZ_CLUSTER}

# change kubectl context
kubectl config get-contexts
kubectl get nodes

# build
kubectl apply -f app-lb.site.yml

# test
sh -c 'RCLIP_API=http://<EXTERNAL IP>; KEY=$(rclip s -t hello); rclip r ${KEY}'

# clean up
kubectl delete -f app-lb.site.yml
kubectl config delete-context ${AZ_CLUSTER}
az aks delete -g ${AZ_GROUP} -l ${AZ_LOC} -n ${AZ_CLUSTER}
```
