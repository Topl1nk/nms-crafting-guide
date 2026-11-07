; Windows installer for NMS Crafting Guide: `iscc /DAppVersion=1.2.3 desktop\installer\nms-crafting-guide.iss` after desktop/build.py.
; Per-user by default (no administrator prompt, installs under %LOCALAPPDATA%\Programs); the wizard offers
; "for all users" too. What the player makes (pictures, window settings) lives in %LOCALAPPDATA%\nms-crafting-guide, apart from the
; program, so an update or an uninstall of the program does not touch it.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E1B6B3A-4F0C-4F5B-9A53-4D5B0F5E2C11}
AppName=NMS Crafting Guide
AppVersion={#AppVersion}
AppPublisher=Topl1nk
AppPublisherURL=https://github.com/Topl1nk/nms-crafting-guide
DefaultDirName={autopf}\nms-crafting-guide
DefaultGroupName=NMS Crafting Guide
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\nms-crafting-guide.exe
OutputDir=..\out
OutputBaseFilename=nms-crafting-guide-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; An update over a running copy: close it rather than fail on a locked file.
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
; The game's languages that Inno Setup ships a wizard translation for (it has none for Korean or Chinese).
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[InstallDelete]
; The program was called NMSii before: take its old file and shortcuts away on an update.
Type: files; Name: "{app}\NMSii.exe"
Type: files; Name: "{autoprograms}\NMSii.lnk"
Type: files; Name: "{autodesktop}\NMSii.lnk"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\out\nms-crafting-guide\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\NMS Crafting Guide"; Filename: "{app}\nms-crafting-guide.exe"
Name: "{autodesktop}\NMS Crafting Guide"; Filename: "{app}\nms-crafting-guide.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\nms-crafting-guide.exe"; Description: "{cm:LaunchProgram,NMS Crafting Guide}"; Flags: nowait postinstall skipifsilent
