Set-Location $PSScriptRoot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pyinstaller --onefile --name backend backend\main.py
New-Item -ItemType Directory -Force backend\dist | Out-Null
Copy-Item dist\backend.exe backend\dist\backend.exe -Force
