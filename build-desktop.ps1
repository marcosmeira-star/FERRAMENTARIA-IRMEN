Set-Location $PSScriptRoot\desktop

# Opcional: usar ícone local sem versionar binário no git
# Exemplo:
#   $env:APP_ICON_PATH="C:\\icons\\app.ico"
# Se definido e o arquivo existir, aplica no package.json antes do build.
if ($env:APP_ICON_PATH -and (Test-Path $env:APP_ICON_PATH)) {
  $pkg = Get-Content package.json -Raw | ConvertFrom-Json
  if (-not $pkg.build.win) { $pkg.build | Add-Member -Name win -MemberType NoteProperty -Value @{} }
  $pkg.build.win.icon = $env:APP_ICON_PATH
  $pkg | ConvertTo-Json -Depth 100 | Set-Content package.json -Encoding UTF8
  Write-Host "Ícone customizado aplicado: $env:APP_ICON_PATH"
} else {
  Write-Host "Sem ícone customizado (usando padrão do Electron Builder)."
}

npm install
npm run build
