import os
import re
import time
import socket

from kubernetes import client, config
from prometheus_client import start_http_server, Gauge
from prometheus_client import start_http_server, Gauge

pvc_usage_metric = Gauge(
    'pvc_usage', 'fetching usge matched by k8s csi',
    ['persistentvolumeclaim', 'volumename', 'mountedby']
)

POOL = {}
METRIC_TIMEOUT = 60

start_http_server(8848)
config.load_incluster_config()
k8s_api_obj = client.CoreV1Api()


def get_items(obj):
    format = obj.to_dict()
    items = format['items']
    return items


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


def get_pvc_mapping(current_node_name):
    pods = get_items(k8s_api_obj.list_pod_for_all_namespaces(watch=False))
    pvcs = get_items(
        k8s_api_obj.list_persistent_volume_claim_for_all_namespaces(
            watch=False))
    # Check if there is a current pod node name exists.
    if not current_node_name:
        current_pod_name = socket.gethostname()
        for p in pods:
            if p['metadata']['name'] == current_pod_name:
                current_node_name = p['spec']['node_name']
    pvc_usage_percent = get_pvc_usage()
    for p in pods:
        # Filter out pods from other nodes
        if p['spec']['node_name'] == current_node_name:
            for vc in p['spec']['volumes']:
                if vc['persistent_volume_claim']:
                    pvc = vc['persistent_volume_claim']['claim_name']
                    for v in pvcs:
                        if v['metadata']['name'] == pvc:
                            vol = v['spec']['volume_name']
                    pod = p['metadata']['name']
                    if pvc in POOL.keys():
                        pvc_usage_metric.remove(
                            pvc, POOL[pvc][0], POOL[pvc][1]
                        )
                    pvc_usage_metric.labels(pvc, vol, pod).set(
                        pvc_usage_percent[vol]
                    )
                    POOL[pvc] = [vol, pod]


def main():
    current_node_name = None
    while True:
        get_pvc_mapping(current_node_name)
        time.sleep(METRIC_TIMEOUT)


if __name__ == "__main__":
    main()
