; Windows installer for NMSii: `iscc /DAppVersion=1.2.3 desktop\installer\nmsii.iss` after desktop/build.py.
; Per-user by default (no administrator prompt, installs under %LOCALAPPDATA%\Programs); the wizard offers
; "for all users" too. What the player makes (pictures, window settings) lives in %LOCALAPPDATA%\NMSii, apart from the
; program, so an update or an uninstall of the program does not touch it.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E1B6B3A-4F0C-4F5B-9A53-4D5B0F5E2C11}
AppName=NMSii
AppVersion={#AppVersion}
AppPublisher=Topl1nk
AppPublisherURL=https://github.com/Topl1nk/nms-crafting-guide
DefaultDirName={autopf}\NMSii
DefaultGroupName=NMSii
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\NMSii.exe
OutputDir=..\out
OutputBaseFilename=NMSii-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; An update over a running copy: close it rather than fail on a locked file.
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\out\NMSii\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\NMSii"; Filename: "{app}\NMSii.exe"
Name: "{autodesktop}\NMSii"; Filename: "{app}\NMSii.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NMSii.exe"; Description: "{cm:LaunchProgram,NMSii}"; Flags: nowait postinstall skipifsilent
