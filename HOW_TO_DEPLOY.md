# 🚀 How to Deploy Nexus Agent

This guide provides comprehensive deployment instructions for the Nexus autonomous agent framework in various environments.

## 📋 Deployment Options

Choose your deployment method:
1. **Local Development** - For testing and development
2. **Production Server** - For dedicated server deployment
3. **Docker Container** - For containerized deployment
4. **Cloud Services** - For scalable cloud deployment
5. **Enterprise Setup** - For corporate environments

## 🏠 Local Development Deployment

### Quick Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd Nexus

# 2. Install dependencies
pip3 install --user pydantic pydantic-settings python-dotenv rich fastapi uvicorn aiohttp selenium webdriver-manager PyYAML cryptography validators structlog psutil json5 aiofiles

# 3. Configure environment
echo "LLM__PROVIDER=mock" > .env
echo "AGENT__NAME=nexus-dev" >> .env
echo "DEBUG_MODE=true" >> .env
echo "MANUS_WORKING_DIR=./data" >> .env

# 4. Create data directory
mkdir -p data
chmod 755 data

# 5. Test deployment
python3 run-nexus.py --test
```

### Local Configuration
Create `.env` file:
```bash
# Core Configuration
LLM__PROVIDER=mock
AGENT__NAME=nexus-local
DEBUG_MODE=true

# Paths
MANUS_WORKING_DIR=./data
LOG_DIR=./logs

# Security
SECURITY__ALLOWED_DOMAINS=localhost,127.0.0.1
SECURITY__BLOCKED_PORTS=22,23,25,53,135,139,445

# Performance
MAX_ITERATIONS=1000
TIMEOUT_SECONDS=300
```

### Directory Structure
```
Nexus/
├── manus/              # Core agent code
├── data/               # Working directory
├── logs/               # Log files
├── .env                # Environment config
├── run-nexus.py        # Main runner
├── requirements.txt    # Dependencies
└── docker-compose.yml  # Docker config
```

## 🖥️ Production Server Deployment

### System Requirements
- **OS**: Ubuntu 20.04+ / CentOS 8+ / macOS 10.15+
- **Python**: 3.10+
- **Memory**: 2GB+ RAM
- **Storage**: 10GB+ available space
- **Network**: Outbound HTTPS access

### Production Setup
```bash
# 1. Create system user
sudo useradd -m -s /bin/bash nexus
sudo usermod -aG sudo nexus

# 2. Set up application directory
sudo mkdir -p /opt/nexus
sudo chown nexus:nexus /opt/nexus
cd /opt/nexus

# 3. Clone and setup
sudo -u nexus git clone <repository-url> .
sudo -u nexus python3 -m pip install --user -r requirements.txt

# 4. Configure production environment
sudo -u nexus cat > .env << EOF
LLM__PROVIDER=mock
AGENT__NAME=nexus-prod
DEBUG_MODE=false
MANUS_WORKING_DIR=/opt/nexus/data
LOG_DIR=/var/log/nexus
SECURITY__ALLOWED_DOMAINS=your-domain.com
SECURITY__BLOCKED_PORTS=22,23,25,53,135,139,445
MAX_ITERATIONS=1000
TIMEOUT_SECONDS=300
EOF

# 5. Create directories
sudo mkdir -p /var/log/nexus /opt/nexus/data
sudo chown nexus:nexus /var/log/nexus /opt/nexus/data

# 6. Test deployment
sudo -u nexus python3 run-nexus.py --test
```

### Systemd Service
Create `/etc/systemd/system/nexus-agent.service`:
```ini
[Unit]
Description=Nexus Autonomous Agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=nexus
Group=nexus
WorkingDirectory=/opt/nexus
Environment=PATH=/home/nexus/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 run-nexus.py --web
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/nexus/data /var/log/nexus

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nexus-agent
sudo systemctl start nexus-agent
sudo systemctl status nexus-agent
```

### Nginx Reverse Proxy
Create `/etc/nginx/sites-available/nexus`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🐳 Docker Deployment

### Single Container
```bash
# Build image
docker build -t nexus-agent .

# Run container
docker run -d \
  --name nexus-agent \
  --restart unless-stopped \
  -p 8080:8080 \
  -e LLM__PROVIDER=mock \
  -e AGENT__NAME=nexus-docker \
  -v nexus-data:/app/data \
  -v nexus-logs:/app/logs \
  nexus-agent

# Check status
docker logs nexus-agent
```

### Docker Compose Deployment
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  nexus-agent:
    build: .
    container_name: nexus-agent
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - LLM__PROVIDER=mock
      - AGENT__NAME=nexus-docker
      - DEBUG_MODE=false
      - SECURITY__ALLOWED_DOMAINS=your-domain.com
    volumes:
      - nexus-data:/app/data
      - nexus-logs:/app/logs
      - ./config:/app/config:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'

  nginx:
    image: nginx:alpine
    container_name: nexus-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - nexus-agent

volumes:
  nexus-data:
  nexus-logs:
```

Deploy:
```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

### Docker Swarm Deployment
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml nexus-stack

# Check services
docker service ls
docker service logs nexus-stack_nexus-agent
```

## ☁️ Cloud Services Deployment

### AWS EC2 Deployment
```bash
# 1. Launch EC2 instance (t3.medium recommended)
# 2. Connect via SSH
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Update system
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git docker.io docker-compose

# 4. Clone and setup
git clone <repository-url> nexus
cd nexus
sudo docker-compose up -d

# 5. Configure security group
# - Allow port 80 (HTTP)
# - Allow port 443 (HTTPS)
# - Restrict port 22 (SSH) to your IP
```

### Google Cloud Run Deployment
Create `cloudbuild.yaml`:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/nexus-agent', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/nexus-agent']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'nexus-agent'
      - '--image'
      - 'gcr.io/$PROJECT_ID/nexus-agent'
      - '--platform'
      - 'managed'
      - '--region'
      - 'us-central1'
      - '--allow-unauthenticated'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '1'
      - '--set-env-vars'
      - 'LLM__PROVIDER=mock,AGENT__NAME=nexus-cloud'
```

Deploy:
```bash
gcloud builds submit --config cloudbuild.yaml
```

### Azure Container Instances
```bash
# Create resource group
az group create --name nexus-rg --location eastus

# Deploy container
az container create \
  --resource-group nexus-rg \
  --name nexus-agent \
  --image your-registry/nexus-agent:latest \
  --cpu 1 \
  --memory 2 \
  --ports 8080 \
  --environment-variables \
    LLM__PROVIDER=mock \
    AGENT__NAME=nexus-azure \
  --restart-policy Always
```

## 🏢 Enterprise Deployment

### Kubernetes Deployment
Create `k8s-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus-agent
  labels:
    app: nexus-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nexus-agent
  template:
    metadata:
      labels:
        app: nexus-agent
    spec:
      containers:
      - name: nexus-agent
        image: nexus-agent:latest
        ports:
        - containerPort: 8080
        env:
        - name: LLM__PROVIDER
          value: "mock"
        - name: AGENT__NAME
          value: "nexus-k8s"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nexus-service
spec:
  selector:
    app: nexus-agent
  ports:
    - port: 80
      targetPort: 8080
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -l app=nexus-agent
kubectl get services nexus-service
```

### Helm Chart Deployment
Create `helm/nexus/values.yaml`:
```yaml
replicaCount: 3

image:
  repository: nexus-agent
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80
  targetPort: 8080

ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: nexus.your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nexus-tls
      hosts:
        - nexus.your-domain.com

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

config:
  llmProvider: mock
  agentName: nexus-enterprise
  debugMode: false
```

Deploy:
```bash
helm install nexus ./helm/nexus
helm upgrade nexus ./helm/nexus
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Core Settings
LLM__PROVIDER=mock                    # Provider type
AGENT__NAME=nexus-prod               # Agent identifier
DEBUG_MODE=false                     # Debug logging

# Paths
MANUS_WORKING_DIR=/app/data          # Working directory
LOG_DIR=/app/logs                    # Log directory

# Security
SECURITY__ALLOWED_DOMAINS=your-domain.com
SECURITY__BLOCKED_PORTS=22,23,25,53,135,139,445
SECURITY__MAX_FILE_SIZE_MB=100

# Performance
MAX_ITERATIONS=1000                  # Max agent iterations
TIMEOUT_SECONDS=300                  # Operation timeout
MAX_CONCURRENT_REQUESTS=10           # Concurrent limit

# Monitoring
ENABLE_METRICS=true                  # Enable metrics
METRICS_PORT=9090                   # Metrics endpoint
HEALTH_CHECK_INTERVAL=30            # Health check interval
```

### Configuration File
Create `config/production.yaml`:
```yaml
llm:
  provider: mock
  model: gpt-3.5-turbo
  temperature: 0.7
  max_tokens: 1000

agent:
  name: nexus-production
  max_iterations: 1000
  timeout_seconds: 300

security:
  allowed_domains:
    - your-domain.com
    - localhost
  blocked_ports:
    - 22
    - 23
    - 25
  max_file_size_mb: 100

logging:
  level: INFO
  format: json
  file: /var/log/nexus/agent.log

monitoring:
  enabled: true
  metrics_port: 9090
  health_check_interval: 30
```

## 📊 Monitoring & Observability

### Health Checks
```bash
# HTTP health check
curl -f http://localhost:8080/health

# Service status
systemctl status nexus-agent

# Container health
docker inspect --format='{{.State.Health.Status}}' nexus-agent

# Kubernetes health
kubectl get pods -l app=nexus-agent
```

### Logging
```bash
# System logs
sudo journalctl -u nexus-agent -f

# Container logs
docker logs -f nexus-agent

# File logs
tail -f /var/log/nexus/agent.log
```

### Metrics
```bash
# Prometheus metrics
curl http://localhost:9090/metrics

# Custom metrics endpoint
curl http://localhost:8080/metrics
```

## 🔒 Security Considerations

### Production Security Checklist
- [ ] Use HTTPS/TLS encryption
- [ ] Configure firewall rules
- [ ] Enable security monitoring
- [ ] Regular security updates
- [ ] Secure API endpoints
- [ ] Input validation enabled
- [ ] Rate limiting configured
- [ ] Access logs enabled

### SSL/TLS Setup
```bash
# Generate SSL certificate
sudo certbot --nginx -d your-domain.com

# Or use Let's Encrypt
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx
```

## 🚨 Backup & Recovery

### Backup Strategy
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/nexus_$DATE"

mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_DIR/data.tar.gz /opt/nexus/data

# Backup config
cp /opt/nexus/.env $BACKUP_DIR/
cp -r /opt/nexus/config $BACKUP_DIR/

# Backup database (if applicable)
# mysqldump nexus_db > $BACKUP_DIR/database.sql

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Process
```bash
#!/bin/bash
# restore.sh
BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# Stop service
sudo systemctl stop nexus-agent

# Restore data
tar -xzf $BACKUP_DIR/data.tar.gz -C /

# Restore config
cp $BACKUP_DIR/.env /opt/nexus/
cp -r $BACKUP_DIR/config /opt/nexus/

# Start service
sudo systemctl start nexus-agent

echo "Recovery completed from: $BACKUP_DIR"
```

## 📋 Deployment Checklist

Before going live:

### Pre-deployment
- [ ] Code tested locally
- [ ] Dependencies installed
- [ ] Configuration validated
- [ ] Security settings configured
- [ ] SSL certificates installed
- [ ] Monitoring setup
- [ ] Backup strategy implemented

### Deployment
- [ ] Service deployed successfully
- [ ] Health checks passing
- [ ] Logs showing normal operation
- [ ] API endpoints responding
- [ ] Security tests passed
- [ ] Performance benchmarks met

### Post-deployment
- [ ] Monitoring alerts configured
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Incident response plan ready
- [ ] Backup verified working
- [ ] Performance baseline established

## 🔄 Updates & Maintenance

### Rolling Updates
```bash
# Zero-downtime update
git pull origin main
docker build -t nexus-agent:new .
docker-compose up -d nexus-agent

# Kubernetes rolling update
kubectl set image deployment/nexus-agent nexus-agent=nexus-agent:new
kubectl rollout status deployment/nexus-agent
```

### Maintenance Schedule
- **Daily**: Health check monitoring
- **Weekly**: Log rotation and cleanup
- **Monthly**: Security updates
- **Quarterly**: Performance review
- **Annually**: Security audit

---

**Need help?** Check `HOW_TO_CLI.md` for CLI usage or `TROUBLESHOOTING.md` for common deployment issues.