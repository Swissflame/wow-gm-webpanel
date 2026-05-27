param(
  [string]$HostName = "192.168.1.54",
  [string]$User = "Klaus",
  [Parameter(Mandatory=$true)][string]$Password,
  [string]$HostKey = ""
)
$ErrorActionPreference = "Stop"
$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp = "C:\Program Files\PuTTY\pscp.exe"
if (!(Test-Path $plink) -or !(Test-Path $pscp)) { throw "PuTTY plink/pscp nicht gefunden." }
$archive = Join-Path $env:TEMP "wow-gm-webpanel.tar.gz"
if (Test-Path $archive) { Remove-Item $archive -Force }
tar --exclude='.git' --exclude='.venv' --exclude='.env' --exclude='instance' --exclude='backups' --exclude='exports' -czf $archive .
$hostKeyArgs = @()
if ($HostKey) { $hostKeyArgs = @("-hostkey", $HostKey) }
& $plink -ssh "$User@$HostName" -pw $Password -batch @hostKeyArgs "rm -rf /tmp/wow-gm-webpanel && mkdir -p /tmp/wow-gm-webpanel"
& $pscp -pw $Password -batch @hostKeyArgs $archive "$User@$HostName`:/tmp/wow-gm-webpanel/app.tar.gz"
& $plink -ssh "$User@$HostName" -pw $Password -batch @hostKeyArgs "cd /tmp/wow-gm-webpanel && tar -xzf app.tar.gz && echo '$Password' | sudo -S bash scripts/install_ubuntu.sh"
