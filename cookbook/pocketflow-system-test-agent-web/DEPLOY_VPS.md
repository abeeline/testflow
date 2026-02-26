# VPS Deployment (One-Click)

## 1) Push code to GitHub

Repository:

- `https://github.com/abeeline/testflow.git`

## 2) Run one script on VPS

```bash
sudo bash deploy/vps_deploy.sh \
  --repo https://github.com/abeeline/testflow.git \
  --branch main \
  --app-dir /opt/testflow \
  --domain your.domain.com
```

## 3) Result

- app service: `testflow-web` (systemd)
- reverse proxy: `nginx -> 127.0.0.1:8010`
- app path on VPS: `/opt/testflow/cookbook/pocketflow-system-test-agent-web`

## 4) TLS (optional)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

## 5) Update after new commits

Rerun the same script. It does `git pull` + service restart.
