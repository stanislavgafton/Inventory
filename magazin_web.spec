# Build: python -m PyInstaller --noconfirm magazin_web.spec
a = Analysis(['web_app.py'], pathex=[], binaries=[], datas=[('web', 'web'), ('inventario.db', '.')], hiddenimports=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name='MagazinWeb', console=True)
