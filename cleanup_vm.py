"""Clean up disk space on the VM and redeploy."""
import paramiko

PASSWORD = 'Omolayo@2016$'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.11.118', username='whamza', password=PASSWORD)

cmds = [
    'df -h /',
    f'echo "{PASSWORD}" | sudo -S docker system prune -af 2>&1 | tail -5',
    f'echo "{PASSWORD}" | sudo -S journalctl --vacuum-size=50M 2>&1 | tail -3',
    f'echo "{PASSWORD}" | sudo -S apt-get clean 2>&1',
    f'echo "{PASSWORD}" | sudo -S rm -rf /tmp/* 2>&1',
    f'echo "{PASSWORD}" | sudo -S rm -rf /var/tmp/* 2>&1',
    f'echo "{PASSWORD}" | sudo -S rm -rf /var/log/*.gz /var/log/*.1 /var/log/*.old 2>&1',
    'rm -rf ~/noc-configmaker/.git/index.lock 2>/dev/null; echo ok',
    'df -h /',
]

for cmd in cmds:
    display = cmd.replace(PASSWORD, '***')
    print(f'>>> {display[:100]}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    print()

ssh.close()
print('Cleanup complete')
