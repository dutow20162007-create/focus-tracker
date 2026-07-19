!define APP_NAME "dash focus-tracker"
!define EXE_NAME "DashFocusTracker.exe"
!ifndef VERSION
  !define VERSION "1.2.0"
!endif

Name "${APP_NAME}"
OutFile "DashFocusTrackerSetup.exe"
InstallDir "$LOCALAPPDATA\DashFocusTracker"
RequestExecutionLevel user
Unicode true
SetCompressor /SOLID lzma
Icon "assets\logo.ico"

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File "dist-win\${EXE_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DashFocusTracker" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DashFocusTracker" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DashFocusTracker" "UninstallString" "$INSTDIR\Uninstall.exe"
  Exec '"$INSTDIR\${EXE_NAME}"'
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\${EXE_NAME}"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DashFocusTracker"
SectionEnd
