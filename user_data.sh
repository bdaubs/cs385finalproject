#!/bin/bash
set -euxo pipefail

exec > >(tee /var/log/user-data.log) 2>&1

apt-get update -y
apt-get install -y nginx php-fpm php-cli curl unzip

cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install

aws --version

mkdir -p /tmp/site-restore
aws s3 cp "s3://${bucket_name}/${s3_key}" /tmp/site-latest.tar.gz

tar -xzf /tmp/site-latest.tar.gz -C /tmp/site-restore

rm -rf /var/www/html
cp -r /tmp/site-restore/html /var/www/html

if [ -f /tmp/site-restore/nginx-default.conf ]; then
  cp /tmp/site-restore/nginx-default.conf /etc/nginx/sites-available/default
fi

chown -R www-data:www-data /var/www/html

nginx -t

systemctl enable nginx

if systemctl list-unit-files | grep -q '^php8.3-fpm'; then
  systemctl enable php8.3-fpm
  systemctl restart php8.3-fpm
elif systemctl list-unit-files | grep -q '^php8.4-fpm'; then
  systemctl enable php8.4-fpm
  systemctl restart php8.4-fpm
else
  systemctl restart php-fpm || true
fi

systemctl restart nginx
