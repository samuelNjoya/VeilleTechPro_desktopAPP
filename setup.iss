; ============================================================================
; VEILLE TECH PRO - Script d'installation Inno Setup
; Version : 2.0
; ============================================================================

[Setup]
AppName=Veille Tech Pro
AppVersion=2.0.0
AppPublisher=VeilleTech
AppPublisherURL=https://github.com/veilletech
AppSupportURL=https://github.com/veilletech
AppUpdatesURL=https://github.com/veilletech
DefaultDirName={pf}\VeilleTech
DefaultGroupName=Veille Tech Pro
UninstallDisplayIcon={app}\VeilleTech.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=VeilleTech_Setup
SetupIconFile=assets\icons\app_icon.ico
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Languages\English.isl"

[Files]
Source: "dist\VeilleTech.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "locales\*"; DestDir: "{app}\locales"; Flags: ignoreversion recursesubdirs
Source: "assets\icons\*"; DestDir: "{app}\assets\icons"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Veille Tech Pro"; Filename: "{app}\VeilleTech.exe"; WorkingDir: "{app}"
Name: "{group}\Désinstaller"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Veille Tech Pro"; Filename: "{app}\VeilleTech.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\VeilleTech.exe"; Description: "{cm:LaunchProgram,Veille Tech Pro}"; Flags: postinstall nowait skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\VeilleTech\VeilleTechPro"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"