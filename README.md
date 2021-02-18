# pvc-exporter

This item provides metric for monitoring mounted pvc usage precent named `pvc_usage`.

# Note

Only used to monitor mounted pvc that provied by block storage provisioner.

# Install

You can get the following files and run apply them.
kubectl apply -f rbac.yml -f daemonset.yml
