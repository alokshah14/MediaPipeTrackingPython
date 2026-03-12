; Inno Setup Script for Finger Invaders
; Install Inno Setup from: https://jrsoftware.org/isdl.php
; Then compile this script to create FingerInvaders-Setup.exe

#define MyAppName "Finger Invaders"
#define MyAppVersion "1.0"
#define MyAppPublisher "Ultraleap Research"
#define MyAppExeName "FingerInvaders.exe"
#define MyAppURL "https://github.com/alokshah14/LeapTrackingPython"

[Setup]
; Basic info
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directory
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Output
OutputDir=installer_output
OutputBaseFilename=FingerInvaders-Setup
SetupIconFile=icon.ico
Compression=lzma2/max
SolidCompression=yes

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; UI
WizardStyle=modern
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Include all files from the dist\FingerInvaders folder
Source: "dist\FingerInvaders\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UltraleapInstalled: Boolean;
  Response: Integer;
begin
  // Check if Ultraleap Hand Tracking is installed
  UltraleapInstalled := DirExists('C:\Program Files\Ultraleap\LeapSDK');

  if not UltraleapInstalled then
  begin
    Response := MsgBox('Ultraleap Hand Tracking Service is required but not detected.' + #13#10 + #13#10 +
                       'Would you like to download it now?' + #13#10 + #13#10 +
                       'Click Yes to open the download page, or No to continue anyway (simulation mode only).',
                       mbConfirmation, MB_YESNO);

    if Response = IDYES then
    begin
      // Open Ultraleap download page
      ShellExec('open', 'https://leap2.ultraleap.com/downloads/', '', '', SW_SHOW, ewNoWait, ResultCode);
      // Don't continue installation
      Result := False;
      Exit;
    end;
  end;

  Result := True;
end;
