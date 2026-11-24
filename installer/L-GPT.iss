#define MyAppName "L-GPT"
#ifndef AppVersion
  #define AppVersion "3.1.0"
#endif
#define MyAppPublisher "L-GPT"
#define MyAppExeName "L-GPT.exe"

[Setup]
AppId={{C5F6A8D1-2B34-4A7C-9D18-6E3F0B71A931}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\L-GPT
DefaultGroupName=L-GPT
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=L-GPT-Setup-{#AppVersion}
SetupIconFile=..\assets\lgpt.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "..\dist\L-GPT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\L-GPT"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\L-GPT"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer L-GPT"; Flags: postinstall nowait skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWin64 then
  begin
    MsgBox('Cette version de L-GPT nécessite Windows 64 bits.', mbError, MB_OK);
    Result := False;
  end;
end;
