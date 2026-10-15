; Script Inno Setup — produit NCK-Setup-<version>.exe
; Compilation : iscc /DVersion=0.12.0 installateur\windows\nck.iss   (depuis la racine du dépôt, après construire.py)
#ifndef Version
  #define Version "0.0.0"
#endif
#define Nom "NCK"
#define Editeur "NockiProgramTECH"
#define URL "https://github.com/NockiProgramTECH/nck"

[Setup]
AppId={{7D1D2C3A-8E8B-4A8A-9C9E-0C4B1A2F3E5D}
AppName={#Nom}
AppVersion={#Version}
AppVerName={#Nom} {#Version}
AppPublisher={#Editeur}
AppPublisherURL={#URL}
AppSupportURL={#URL}/issues
DefaultDirName={autopf}\NCK
DefaultGroupName={#Nom}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist
OutputBaseFilename=NCK-Setup-{#Version}
SetupIconFile=..\..\editeurs\vscode\icones\nck.ico
UninstallDisplayIcon={app}\nck.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes
ChangesEnvironment=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "path"; Description: "Ajouter nck au PATH (utiliser « nck » dans n'importe quel terminal)"; GroupDescription: "Intégration :"
Name: "assoc"; Description: "Associer les fichiers .nck à NCK (icône + double-clic pour exécuter)"; GroupDescription: "Intégration :"
Name: "menu"; Description: "Ajouter « Exécuter avec NCK » au menu contextuel des fichiers .nck"; GroupDescription: "Intégration :"
Name: "vscode"; Description: "Installer l'extension NCK pour Visual Studio Code (coloration, erreurs, complétion)"; GroupDescription: "Éditeur :"; Flags: unchecked
Name: "exemples"; Description: "Copier les exemples dans Documents\NCK\exemples"; GroupDescription: "Divers :"

[Files]
Source: "..\..\dist\nck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\nck\exemples\*"; DestDir: "{userdocs}\NCK\exemples"; Flags: ignoreversion recursesubdirs; Tasks: exemples
Source: "..\..\dist\nck\editeurs\vscode\*"; DestDir: "{%USERPROFILE}\.vscode\extensions\nck-lang"; Flags: ignoreversion recursesubdirs createallsubdirs; Tasks: vscode

[Icons]
Name: "{group}\NCK (console)"; Filename: "{app}\nck.exe"; WorkingDir: "{userdocs}\NCK"
Name: "{group}\Documentation NCK"; Filename: "{app}\docs\LANGAGE.md"
Name: "{group}\Désinstaller NCK"; Filename: "{uninstallexe}"

[Registry]
; Association .nck
Root: HKA; Subkey: "Software\Classes\.nck"; ValueType: string; ValueName: ""; ValueData: "NCK.Fichier"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\NCK.Fichier"; ValueType: string; ValueName: ""; ValueData: "Programme NCK"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\editeurs\vscode\icones\nck.ico,0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\shell\open\command"; ValueType: string; ValueName: ""; ValueData: "cmd.exe /k """"{app}\nck.exe"" ""%1"""""; Tasks: assoc
; Menu contextuel
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\shell\nck_executer"; ValueType: string; ValueName: ""; ValueData: "Exécuter avec NCK"; Flags: uninsdeletekey; Tasks: menu
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\shell\nck_executer"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\nck.exe"; Tasks: menu
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\shell\nck_executer\command"; ValueType: string; ValueName: ""; ValueData: "cmd.exe /k """"{app}\nck.exe"" ""%1"""""; Tasks: menu
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\shell\nck_verifier"; ValueType: string; ValueName: ""; ValueData: "Vérifier avec NCK"; Flags: uninsdeletekey; Tasks: menu
Root: HKA; Subkey: "Software\Classes\NCK.Fichier\shell\nck_verifier\command"; ValueType: string; ValueName: ""; ValueData: "cmd.exe /k """"{app}\nck.exe"" verifier ""%1"""""; Tasks: menu

[Run]
Filename: "{app}\nck.exe"; Parameters: "info"; Description: "Afficher les informations NCK"; Flags: postinstall nowait skipifsilent shellexec unchecked

[Code]
// Ajout / retrait du PATH utilisateur (ou machine si installé en admin), sans doublon.
function CleEnv(): String;
begin
  if IsAdminInstallMode then Result := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
  else Result := 'Environment';
end;

function RacineEnv(): Integer;
begin
  if IsAdminInstallMode then Result := HKLM else Result := HKCU;
end;

procedure AjouterAuPath(Dossier: String);
var Chemin: String;
begin
  if not RegQueryStringValue(RacineEnv(), CleEnv(), 'Path', Chemin) then Chemin := '';
  if Pos(';' + Uppercase(Dossier) + ';', ';' + Uppercase(Chemin) + ';') > 0 then exit;
  if (Chemin <> '') and (Chemin[Length(Chemin)] <> ';') then Chemin := Chemin + ';';
  RegWriteExpandStringValue(RacineEnv(), CleEnv(), 'Path', Chemin + Dossier);
end;

procedure RetirerDuPath(Dossier: String);
var Chemin: String; P: Integer;
begin
  if not RegQueryStringValue(RacineEnv(), CleEnv(), 'Path', Chemin) then exit;
  P := Pos(';' + Uppercase(Dossier) + ';', ';' + Uppercase(Chemin) + ';');
  if P = 0 then exit;
  Delete(Chemin, P, Length(Dossier) + 1);
  if (Chemin <> '') and (Chemin[1] = ';') then Delete(Chemin, 1, 1);
  RegWriteExpandStringValue(RacineEnv(), CleEnv(), 'Path', Chemin);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('path') then AjouterAuPath(ExpandConstant('{app}'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then RetirerDuPath(ExpandConstant('{app}'));
end;
