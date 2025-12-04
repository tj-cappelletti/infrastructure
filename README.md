# Infrastructure Monorepo

A centralized monorepo for managing application deployments across DNS, HAProxy, and Kubernetes infrastructure in a homelab environment.

## Overview

This repository serves as a single source of truth for application deployments, orchestrating:
- **DNS Configuration**: Bind9 DNS records via Ansible
- **HAProxy Configuration**: Load balancer rules via Ansible
- **Kubernetes Deployments**: K3s cluster resources via kubectl/kustomize

## Repository Structure

```
infrastructure/
├── applications/                    # Application definitions (single source of truth)
│   └── kubernetes-bootcamp.yml      # Example application configuration
├── ansible/
│   ├── inventory/
│   │   └── hosts.yml               # Ansible inventory for infrastructure hosts
│   ├── playbooks/
│   │   ├── deploy-dns.yml          # DNS deployment playbook
│   │   └── deploy-haproxy.yml      # HAProxy deployment playbook
│   └── roles/
│       ├── bind9/                  # Bind9 DNS role
│       │   ├── handlers/main.yml
│       │   ├── tasks/main.yml
│       │   └── templates/zone-entry.j2
│       └── haproxy/                # HAProxy role
│           ├── handlers/main.yml
│           ├── tasks/main.yml
│           └── templates/backend.cfg.j2
├── kubernetes/
│   └── apps/                       # Kubernetes manifests per application
│       └── kubernetes-bootcamp/
│           ├── deployment.yaml
│           ├── ingress.yaml
│           ├── kustomization.yaml
│           ├── namespace.yaml
│           └── service.yaml
├── scripts/
│   ├── generate-haproxy-config.py  # HAProxy config generator
│   ├── smoke-test.py               # Deployment smoke tests
│   └── validate-app-config.py      # Configuration validator
└── .github/
    └── workflows/
        └── deploy-app.yml          # CI/CD pipeline
```

## Adding a New Application

1. **Create the application definition** in `applications/<app-name>.yml`:

```yaml
metadata:
  name: my-application
  environment: production
  owner: team-name

dns:
  provider: bind9
  zone: webstorm.cloud
  server: 172.16.0.11
  records:
    - type: A
      name: myapp
      value: 172.16.0.60
      ttl: 300

haproxy:
  host: 172.16.0.60
  frontend:
    name: my-application-frontend
    bind_port: 80
    mode: http
    acl:
      name: host_myapp
      match: "hdr(host) -i myapp.webstorm.cloud"
  backend:
    name: my-application-backend
    mode: http
    balance: roundrobin
    servers:
      - name: k3s-worker-1
        address: 172.16.0.21
        port: 80
        options: check
      - name: k3s-worker-2
        address: 172.16.0.22
        port: 80
        options: check

kubernetes:
  namespace: my-application
  deployment:
    name: my-application
    replicas: 3
    image: my-registry/my-application:v1
    resources:
      requests:
        memory: 128Mi
        cpu: 100m
      limits:
        memory: 256Mi
        cpu: 200m
  service:
    name: my-application
    type: ClusterIP
    port: 8080
  ingress:
    name: my-application-ingress
    className: traefik
    host: myapp.webstorm.cloud
    path: /
```

2. **Create Kubernetes manifests** in `kubernetes/apps/<app-name>/`:
   - `namespace.yaml`
   - `deployment.yaml`
   - `service.yaml`
   - `ingress.yaml`
   - `kustomization.yaml`

3. **Commit and push** to trigger the deployment pipeline.

## Triggering Deployments

### Automatic Deployment

Deployments are automatically triggered when:
- Changes are pushed to `main` branch affecting:
  - `applications/**`
  - `kubernetes/apps/**`

### Manual Deployment

1. Go to **Actions** → **Deploy Application**
2. Click **Run workflow**
3. Select the application to deploy
4. Optionally enable **dry run** mode

## Workflow Stages

The deployment pipeline consists of the following stages:

| Stage | Description |
|-------|-------------|
| **detect-changes** | Identifies which applications have changed |
| **validate** | Validates app config, K8s manifests, and HAProxy config |
| **deploy-dns** | Deploys DNS records to Bind9 server |
| **deploy-haproxy** | Deploys HAProxy configuration and reloads service |
| **deploy-kubernetes** | Applies K8s manifests and waits for rollout |
| **notify** | Runs smoke tests and reports deployment status |

## Configuration Validation

Validate your application configuration before committing:

```bash
# Validate application YAML schema
python scripts/validate-app-config.py applications/kubernetes-bootcamp.yml

# Generate and preview HAProxy configuration
python scripts/generate-haproxy-config.py applications/kubernetes-bootcamp.yml

# Run smoke tests against deployed application
python scripts/smoke-test.py applications/kubernetes-bootcamp.yml
```

## Kubernetes Manifest Validation

```bash
# Dry-run Kubernetes manifests
kubectl apply --dry-run=client -k kubernetes/apps/kubernetes-bootcamp/

# View rendered manifests
kubectl kustomize kubernetes/apps/kubernetes-bootcamp/
```

## Ansible Playbook Validation

```bash
# Syntax check
ansible-playbook --syntax-check ansible/playbooks/deploy-dns.yml
ansible-playbook --syntax-check ansible/playbooks/deploy-haproxy.yml

# Dry-run (check mode)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deploy-dns.yml --check
```

## Troubleshooting

### DNS Issues

1. Verify DNS record in zone file:
   ```bash
   ssh ansible@172.16.0.11 "cat /var/lib/bind/db.webstorm.cloud"
   ```

2. Test DNS resolution:
   ```bash
   nslookup bootcamp.webstorm.cloud 172.16.0.11
   dig @172.16.0.11 bootcamp.webstorm.cloud
   ```

3. Check Bind9 status:
   ```bash
   ssh ansible@172.16.0.11 "sudo systemctl status named"
   ```

### HAProxy Issues

1. Check HAProxy configuration:
   ```bash
   ssh ansible@172.16.0.60 "haproxy -c -f /etc/haproxy/haproxy.cfg"
   ```

2. View HAProxy stats:
   ```bash
   curl http://172.16.0.60:8404/stats
   ```

3. Check HAProxy logs:
   ```bash
   ssh ansible@172.16.0.60 "journalctl -u haproxy -f"
   ```

### Kubernetes Issues

1. Check pod status:
   ```bash
   kubectl get pods -n kubernetes-bootcamp
   kubectl describe pod -n kubernetes-bootcamp <pod-name>
   ```

2. Check deployment rollout:
   ```bash
   kubectl rollout status deployment/kubernetes-bootcamp -n kubernetes-bootcamp
   ```

3. View ingress configuration:
   ```bash
   kubectl get ingress -n kubernetes-bootcamp -o yaml
   ```

4. Check Traefik logs:
   ```bash
   kubectl logs -n kube-system -l app.kubernetes.io/name=traefik
   ```

## Infrastructure Components

| Component | IP Address | Description |
|-----------|------------|-------------|
| HAProxy VIP | 172.16.0.60 | Load balancer virtual IP |
| Bind9 DNS | 172.16.0.11 | Primary DNS server |
| K3s Worker 1 | 172.16.0.21 | Kubernetes worker node |
| K3s Worker 2 | 172.16.0.22 | Kubernetes worker node |

## Requirements

- Python 3.11+
- Ansible 2.14+
- kubectl with K3s cluster access
- SSH access to infrastructure hosts

## License

See [LICENSE](LICENSE) file for details.
