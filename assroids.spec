# assroids.spec
# Run with: pyinstaller assroids.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Images
        ('AssROIDS Menu BG.png',        '.'),
        ('Blast Off Button.png',        '.'),
        ('Exit Button.png',             '.'),
        ('READ ME Button.png',          '.'),
        ('Settings Button.png',         '.'),
        ('ship.png',                    '.'),
        ('ship_w_shield.png',           '.'),
        ('butt.png',                    '.'),
        ('poop.png',                    '.'),
        ('Dick Butt Boss.png',          '.'),
        ('TitVag Boss.png',             '.'),
        ('Coin Purse Boss.png',         '.'),
        ('Condom Power Up Icon.png',    '.'),
        ('Zinc Tab Power Up Icon.png',  '.'),
        ('DP Can Icon.png',             '.'),
        # Audio
        ('Ass Roids Menu Song.mp3',     '.'),
        ('Space Amb.mp3',               '.'),
        ('Button Tick.mp3',             '.'),
        ('Blast Off SFX.mp3',           '.'),
        ('Main Gun Sound.mp3',          '.'),
        ('Poop Splat.mp3',              '.'),
        ('Butt Smack.mp3',              '.'),
        ('Boss Enter Cluck.mp3',        '.'),
        ('Tit Vag Boss SFX.mp3',        '.'),
        ('Coin Purse Boss SFX.mp3',     '.'),
        ('Boss Death FX.mp3',           '.'),
        ('Swoosh.mp3',                  '.'),
        ('Rubber Pop.mp3',              '.'),
        ('Gulp.mp3',                    '.'),
        ('Milk Beam SFX long.mp3',      '.'),
        ('Dick Butt Sus SFX.mp3',       '.'),
        ('Thrusters SFX.mp3',           '.'),
        ('Player Death SFX.mp3',        '.'),
        ('Mandingo Ship.png',           '.'),
        ('Mandingo Enter SFX.mp3',      '.'),
        ('Mandingo Engine SFX.mp3',     '.'),
        ('Mandingo Beam Charge SFX.mp3', '.'),
        ('Explosion - SFX.mp3',         '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AssROIDS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # no terminal window when launched
    icon='AssROIDS ICON.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AssROIDS',
)
