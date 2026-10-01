; Inno Setup - MEDICONF dans Program Files + LibreOffice Portable optionnel
#define MyAppName "MEDICONF"
#define MyAppVersion "1.0"
#define MyAppPublisher "JF GUILARD"
#define MyAppExeName "MEDICONF.exe"

[Setup]
AppId={{A7B3C1E2-4F58-4A11-9C2D-000000202601}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MEDICONF
DefaultGroupName=MEDICONF
DisableProgramGroupPage=yes
OutputDir=installer-out
OutputBaseFilename=MEDICONF-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le bureau"; GroupDescription: "Raccourcis :"
Name: "libreoffice"; Description: "Telecharger et installer LibreOffice Portable a cote de MEDICONF (environ 213 Mo)"; GroupDescription: "Bureautique :"; Flags: unchecked

[Files]
Source: "dist\MEDICONF.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer-lo.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MEDICONF"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller MEDICONF"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MEDICONF"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer MEDICONF"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\LibreOfficePortable"
Type: files; Name: "{app}\installer-lo.ps1"

[Code]
var
  InstallerLO: Boolean;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  InstallerLO := False;
  if WizardIsTaskSelected('libreoffice') then
  begin
    if MsgBox('Confirmez-vous le telechargement puis l''installation de LibreOffice Portable (~213 Mo) dans :' + #13#10 +
              ExpandConstant('{app}\LibreOfficePortable') + #13#10#13#10 +
              'Oui = telecharger et installer' + #13#10 +
              'Non = installer seulement MEDICONF',
              mbConfirmation, MB_YESNO) = IDYES then
      InstallerLO := True;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if (CurStep = ssPostInstall) and InstallerLO then
  begin
    WizardForm.StatusLabel.Caption := 'Telechargement de LibreOffice Portable...';
    if not Exec('powershell.exe',
      '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\installer-lo.ps1') + '"',
      '', SW_SHOW, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
      MsgBox('LibreOffice Portable n''a pas pu etre installe. MEDICONF est installe. Relancez le setup pour reessayer.', mbError, MB_OK)
    else
      MsgBox('LibreOffice Portable est installe a cote de MEDICONF.', mbInformation, MB_OK);
  end;
end;
