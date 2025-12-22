# Domain Setup Guide: noc-configmaker.nxlink.com

Your domain is pointing to your VM! Now we need to configure Nginx to serve your application with HTTPS.

## Quick Setup (Run on VM)

**SSH into your VM:**
```bash
ssh <user>@<vm-ip>
```

**Navigate to the deployment directory:**
```bash
cd ~/vm_deployment
```

**Make the script executable and run it:**
```bash
chmod +x configure_nginx_domain.sh
bash configure_nginx_domain.sh
```

The script will:
1. ✅ Install Certbot (for free SSL certificates)
2. ✅ Create Nginx configuration for your domain
3. ✅ Obtain SSL certificate from Let's Encrypt
4. ✅ Configure HTTPS redirect
5. ✅ Open firewall ports 80 and 443

## What the Script Does

1. **HTTP → HTTPS Redirect**: All HTTP traffic automatically redirects to HTTPS
2. **SSL Certificate**: Gets a free certificate from Let's Encrypt
3. **Reverse Proxy**: Routes all requests to your Flask backend (port 5000)
4. **Domain Configuration**: Sets up `noc-configmaker.nxlink.com` as the server name

## Verify Everything Works

**1. Check if backend service is running:**
```bash
sudo systemctl status noc-configmaker
```

**2. If not running, start it:**
```bash
sudo systemctl start noc-configmaker
```

**3. Check Nginx status:**
```bash
sudo systemctl status nginx
```

**4. Test your domain:**
Open in browser: `https://noc-configmaker.nxlink.com`

## Troubleshooting

### If you see "Welcome to nginx" page:
- The script may not have run yet, or Nginx config wasn't updated
- Run: `sudo nginx -t` to check for errors
- Run: `sudo systemctl reload nginx` to reload config

### If SSL certificate fails:
- Make sure domain DNS is fully propagated (can take a few minutes)
- Check DNS: `nslookup noc-configmaker.nxlink.com` should return `192.168.11.118`
- Try again: `sudo certbot --nginx -d noc-configmaker.nxlink.com`

### If backend is not responding:
- Check logs: `sudo journalctl -u noc-configmaker -f`
- Restart service: `sudo systemctl restart noc-configmaker`
- Verify port 5000: `sudo netstat -tlnp | grep 5000`

### If you get connection errors:
- Check firewall: `sudo ufw status`
- Open ports if needed: `sudo ufw allow 80/tcp && sudo ufw allow 443/tcp`

## Manual Configuration (If Script Fails)

If the script doesn't work, you can manually configure:

**1. Edit Nginx config:**
```bash
sudo nano /etc/nginx/sites-available/noc-configmaker-domain
```

**2. Get SSL certificate:**
```bash
sudo certbot --nginx -d noc-configmaker.nxlink.com
```

**3. Reload Nginx:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## After Setup

Your application will be accessible at:
- **HTTPS**: `https://noc-configmaker.nxlink.com` ✅ (Recommended)
- **HTTP**: `http://noc-configmaker.nxlink.com` (will redirect to HTTPS)

All API calls will automatically go through HTTPS, and your Flask backend will handle everything.

## Certificate Renewal

Let's Encrypt certificates expire every 90 days. Certbot automatically renews them, but you can test renewal:
```bash
sudo certbot renew --dry-run
```

---

**Need Help?** Check the logs:
- Backend: `sudo journalctl -u noc-configmaker -f`
- Nginx: `sudo tail -f /var/log/nginx/error.log`
