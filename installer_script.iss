[Setup]
AppName=YouTube & TikTok Master Control
AppVersion=1.0.0
DefaultDirName={autopf}\YoutubeTiktokMasterControl
DefaultGroupName=YouTube & TikTok Master Control
OutputDir=Output
OutputBaseFilename=YoutubeTiktokMasterControl_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un icono en el escritorio"; GroupDescription: "Iconos adicionales:"

[Files]
Source: "dist\YoutubeTiktokMasterControl\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: ".env"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\YouTube & TikTok Master Control"; Filename: "{app}\YoutubeTiktokMasterControl.exe"
Name: "{autodesktop}\YouTube & TikTok Master Control"; Filename: "{app}\YoutubeTiktokMasterControl.exe"; Tasks: desktopicon
Name: "{group}\Desinstalar YouTube & TikTok Master Control"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\YoutubeTiktokMasterControl.exe"; Description: "Ejecutar YouTube & TikTok Master Control"; Flags: nowait postinstall skipifsilent
