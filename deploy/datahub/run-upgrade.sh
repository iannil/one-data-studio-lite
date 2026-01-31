#!/bin/bash
docker run --rm --network ods-network \
  -e EBEAN_DATASOURCE_HOST=datahub-mysql:3306 \
  -e EBEAN_DATASOURCE_URL='jdbc:mysql://datahub-mysql:3306/datahub?allowPublicKeyRetrieval=true&useSSL=false' \
  -e EBEAN_DATASOURCE_USERNAME=root \
  -e EBEAN_DATASOURCE_PASSWORD=datahub2024 \
  -e EBEAN_DATASOURCE_DRIVER=com.mysql.jdbc.Driver \
  -e ELASTICSEARCH_HOST=datahub-elasticsearch \
  -e ELASTICSEARCH_PORT=9200 \
  -e KAFKA_BOOTSTRAP_SERVER=datahub-kafka:9092 \
  -e KAFKA_SCHEMAREGISTRY_URL='http://datahub-schema-registry:8081' \
  -e GRAPH_SERVICE_IMPL=elasticsearch \
  -e DATAHUB_GMS_HOST=datahub-gms \
  -e DATAHUB_GMS_PORT=8080 \
  -e ENTITY_REGISTRY_CONFIG_PATH=/datahub/datahub-gms/resources/entity-registry.yml \
  acryldata/datahub-upgrade:v0.13.2 -u SystemUpdate
