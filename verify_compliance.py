import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.11.118', username='whamza', password='Omolayo@2016$')
cmd = """curl -sv http://localhost:8000/api/compliance/blocks?loopback_ip=10.3.24.4 2>&1 | head -30"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err.strip():
    print('STDERR:', err)
ssh.close()
