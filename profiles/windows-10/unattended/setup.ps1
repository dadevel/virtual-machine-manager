F:\spice_guest_tools.exe

# disable windows telemetry service according to https://www.bsi.bund.de/DE/Service-Navi/Publikationen/Studien/SiSyPHuS_Win10/AP4/SiSyPHuS_AP4_node.html
Get-Service -Name DiagTrack | Stop-Service -PassThru | Set-Service -StartupType Disabled -PassThru
Get-AutologgerConfig -Name Diagtrack-Listener | Set-AutologgerConfig -Start 0 -PassThru

# set visual effects to "adjust for best performance"
New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects' -Name 'VisualFXSetting' -Value 2 -PropertyType 'DWORD'
