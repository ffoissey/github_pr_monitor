# -*- mode: python ; coding: utf-8 -*-

a = Analysis(['github_pr_monitor/main.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             noarchive=False)

pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='github_pr_monitor',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          argv_emulation=True,
          icon=['assets/github_pr_monitor.icns'],
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)

coll = COLLECT(exe,
               a.binaries,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='github_pr_monitor')

app = BUNDLE(coll,
             name='github_pr_monitor.app',
             icon=None,
             bundle_identifier=None)







