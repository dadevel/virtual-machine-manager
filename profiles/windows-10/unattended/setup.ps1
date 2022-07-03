F:\spice_guest_tools.exe

# install winget
# download url: https://github.com/microsoft/winget-cli/releases/download/v1.2.10271/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle
#Invoke-WebRequest https://aka.ms/getwinget -OutFile $env:TMP/AppInstaller.msixbundle 
#Add-AppxPackage $env:TMP/AppInstaller.msixbundle
#Remove-Item -Path $env:TMP/AppInstaller.msixbundle

#winget install -e --id vim.vim
# install neovim, https://github.com/neovim/neovim/releases
#curl.exe -Lo nvim.msi https://github.com/neovim/neovim/releases/download/v0.7.0/nvim-win64.msi
#msiexec nvim.msi

# install visual studio
#winget install -e --id Microsoft.VisualStudio.2022.Community

#winget install -e --id Git.Git
#winget install -e --id GitHub.GitLFS

# install 7zip, https://www.7-zip.org/
#curl.exe -Lo 7z.msi https://www.7-zip.org/a/7z2107-x64.msi
#msiexec 7z.msi

# sysinternals
#winget install sysinternals --accept-package-agreements
#curl.exe -Lo procmon.zip https://download.sysinternals.com/files/ProcessMonitor.zip
#curl.exe -Lo sysmon.zip https://download.sysinternals.com/files/Sysmon.zipp
#curl.exe -Lo procexp.zip https://download.sysinternals.com/files/ProcessExplorer.zip
#Expand-Archive ./procmon.zip -DestinationPath ./procmon
#Move-Item ./procmon/procmon.exe PATH\
#Expand-Archive ./sysmon.zip -DestinationPath ./sysmon
#Move-Item ./sysmon/sysmon.exe PATH\
#Expand-Archive ./procexp.zip -DestinationPath ./procexp
#Move-Item ./procexp/procexp.exe PATH\

#winget install -e --id Microsoft.WindowsTerminal
#winget install -e --id Microsoft.PowerShell
#winget install -e --id Microsoft.VisualStudioCode

# disable hibernation
#POWERCFG -H OFF

# disable defender via local group policy
#New-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender" -Name DisableAntiSpyware -Value 1 -PropertyType DWORD -Force
#gpupdate /force

# setup ssh
#Add-WindowsCapability -Online -Name OpenSSH.Client
#Add-WindowsCapability -Online -Name OpenSSH.Server
#New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -PropertyType String -Force
#mkdir ~/.ssh
#echo TODO > ~/.ssh/authorized_keys
#echo TODO > C:/ProgramData/ssh/administrators_authorized_keys
## fix permissions
#icacls.exe C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant Administrators:F /grant SYSTEM:F
#Set-Service -Name sshd -StartupType Automatic
#Restart-Service sshd

# install windows terminal
#curl.exe -Lo ./Microsoft.WindowsTerminal.msixbundle 'https://github.com/microsoft/terminal/releases/download/v1.13.10983.0/Microsoft.WindowsTerminalPreview_Win10_1.13.10983.0_8wekyb3d8bbwe.msixbundle'
#Add-AppxPackage ./Microsoft.WindowsTerminal.msixbundle

# $Host.UI.RawUI.WindowTitle = 'Installing updates...'
# Get-WUInstall -AcceptAll -IgnoreReboot
# if (Get-WURebootStatus -Silent) {
#     $Host.UI.RawUI.WindowTitle = 'Updates installation finished. Rebooting.'
#     shutdown /r /t 0
# }

# $Host.UI.RawUI.WindowTitle = 'Disabling autologin...'
# Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -Name Unattend*
# Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name AutoLogonCount

# $Host.UI.RawUI.WindowTitle = 'Installing virtio drivers...'
# $iso = Get-WmiObject win32_cdromdrive | Where-Object { $_.volumename -like 'virtio-win*' }
# $drivers = Get-ChildItem -Path $iso.drive -Recurse -Include '*.inf'
# ForEach ($driver in $drivers) {
#     pnputil.exe -i -a $driver.FullName
#     # pnputil.exe /add-driver $driver.FullName /install
# }

# $Host.UI.RawUI.WindowTitle = 'Installing virtio guest tools...'
# #Start-Process msiexec -ArgumentList "/I $($iso.drive)\guest-tools\qemu-ga-x86_64.msi /qn /norestart" -Wait -NoNewWindow
# #msiexec /i e:\virtio-win-gt-x64.msi /qn /passive
# msiexec /i e:\guest-agent\qemu-ga-x86_64.msi /qn /passive

# $Host.UI.RawUI.WindowTitle = 'Customizing...'

# enable rdp
# Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -value 0
# Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# $Host.UI.RawUI.WindowTitle = 'Running sysprep...'
# C:\Windows\System32\Sysprep\Sysprep.exe /generalize /oobe /shutdown /unattend:C:\Windows\Temp\Unattend.xml
