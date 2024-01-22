# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['github_pr_monitor/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='github_pr_monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='github_pr_monitor.entitlements',
    icon=['assets/github_pr_monitor.icns'],
)
app = BUNDLE(
    exe,
    name='github_pr_monitor.app',
    icon='assets/github_pr_monitor.icns',
    bundle_identifier='com.ffoissey.githubprmonitor',
    info_plist= {
        'LSUIElement': 'YES',
    },
)
