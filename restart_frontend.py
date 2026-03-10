"""Restart frontend container to reload nginx.conf."""
import paramiko

PASSWORD = 'Omolayo@2016$'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.11.118', username='whamza', password=PASSWORD)

cmd = f'cd ~/noc-configmaker && echo "{PASSWORD}" | sudo -S docker compose restart frontend 2>&1'
print(f'>>> restarting frontend...')
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
print(stdout.read().decode().strip())
print(stderr.read().decode().strip())

ssh.close()
print('Done')
