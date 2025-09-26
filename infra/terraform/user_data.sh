#!/bin/bash
set -euo pipefail

LOG_GROUP="${log_group}"
REGION="${region}"

amazon-linux-extras enable docker
dnf install -y docker awslogs
systemctl enable docker
systemctl start docker

# Configure awslogs
cat >/etc/awslogs/awscli.conf <<EOF
[plugins]
cwlogs = cwlogs
[default]
region = ${REGION}
EOF

cat >/etc/awslogs/awslogs.conf <<EOF
[general]
state_file = /var/lib/awslogs/agent-state

[docker]
file = /var/lib/docker/containers/*/*-json.log
log_group_name = ${LOG_GROUP}
log_stream_name = {hostname}/docker
datetime_format = %Y-%m-%dT%H:%M:%S
EOF

systemctl enable awslogsd
systemctl start awslogsd

# Pull and run stressed services to generate load and logs
docker run -d --name postgres -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:15
docker run -d --name mysql -e MYSQL_ROOT_PASSWORD=pass -p 3306:3306 mysql:8
docker run -d --name redis -p 6379:6379 redis:7

# Intentionally heavy service (limited resources) to induce pressure
docker run -d --name stress --cpus=0.25 --memory=256m progrium/stress --cpu 2 --io 1 --vm 1 --vm-bytes 128M

echo "Setup complete" | logger



