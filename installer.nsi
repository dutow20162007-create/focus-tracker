!define APP_NAME "Focus Tracker"
!define EXE_NAME "FocusTracker.exe"
!ifndef VERSION
  !define VERSION "1.0.0"
!endif

Name "${APP_NAME}"
OutFile "FocusTrackerSetup.exe"
InstallDir "$LOCALAPPDATA\FocusTracker"
RequestExecutionLevel user
Unicode true
SetCompressor /SOLID lzma

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File "dist-win\${EXE_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FocusTracker" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FocusTracker" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FocusTracker" "UninstallString" "$INSTDIR\Uninstall.exe"
  Exec '"$INSTDIR\${EXE_NAME}"'
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\${EXE_NAME}"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FocusTracker"
SectionEnd
