# Kubernetes (kustomize) — demonstrative deployment

A **demonstrative** deployment target for TinyInsta: the same topology as
`docker-compose.yml` expressed as Kubernetes objects. It shows the polyglot
system running on a cluster — it is **not** a hardened production setup.

> Datastores run as **single-replica Deployments with `emptyDir`** (ephemeral).
> For anything real, swap them for StatefulSets + PVCs, or managed
> services/operators (Postgres, Mongo, Neo4j, Redpanda, Elasticsearch, MinIO).

## Layout

| File | Contents |
|---|---|
| `namespace.yaml` | the `tinyinsta` namespace |
| `config.yaml` | shared `ConfigMap` + example `Secret` (replace the secret!) |
| `datastores.yaml` | postgres, redis, redpanda, mongo, neo4j, minio, elasticsearch, keycloak |
| `apps.yaml` | the 9 HTTP services (Deployment + Service on `:8000`) |
| `workers.yaml` | the bus consumers (`manage.py consume`) + media-worker |
| `ingress.yaml` | the CDN + a single ingress-nginx Ingress for `/api/*`, `/ws`, `/cdn` |
| `kustomization.yaml` | ties it together; generates ConfigMaps from the compose configs |

## Prerequisites

- A cluster (e.g. `kind` or `minikube`) and `kubectl`.
- The **ingress-nginx** controller installed (the Ingress uses its regex rewrite).
- The service images available to the cluster. They are the locally-built
  compose images (`tinyinsta/<svc>`), referenced with `imagePullPolicy:
  IfNotPresent`.

## Deploy

```bash
# 1. Build the images (compose), then load them into the local cluster.
make build
for img in user-svc post-svc usertimeline-svc hometimeline-svc interaction-svc \
           stories-svc media-svc search-svc realtime-svc media-worker; do
  kind load docker-image "tinyinsta/$img:latest"      # minikube: `minikube image load`
done

# 2. Apply everything.
kubectl apply -k infra/k8s

# 3. Watch it come up.
kubectl -n tinyinsta get pods
```

To publish/pull from a registry instead of loading locally, point the images at
your registry:

```bash
cd infra/k8s
kustomize edit set image tinyinsta/user-svc=ghcr.io/<owner>/tinyinsta-user-svc:latest
# …repeat per service (CI pushes these tags — see .github/workflows/ci.yml)
```

## Verify

```bash
kubectl -n tinyinsta get pods            # all Running/Ready
kubectl -n tinyinsta port-forward svc/user-svc 8000:8000 &
curl localhost:8000/health               # {"status":"ok","service":"user-svc"}
```

Then reach the app through the ingress controller's address at `/api/...`,
`/ws` and `/cdn/...`.
