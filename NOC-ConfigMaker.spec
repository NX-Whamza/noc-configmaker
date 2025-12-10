# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('NOC-configMaker.html', '.'), ('login.html', '.'), ('change-password.html', '.'), ('config_policies', 'config_policies'), ('nextlink_standards.py', '.'), ('nextlink_enterprise_reference.py', '.'), ('nextlink_compliance_reference.py', '.')]
binaries = []
hiddenimports = ['flask', 'flask_cors', 'werkzeug', 'werkzeug.serving', 'requests', 'sqlite3', 'smtplib', 'email', 'email.mime', 'email.mime.text', 'email.mime.multipart', 'api_server', 'nextlink_standards', 'nextlink_enterprise_reference', 'nextlink_compliance_reference', 'hashlib', 'secrets', 'base64', 'json', 'jwt', 'jwt.algorithms']
tmp_ret = collect_all('flask')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('werkzeug')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='NOC-ConfigMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
