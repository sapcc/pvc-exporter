import os
import re
import time
import socket

from kubernetes import client, config
from prometheus_client import start_http_server, Gauge

pvc_usage_metric = Gauge(
    'pvc_usage', 'fetching usge matched by k8s csi',
    ['persistentvolumeclaim', 'volumename', 'mountedby', 'nfsversion']
)

POOL = {}
METRIC_TIMEOUT = 60 * 5

start_http_server(8848)
config.load_incluster_config()
k8s = client.CoreV1Api()
HOST_NAME = socket.gethostname()
IP_ADDR = socket.gethostbyname(HOST_NAME)


def get_items(obj):
    format = obj.to_dict()
    items = format['items']
    return items


def get_pods_by_field_selector(field_selector):
    return get_items(k8s.list_pod_for_all_namespaces(
        watch=False, field_selector=field_selector))


def get_nfs_version():
    result = {}
    cmd = "mount -v | grep -E 'kubernetes.io~nfs'"
    with os.popen(cmd) as get_pvc:
        pvcs = get_pvc.readlines()
        for pvc in pvcs:
            pvc_l = pvc.split(' ')
            volume = pvc_l[2].split('/')[-1].strip()
            for v in pvc_l[2].split('/'):
                if re.match("^pvc", v):
                    volume = v
            for vers in pvc_l:
                if 'vers' in vers:
                    vers = vers.split(',')[2]
                    nfs_v = vers.split('=')[-1]
                    result[volume] = nfs_v
    return result


def get_pvc_usage():
    result = {}
    cmd = "df -h|grep -E 'kubernetes.io~nfs'"
    with os.popen(cmd) as get_pvc:
        pvcs = get_pvc.readlines()
        for pvc in pvcs:
            pvc_l = pvc.split(' ')
            volume = pvc_l[-1].split('/')[-1].strip()
            for v in pvc_l[-1].split('/'):
                if re.match("^pvc", v):
                    volume = v
            for usage in pvc_l:
                if re.match("^[0-9]*\%", usage):
                    usage = float(usage.strip('%')) / 100.0
                    result[volume] = usage
    return result


def get_pvc_mapping():
    # Get pod by host name
    pods = get_pods_by_field_selector(f"metadata.name={HOST_NAME}")
    if not pods:
        # Get pod by ip address
        pods = get_pods_by_field_selector(f"status.podIP={IP_ADDR}")
    # If there is no pods just return None
    if not pods:
        return
    # Get all PVCs
    pvcs = get_items(
        k8s.list_persistent_volume_claim_for_all_namespaces(
            watch=False))
    node_name = pods[0]['spec']['node_name']
    # Get all pods on current node
    pods = get_pods_by_field_selector(f"spec.nodeName={node_name}")
    # Get pvc usage on current node
    pvc_usage_percent = get_pvc_usage()
    # Get nfs versions of each pvc
    pvc_nfs_version = get_nfs_version()
    for p in pods:
        if p['spec'].get('volumes'):
            for vc in p['spec']['volumes']:
                if vc.get('persistent_volume_claim'):
                    pvc = vc['persistent_volume_claim']['claim_name']
                    for v in pvcs:
                        if v['metadata']['name'] == pvc:
                            vol = v['spec']['volume_name']
                    pod = p['metadata']['name']
                    if pvc in POOL.keys():
                        pvc_usage_metric.remove(
                            pvc, POOL[pvc][0], POOL[pvc][1], POOL[pvc][2]
                        )
                    if pvc_nfs_version.get(vol) and pvc_usage_percent.get(vol):
                        pvc_usage_metric.labels(
                            pvc, vol, pod, pvc_nfs_version[vol]
                        ).set(pvc_usage_percent[vol])
                        POOL[pvc] = [vol, pod, pvc_nfs_version[vol]]


def main():
    while True:
        get_pvc_mapping()
        time.sleep(METRIC_TIMEOUT)


if __name__ == "__main__":
    main()
