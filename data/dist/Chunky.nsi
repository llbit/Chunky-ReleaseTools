; NSIS script for Chunky
; Copyright (c) 2013, Jesper �qvist <jesper@llbit.se>

; Use Modern UI
!include "MUI2.nsh"
!define MUI_ICON "dist\chunky.ico"

Name "Chunky"
OutFile "build\Chunky-@VERSION@.exe"

InstallDir $PROGRAMFILES\Chunky

; Registry key to save install directory
InstallDirRegKey HKLM "Software\Chunky" "Install_Dir"

; request admin privileges
RequestExecutionLevel admin

; Warn on abort
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_LICENSE LICENSE
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

  !define MUI_FINISHPAGE_NOAUTOCLOSE
  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_NOTCHECKED
  !define MUI_FINISHPAGE_RUN_TEXT "Start Chunky"
  !define MUI_FINISHPAGE_RUN_FUNCTION "StartChunky"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

Function .onInit

  Var /GLOBAL JavaExe

  ; First check for 64 bit JRE
  SetRegView 64
  ReadRegStr $0 HKLM "Software\JavaSoft\Java Runtime Environment" "CurrentVersion"
  StrCmp $0 "" FindJRE64_2
  ReadRegStr $1 HKLM "Software\JavaSoft\Java Runtime Environment\$0" "JavaHome"
  StrCmp $1 "" FindJRE64_2 FoundJava

  ; JRE 9.0.1 registry entries are in Software\JavaSoft\JRE:
  FindJRE64_2:
  ReadRegStr $0 HKLM "Software\JavaSoft\JRE" "CurrentVersion"
  StrCmp $0 "" FindJDK64
  ReadRegStr $1 HKLM "Software\JavaSoft\JRE\$0" "JavaHome"
  StrCmp $1 "" FindJDK64 FoundJava

  ; 64 bit JDK
  FindJDK64:
  ReadRegStr $0 HKLM "Software\JavaSoft\Java Development Kit" "CurrentVersion"
  StrCmp $0 "" FindJDK64_2
  ReadRegStr $1 HKLM "Software\JavaSoft\Java Development Kit\$0" "JavaHome"
  StrCmp $1 "" FindJDK64_2 FoundJava

  ; JDK 9.0.1 registry entries are in Software\JavaSoft\JDK:
  FindJDK64_2:
  ReadRegStr $0 HKLM "Software\JavaSoft\JDK" "CurrentVersion"
  StrCmp $0 "" FindJRE32
  ReadRegStr $1 HKLM "Software\JavaSoft\JDK\$0" "JavaHome"
  StrCmp $1 "" FindJRE32 FoundJava

  ; 32 bit JRE
  FindJRE32:
  SetRegView 32
  ReadRegStr $0 HKLM "Software\JavaSoft\Java Runtime Environment" "CurrentVersion"
  StrCmp $0 "" FindJDK32
  ReadRegStr $1 HKLM "Software\JavaSoft\Java Runtime Environment\$0" "JavaHome"
  StrCmp $1 "" FindJDK32 FoundJava

  ; 32 bit JDK
  FindJDK32:
  ReadRegStr $0 HKLM "Software\JavaSoft\Java Development Kit" "CurrentVersion"
  StrCmp $0 "" NoJava
  ReadRegStr $1 HKLM "Software\JavaSoft\Java Development Kit\$0" "JavaHome"
  StrCmp $1 "" NoJava FoundJava

  NoJava:
  MessageBox MB_OK "Could not find Java runtime environment! Please install Java."
  Abort

  FoundJava:
  StrCpy $JavaExe "$1\bin\javaw.exe"

FunctionEnd

Function StartChunky
  ExecShell "" "$SMPROGRAMS\Chunky\Chunky.lnk"
FunctionEnd

Section "Chunky (required)" SecChunky

  SectionIn RO

  ; Set destination directory
  SetOutPath $INSTDIR

  File /oname=chunky.jar build\chunky-@VERSION@.jar
  File build\ReadMe.html
  File /oname=LICENSE.txt LICENSE
  File build\release_notes-@VERSION@.txt
  File dist\chunky.ico

  ; Write install dir to registry
  WriteRegStr HKLM "Software\Chunky" "Install_Dir" "$INSTDIR"

  ; Write Windows uninstall keys
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Chunky" "DisplayName" "Chunky"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Chunky" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Chunky" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Chunky" "NoRepair" 1
  WriteUninstaller "Uninstall.exe"

SectionEnd

Section "Start Menu Shortcuts" SecSM

  WriteINIStr "$INSTDIR\Wiki.URL" "InternetShortcut" "URL" "http://chunky.llbit.se"

  CreateDirectory "$SMPROGRAMS\Chunky"

  ; Default Chunky Shortcut
  ;;;;CreateShortCut "$SMPROGRAMS\Chunky\Chunky.lnk" "$INSTDIR\chunky.jar" "" "$INSTDIR\chunky.ico"
  CreateShortCut "$SMPROGRAMS\Chunky\Chunky.lnk" "$JavaExe" "-jar $\"$INSTDIR\chunky.jar$\"" "$INSTDIR\chunky.ico"
  CreateShortCut "$SMPROGRAMS\Chunky\ReadMe.lnk" "$INSTDIR\ReadMe.html"
  CreateShortCut "$SMPROGRAMS\Chunky\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortCut "$SMPROGRAMS\Chunky\Wiki.lnk" "$INSTDIR\Wiki.URL"

  ; Remove more memory shortcut
  Delete "$SMPROGRAMS\Chunky\Chunky (more memory).lnk"

  ; Launcher Shortcut
  CreateShortCut "$SMPROGRAMS\Chunky\Chunky (Launcher).lnk" "$JavaExe" "-jar $\"$INSTDIR\chunky.jar$\" --launcher" "$INSTDIR\chunky.ico"

SectionEnd

;Descriptions

  ;Language strings
  LangString DESC_SecChunky ${LANG_ENGLISH} "Installs Chunky"
  LangString DESC_SecSM ${LANG_ENGLISH} "Adds shortcuts to your start menu"

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecChunky} $(DESC_SecChunky)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecSM} $(DESC_SecSM)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller

Section "Uninstall"

  ; Delete reg keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Chunky"
  DeleteRegKey HKLM SOFTWARE\Chunky

  ; Delete installed files
  Delete $INSTDIR\chunky.jar
  Delete $INSTDIR\chunky.ico
  Delete $INSTDIR\ReadMe.html
  Delete $INSTDIR\LICENSE.txt
  Delete "$INSTDIR\*.txt"
  Delete "$INSTDIR\*.URL"
  Delete $INSTDIR\Uninstall.exe

  ; Delete shortcuts
  Delete "$SMPROGRAMS\Chunky\*.lnk"

  ; Remove directories used
  RMDir "$SMPROGRAMS\Chunky"
  RMDir "$INSTDIR"

SectionEnd
