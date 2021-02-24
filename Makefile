IMAGE_BASE             ?= keppel.eu-de-1.cloud.sap/ccloud
IMAGE_PVC_BLOCK_SCANER ?= $(IMAGE_BASE)/block-pvc-scanner
VERSION = $(shell git rev-parse --verify HEAD | head -c 8)


build-pvc-scanner:
	docker build -t $(IMAGE_PVC_BLOCK_SCANER):$(VERSION) block-pvc-scanner/

push: build-pvc-scanner
	docker push $(IMAGE_PVC_BLOCK_SCANER):$(VERSION)
