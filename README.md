# s1decar
Sidecar for Netswatch
Sidecar is a tool for rendering Netswach topology

## Prerequsites
* Python 3

## Quick Start
```
pip install -r requirements.txt
python app.py
```

## Environment Variables
Name | Description | Default
--- | --- | --- 
ETCD_ENDPOINT | Etcd endpoint | http://localhost:2379
ETCD_USERNAME | Etcd username | 
ETCD_PASSWORD | Etcd password | 
SIDECAR_PREFIX | Application prefix in URL | sidecar
NODE_LABEL_COLOR | Node label color in topology | #d8d9da

## Build Docker Image
```
make image
```
