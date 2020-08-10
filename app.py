import os
import re
import json
import time
import logging
import threading
import itertools
import requests
from requests.auth import HTTPBasicAuth
from flask import Flask, render_template, jsonify

app = Flask(__name__)

ETCD_ENDPOINT = os.getenv("ETCD_ENDPOINT", "http://localhost:2379")
ETCD_USERNAME = os.getenv("ETCD_USERNAME", "")
ETCD_PASSWORD = os.getenv("ETCD_PASSWORD", "")
NODE_API = f"{ETCD_ENDPOINT}/v2/keys/coreos.com/network/nodes"
SUBNET_API = f"{ETCD_ENDPOINT}/v2/keys/coreos.com/network/subnets"
# RAW_NODES = []
ROUTER_EDGE_WIDTH = 1
ROUTER_BACKGROUND = "#1982C4"
ROUTER_BORDER = "#8AC926"
ROUTER_SIZE = 20

LOOP = int(os.getenv("LOOP", "60"))  # Main thread loop seconds


def logger(name='sidecar'):
    log = logging.getLogger(name)
    log_format = '[%(asctime)s] %(levelname)s [%(threadName)s]: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(format=log_format, datefmt=date_format)
    log.setLevel(logging.DEBUG)
    return log


LOG = logger()


def extract_ip(text="") -> str:
    regex = r"(((25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?))"
    m = re.search(regex, text)
    return m.group(0)


def dedup(it):
    """
    :param it: iterable [(1,3), (1,4), (3,1),(3,4),(4,3)]
    :return: [(1,3),(1,4),(3,4)]
    """
    sep = ","
    foo = []
    for item in it:
        li = list(item)
        li.sort()
        s = sep.join(str(x) for x in li)
        foo.append(s)

    bar = []
    for item in set(foo):
        bar.append([int(x) for x in item.split(sep)])
    return bar


def get_routers(raw_nodes) -> list:
    return [node for node in raw_nodes if node["node_type"] == "router"]


def parse_etcd_payload(payload) -> list:
    """
    parse etcd API response, and return list like this:
    [
        {'key': '/coreos.com/network/nodes/ted.com/10.14.128.0', 'value': '{"node_type": "node"}', 'modifiedIndex': 149, 'createdIndex': 149},
        {'key': '/coreos.com/network/nodes/ted.com/10.13.112.0', 'value': '{"node_type": "router"}', 'modifiedIndex': 102, 'createdIndex': 102}
    ]
    """
    data = json.loads(payload)
    keys = []
    nodes = data["node"].get("nodes", [])

    if not nodes:
        # If "nodes" list is not in "/coreos.com/network/subnets" or "/coreos.com/network/nodes",
        # return directly.
        return keys

    for node in nodes:
        try:
            keys.extend(node["nodes"])
        except KeyError:
            LOG.error(f"KeyError while processing {node}")
    return keys


def extract_node_info(route):
    org, ip = route["key"].split("/")[-2:]
    value = json.loads(route["value"])
    node_type = value["node_type"]
    meta = value["meta"]
    return org, ip, node_type, meta


def load_nodes():
    raw_nodes = []
    response = requests.get(NODE_API, auth=(ETCD_USERNAME, ETCD_PASSWORD), params={"recursive": "true"})
    if response.status_code == 200:
        idx = 1
        grp = 0
        current_org = ""

        for node in parse_etcd_payload(response.text):
            org, ip, node_type, meta = extract_node_info(node)
            if org != current_org:
                current_org = org
                grp += 1
            raw_nodes.append({
                "id": idx,
                "ip": ip,
                "org": org,
                "group": grp,
                "node_type": node_type,
                "meta": meta,
            })
            idx += 1
    else:
        print("Error loading nodes")
        print(response.text)
    return raw_nodes


def generate_nodes(raw_nodes):
    nodes = []
    for raw in raw_nodes:
        host_ip = raw["meta"]["host_ip"]
        hostname = raw["meta"]["hostname"]
        node = {
            "id": raw["id"],
            "label": f"{hostname}",
            "group": raw["group"],
            "title": f"<h4>Hostname: {hostname}</h4><h4>Host IP: {host_ip}</h4><h4>Net: {raw['ip']}</h4>",
            # "title": raw["node_type"],
            # "title": f"<h3>{hostname}</h3><h4>{raw['ip']}</h4>",
        }

        if raw["node_type"] == "router":
            node["size"] = ROUTER_SIZE
            node["color"] = {
                "background": ROUTER_BACKGROUND,
                "border": ROUTER_BORDER,
            }
            node["label"] = f"{raw['org']}({raw['ip']})"
            node["shape"] = "square"
        elif raw["node_type"] == "internal":
            node["shapeProperties"] = {
                "borderDashes": [5, 5]
            }
        # else:
        #     node["shape"] = "square"

        nodes.append(node)
    return nodes


def generate_edges(raw_nodes):
    edges = []
    routers = get_routers(raw_nodes)
    for rt in routers:
        org = rt["org"]
        router_id = rt["id"]
        for node in raw_nodes:
            if node["node_type"] == "router":
                continue
            if node["org"] == org:
                edges.append({
                    "from": node["id"],
                    "to": router_id
                })
    # Connect routers
    tmp = dedup(itertools.permutations([r["id"] for r in routers], 2))
    for t in tmp:
        edges.append({
            "from": t[0],
            "to": t[1],
            "value": ROUTER_EDGE_WIDTH,
            "scaling": {
                "min": 1,
                "max": 6,
            }
        })
    return edges


def generate_info(raw_nodes):
    total_nodes = len(raw_nodes)
    router = 0
    node = 0
    internal = 0
    for raw in raw_nodes:
        if raw["node_type"] == "router":
            router += 1
        elif raw["node_type"] == "node":
            node += 1
        else:
            internal += 1

    return {
        "total": total_nodes,
        "router": router,
        "node": node,
        "internal": internal
    }


def sync_nodes_subnets():
    LOG.info("Synchronize nodes and subnets")
    all_nodes = {}
    subnets_set = set()
    response = requests.get(SUBNET_API, auth=(ETCD_USERNAME, ETCD_PASSWORD), params={"recursive": "true"})
    if response.status_code == 200:
        data = json.loads(response.text)
        try:
            keys = data["node"]["nodes"]
            # key["keys"] is like: /coreos.com/network/subnets/10.12.128.0-20
            subnets_set = set([extract_ip(key["key"]) for key in keys])

        except KeyError as err:
            LOG.error("Key error while processing subnets")
            LOG.debug(err)
            LOG.debug(data)
            return
    else:
        LOG.error("Error while loading subnets")
        LOG.debug(response.text)

    response = requests.get(NODE_API, auth=(ETCD_USERNAME, ETCD_PASSWORD), params={"recursive": "true"})
    if response.status_code == 200:
        data = json.loads(response.text)
        orgs = data["node"].get("nodes", [])
        if not orgs:
            # If NODE_API contains no "nodes", return directly
            return
        for org in orgs:
            try:
                keys = org["nodes"]
                for key in keys:
                    net = extract_ip(key["key"])
                    all_nodes[net] = key["key"]
            except KeyError:
                LOG.error(f"Key error while processing {org}")
    else:
        LOG.error("Error while loading nodes")
        LOG.debug(response.text)
        return

    nodes_set = set(all_nodes.keys())
    orphan_nodes = nodes_set - subnets_set
    for orphan in orphan_nodes:
        node = all_nodes[orphan]
        LOG.info(f"Found orphan node: {node}")
        url = f"{ETCD_ENDPOINT}/v2/keys/{node}"

        response = requests.delete(url, auth=(ETCD_USERNAME, ETCD_PASSWORD))

        if response.status_code == 200:
            LOG.info(f"Orphan node {node} deleted")
        else:
            LOG.critical(f"Error while deleting orphan node: {node}")
            LOG.critical(response)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/topo')
def generate_topology():
    raw = load_nodes()
    generate_info(raw)
    topo = {
        "nodes": generate_nodes(raw),
        "edges": generate_edges(raw),
        "info": generate_info(raw),
    }
    return topo


if __name__ == "__main__":
    # flask_thread = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0"})
    # flask_thread.start()
    # while True:
    #     sync_nodes_subnets()
    #     time.sleep(LOOP)
    app.run(host="0.0.0.0", debug=True)
