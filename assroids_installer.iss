; assroids_installer.iss
; Compile with Inno Setup 6: https://jrsoftware.org/isinfo.php

[Setup]
AppName=AssROIDS
AppVersion=1.0
AppPublisher=HSTV
DefaultDirName={autopf}\AssROIDS
DefaultGroupName=AssROIDS
OutputDir=installer_output
OutputBaseFilename=AssROIDS_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Optional: swap butt.png for a proper .ico file
;SetupIconFile=assroids.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Include everything PyInstaller collected into dist\AssROIDS\
Source: "dist\AssROIDS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Include the README next to the exe so open_readme() can find it
Source: "README_GAME.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AssROIDS";         Filename: "{app}\AssROIDS.exe"
Name: "{group}\Uninstall AssROIDS"; Filename: "{uninstallexe}"
Name: "{commondesktop}\AssROIDS"; Filename: "{app}\AssROIDS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AssROIDS.exe"; Description: "Launch AssROIDS"; Flags: nowait postinstall skipifsilent
