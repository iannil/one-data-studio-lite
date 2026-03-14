# Kubernetes Deployment Guide

Complete guide for deploying the Smart Data Platform on Kubernetes.

## Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3.x
- StorageClass configured (for PVCs)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Ingress (Traefik)                         │
└─────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
│   Frontend     │      │    Backend      │      │   Services      │
│   (Next.js)    │      │    (FastAPI)    │      │                 │
│                │      │                 │      │ • MLflow        │
│ Deployment: 3  │      │ Deployment: 3   │      │ • Jupyter Hub   │
│ HPA: CPU 70%   │      │ HPA: CPU 80%    │      │ • Label Studio  │
└────────────────┘      └─────────────────┘      │ • KServe        │
                                                 └─────────────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
│   PostgreSQL   │      │     Redis       │      │     MinIO       │
│  (StatefulSet) │      │   (Cluster)     │      │  (StatefulSet)  │
│    Replicas:3  │      │    Replicas:3   │      │    Replicas:1   │
└────────────────┘      └─────────────────┘      └─────────────────┘
```

## Quick Start

### 1. Add Helm Repository

```bash
helm repo add one-data-studio https://charts.one-data-studio.io
helm repo update
```

### 2. Create Namespace

```bash
kubectl create namespace one-data-studio
```

### 3. Install

```bash
helm install one-data-studio one-data-studio/one-data-studio \
  --namespace one-data-studio \
  --set frontend.ingress.enabled=true \
  --set frontend.ingress.host=platform.example.com \
  --set backend.secretKey=$(openssl rand -hex 32)
```

## Configuration

### Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.replicaCount` | Frontend replicas | `3` |
| `frontend.image.repository` | Frontend image | `one-data-studio/frontend` |
| `frontend.image.tag` | Frontend tag | `latest` |
| `backend.replicaCount` | Backend replicas | `3` |
| `backend.image.repository` | Backend image | `one-data-studio/backend` |
| `backend.image.tag` | Backend tag | `latest` |
| `backend.secretKey` | JWT secret | *required* |
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.replicaCount` | PostgreSQL replicas | `3` |
| `redis.enabled` | Enable Redis | `true` |
| `redis.cluster.enabled` | Enable Redis Cluster | `false` |
| `minio.enabled` | Enable MinIO | `true` |
| `mlflow.enabled` | Enable MLflow | `true` |
| `jupyter.enabled` | Enable Jupyter Hub | `true` |
| `labelStudio.enabled` | Enable Label Studio | `true` |

### Production Values

Create `production-values.yaml`:

```yaml
# Production configuration
frontend:
  replicaCount: 3
  image:
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

backend:
  replicaCount: 3
  image:
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 1000m
      memory: 2Gi
    limits:
      cpu: 4000m
      memory: 8Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 80

postgresql:
  replicaCount: 3
  resources:
    requests:
      cpu: 2000m
      memory: 4Gi
    limits:
      cpu: 8000m
      memory: 16Gi
  persistence:
    size: 500Gi

redis:
  cluster:
    enabled: true
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

minio:
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi
  persistence:
    size: 1Ti

# Enable ML services
mlflow:
  enabled: true

jupyter:
  enabled: true

labelStudio:
  enabled: true

# Monitoring
monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
```

Install with production values:

```bash
helm install one-data-studio one-data-studio/one-data-studio \
  --namespace one-data-studio \
  --values production-values.yaml \
  --set backend.secretKey=$(openssl rand -hex 32)
```

## Storage Configuration

### Storage Classes

Define storage classes for different workloads:

```yaml
# fast-ssd-storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
allowVolumeExpansion: true
---
# standard-storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
allowVolumeExpansion: true
```

Apply storage classes:

```bash
kubectl apply -f fast-ssd-storageclass.yaml
kubectl apply -f standard-storageclass.yaml
```

## Ingress Configuration

### Traefik Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: one-data-studio-ingress
  namespace: one-data-studio
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - platform.example.com
    secretName: one-data-studio-tls
  rules:
  - host: platform.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

## Monitoring Setup

### Prometheus ServiceMonitors

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: backend-monitor
  namespace: one-data-studio
spec:
  selector:
    matchLabels:
      app: backend
  endpoints:
  - port: metrics
    interval: 30s
```

### Grafana Dashboards

Import pre-configured dashboards:

```bash
kubectl create configmap grafana-dashboards \
  --namespace one-data-studio \
  --from-file=./dashboards/
```

## Backup Strategy

### PostgreSQL Backup

```yaml
# CronJob for daily backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: one-data-studio
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: prodrigestivill/postgres-backup-local:15
            env:
            - name: POSTGRES_HOST
              value: postgresql
            - name: POSTGRES_DB
              value: onedatastudio
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgresql
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgresql
                  key: password
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Scaling Operations

### Horizontal Pod Autoscaler

```bash
# Check HPA status
kubectl get hpa -n one-data-studio

# Manual scaling
kubectl scale deployment backend --replicas=10 -n one-data-studio
```

### Vertical Pod Autoscaler

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: backend-vpa
  namespace: one-data-studio
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  updatePolicy:
    updateMode: Auto
  resourcePolicy:
    containerPolicies:
    - containerName: backend
      minAllowed:
        cpu: 500m
        memory: 1Gi
      maxAllowed:
        cpu: 8000m
        memory: 16Gi
```

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending state**
   ```bash
   kubectl describe pod <pod-name> -n one-data-studio
   # Check for resource constraints or PVC issues
   ```

2. **High memory usage**
   ```bash
   kubectl top pods -n one-data-studio
   # Identify resource-hungry pods
   ```

3. **Database connection issues**
   ```bash
   kubectl exec -it postgresql-0 -n one-data-studio -- psql -U onedatastudio
   # Check database logs
   ```

### Logs Collection

```bash
# Collect all logs
kubectl logs -l app=backend -n one-data-studio --all-containers=true > backend-logs.txt

# Stream logs in real-time
kubectl logs -f deployment/backend -n one-data-studio
```

## Upgrades

### Helm Upgrade

```bash
helm repo update
helm upgrade one-data-studio one-data-studio/one-data-studio \
  --namespace one-data-studio \
  --values production-values.yaml \
  --reuse-values
```

### Rollback

```bash
# Check revision history
helm history one-data-studio -n one-data-studio

# Rollback to previous version
helm rollback one-data-studio -n one-data-studio
```
