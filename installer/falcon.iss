#define MyAppName "Falcon"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Falcon Language"
#define MyAppExeName "falcon.exe"

[Setup]
AppId={{8EE95CAA-1EC9-4CB7-8E93-7AF223B4A8D8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=falcon-setup-x64
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addtopath"; Description: "Add Falcon to PATH"; GroupDescription: "Additional tasks:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: addtopath

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  EnvironmentKey = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';

procedure AddToPath(Path: string);
var
  PrevPath: string;
begin
  if not RegQueryStringValue(HKLM, EnvironmentKey, 'Path', PrevPath) then
    PrevPath := '';
  if Pos(';' + Uppercase(Path) + ';', ';' + Uppercase(PrevPath) + ';') = 0 then
  begin
    if (PrevPath <> '') and (PrevPath[Length(PrevPath)] <> ';') then
      PrevPath := PrevPath + ';';
    PrevPath := PrevPath + Path;
    RegWriteStringValue(HKLM, EnvironmentKey, 'Path', PrevPath);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
    AddToPath(ExpandConstant('{app}'));
end;
