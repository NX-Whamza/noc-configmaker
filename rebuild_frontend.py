"""Rebuild frontend container to pick up nginx.conf changes."""
import paramiko

PASSWORD = 'Omolayo@2016$'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.11.118', username='whamza', password=PASSWORD)

cmds = [
    f'cd ~/noc-configmaker && echo "{PASSWORD}" | sudo -S docker compose build --no-cache frontend 2>&1 | tail -5',
    f'cd ~/noc-configmaker && echo "{PASSWORD}" | sudo -S docker compose up -d 2>&1',
    f'sleep 3 && cd ~/noc-configmaker && echo "{PASSWORD}" | sudo -S docker compose ps 2>&1',
]

for cmd in cmds:
    display = cmd.replace(PASSWORD, '***')
    print(f'>>> {display[:100]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    print()

ssh.close()
print('Frontend rebuild complete')
