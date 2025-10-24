# MongoDB Deployment Guide for Hostinger VPS

This guide covers deploying MongoDB Community Edition on your Hostinger VPS using Docker Compose.

## Prerequisites

1. Hostinger VPS with Docker installed
2. SSH access to your VPS
3. At least 2GB RAM available
4. 10GB+ free disk space

## Quick Start

### 1. Install Docker & Docker Compose (if not installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (avoid using sudo)
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

### 2. Create Environment File

```bash
# Create project directory
mkdir -p ~/scf-mongodb
cd ~/scf-mongodb

# Create .env file with secure passwords
cat > .env << 'EOF'
# MongoDB Root Password (CHANGE THIS!)
MONGO_ROOT_PASSWORD=YourSecurePassword123!

# Mongo Express Web UI Credentials (CHANGE THIS!)
MONGOEXPRESS_USERNAME=admin
MONGOEXPRESS_PASSWORD=AnotherSecurePassword456!
EOF

# Secure the .env file
chmod 600 .env
```

### 3. Create Docker Compose File

Copy the `docker-compose.mongodb.yml` to your VPS:

```bash
# Option 1: Create the file directly
nano docker-compose.yml
# Paste the contents from docker-compose.mongodb.yml

# Option 2: Upload via SCP from your local machine
scp docker-compose.mongodb.yml user@your-vps-ip:~/scf-mongodb/docker-compose.yml
```

### 4. Start MongoDB

```bash
cd ~/scf-mongodb

# Start MongoDB (detached mode)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mongodb
```

### 5. Import SCF Data

**Option 1: Using mongoimport (from your local machine)**
```bash
# Copy JSON file to VPS
scp scf_mongodb.json user@your-vps-ip:~/scf-mongodb/

# SSH into VPS and import
ssh user@your-vps-ip
cd ~/scf-mongodb

# Import data
docker exec -i scf-mongodb mongoimport \
  --username admin \
  --password YourSecurePassword123! \
  --authenticationDatabase admin \
  --db scf \
  --collection controls \
  --file /data/db/../scf_mongodb.json \
  --jsonArray

# Or copy file into container first
docker cp scf_mongodb.json scf-mongodb:/tmp/
docker exec scf-mongodb mongoimport \
  --username admin \
  --password YourSecurePassword123! \
  --authenticationDatabase admin \
  --db scf \
  --collection controls \
  --file /tmp/scf_mongodb.json \
  --jsonArray
```

**Option 2: Using Python script**
```python
from pymongo import MongoClient
import json

# Connect to MongoDB
client = MongoClient(
    'mongodb://admin:YourSecurePassword123!@your-vps-ip:27017/',
    authSource='admin'
)
db = client['scf']

# Load and insert data
with open('scf_mongodb.json', 'r', encoding='utf-8') as f:
    controls = json.load(f)
    db.controls.insert_many(controls)
    print(f"Inserted {len(controls)} controls")

# Create indexes for performance
db.controls.create_index('domain.identifier')
db.controls.create_index('framework_mappings.nist_800_53_rev5')
print("Indexes created")
```

### 6. Create Indexes

```bash
# Connect to MongoDB shell
docker exec -it scf-mongodb mongosh -u admin -p YourSecurePassword123! --authenticationDatabase admin

# In the MongoDB shell:
use scf

// Create indexes
db.controls.createIndex({ "domain.identifier": 1 })
db.controls.createIndex({ "framework_mappings.nist_800_53_rev5": 1 })
db.controls.createIndex({ "framework_mappings.iso_27001_v2022": 1 })
db.controls.createIndex({ "scf_core.esp_level_1_foundational": 1 })
db.controls.createIndex({ title: "text", "domain.name": "text" })

// Verify indexes
db.controls.getIndexes()

// Verify data
db.controls.countDocuments()

exit
```

---

## Security Hardening (IMPORTANT!)

### 1. Firewall Configuration

```bash
# Install UFW if not installed
sudo apt install ufw -y

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# DO NOT expose MongoDB port publicly
# MongoDB should only be accessible locally or via VPN

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 2. Use Reverse Proxy for Mongo Express (Optional)

If you want to access Mongo Express web UI securely:

```bash
# Install nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Create nginx config
sudo nano /etc/nginx/sites-available/mongo-express

# Add this configuration:
```

```nginx
server {
    listen 80;
    server_name mongo.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mongo-express /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d mongo.yourdomain.com
```

### 3. MongoDB Authentication

**Create read-only user for your application:**

```bash
docker exec -it scf-mongodb mongosh -u admin -p YourSecurePassword123! --authenticationDatabase admin

# In MongoDB shell:
use scf

db.createUser({
  user: "scf_app",
  pwd: "AppPassword123!",
  roles: [
    { role: "read", db: "scf" }
  ]
})

# Test the user
exit
```

**Connection string for your app:**
```
mongodb://scf_app:AppPassword123!@your-vps-ip:27017/scf?authSource=scf
```

### 4. Enable SSL/TLS (Recommended for production)

Create self-signed certificate or use Let's Encrypt:

```bash
# Generate self-signed cert (for testing)
docker exec -it scf-mongodb bash
mkdir -p /etc/ssl/mongodb
openssl req -newkey rsa:2048 -new -x509 -days 365 -nodes \
  -out /etc/ssl/mongodb/mongodb-cert.crt \
  -keyout /etc/ssl/mongodb/mongodb-cert.key
cat /etc/ssl/mongodb/mongodb-cert.key /etc/ssl/mongodb/mongodb-cert.crt > /etc/ssl/mongodb/mongodb.pem
exit
```

Update docker-compose.yml:
```yaml
  mongodb:
    command: ["--tlsMode", "requireTLS", "--tlsCertificateKeyFile", "/etc/ssl/mongodb/mongodb.pem"]
    volumes:
      - ./ssl:/etc/ssl/mongodb:ro
```

---

## Backup & Restore

### Automated Backup Script

```bash
# Create backup script
nano ~/scf-mongodb/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
MONGO_PASSWORD="YourSecurePassword123!"

mkdir -p $BACKUP_DIR

# Backup database
docker exec scf-mongodb mongodump \
  --username admin \
  --password $MONGO_PASSWORD \
  --authenticationDatabase admin \
  --db scf \
  --gzip \
  --archive=/data/db/../backup_${DATE}.gz

# Copy backup out of container
docker cp scf-mongodb:/data/backup_${DATE}.gz $BACKUP_DIR/

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/backup_${DATE}.gz"
```

```bash
# Make executable
chmod +x ~/scf-mongodb/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /home/yourusername/scf-mongodb/backup.sh >> /var/log/mongodb-backup.log 2>&1
```

### Restore from Backup

```bash
# Copy backup to container
docker cp backup_20240124_020000.gz scf-mongodb:/data/backup.gz

# Restore
docker exec scf-mongodb mongorestore \
  --username admin \
  --password YourSecurePassword123! \
  --authenticationDatabase admin \
  --gzip \
  --archive=/data/backup.gz \
  --drop
```

---

## Monitoring & Maintenance

### View Logs

```bash
# MongoDB logs
docker-compose logs -f mongodb

# Last 100 lines
docker-compose logs --tail=100 mongodb
```

### Check Resource Usage

```bash
# Container stats
docker stats scf-mongodb

# Disk usage
docker exec scf-mongodb du -sh /data/db
```

### Database Stats

```bash
docker exec -it scf-mongodb mongosh -u admin -p YourSecurePassword123! --authenticationDatabase admin

# In MongoDB shell:
use scf
db.stats()
db.controls.stats()
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs mongodb

# Check permissions
ls -la ~/scf-mongodb/

# Verify environment variables
docker-compose config
```

### Can't Connect Remotely

```bash
# Check if MongoDB is listening
docker exec scf-mongodb netstat -tlnp | grep 27017

# Test connection from VPS
docker exec scf-mongodb mongosh -u admin -p YourSecurePassword123! --eval "db.version()"

# Check firewall
sudo ufw status
```

### Performance Issues

```bash
# Check slow queries
docker exec -it scf-mongodb mongosh -u admin -p YourSecurePassword123! --authenticationDatabase admin

use scf
db.setProfilingLevel(1, { slowms: 100 })
db.system.profile.find().limit(5).sort({ ts: -1 }).pretty()
```

---

## Production Checklist

- [ ] Changed default passwords in `.env`
- [ ] Configured firewall (MongoDB not exposed publicly)
- [ ] Created read-only user for application
- [ ] Set up automated backups
- [ ] Configured resource limits in docker-compose.yml
- [ ] Created necessary indexes
- [ ] Set up monitoring (optional: Prometheus + Grafana)
- [ ] Configured SSL/TLS (if exposing remotely)
- [ ] Set up reverse proxy for Mongo Express (optional)
- [ ] Tested backup and restore process
- [ ] Documented connection strings for your team

---

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart MongoDB
docker-compose restart mongodb

# View container status
docker-compose ps

# Access MongoDB shell
docker exec -it scf-mongodb mongosh -u admin -p YourSecurePassword123! --authenticationDatabase admin

# Backup database
docker exec scf-mongodb mongodump --username admin --password YourSecurePassword123! --authenticationDatabase admin --db scf --gzip --archive=/data/backup.gz

# Restore database
docker exec scf-mongodb mongorestore --username admin --password YourSecurePassword123! --authenticationDatabase admin --gzip --archive=/data/backup.gz

# Update to latest MongoDB version
docker-compose pull
docker-compose up -d
```

---

## Resources

- **Official Docker Compose File:** https://github.com/docker-library/docs/blob/master/mongo/README.md
- **MongoDB Documentation:** https://docs.mongodb.com/
- **Docker Hub - MongoDB:** https://hub.docker.com/_/mongo
- **MongoDB Security Checklist:** https://docs.mongodb.com/manual/administration/security-checklist/
- **Hostinger VPS Guide:** https://www.hostinger.com/tutorials/vps

---

## Connection Examples

### Python (PyMongo)
```python
from pymongo import MongoClient

client = MongoClient(
    'mongodb://scf_app:AppPassword123!@your-vps-ip:27017/scf?authSource=scf'
)
db = client['scf']

# Query
controls = db.controls.find_one({'_id': 'GOV-01'})
```

### Node.js (MongoDB Driver)
```javascript
const { MongoClient } = require('mongodb');

const uri = 'mongodb://scf_app:AppPassword123!@your-vps-ip:27017/scf?authSource=scf';
const client = new MongoClient(uri);

async function run() {
  await client.connect();
  const db = client.db('scf');
  const control = await db.collection('controls').findOne({ _id: 'GOV-01' });
  console.log(control);
}
```

### .NET (MongoDB.Driver)
```csharp
using MongoDB.Driver;

var client = new MongoClient("mongodb://scf_app:AppPassword123!@your-vps-ip:27017/scf?authSource=scf");
var database = client.GetDatabase("scf");
var collection = database.GetCollection<BsonDocument>("controls");
var control = collection.Find(new BsonDocument("_id", "GOV-01")).FirstOrDefault();
```
