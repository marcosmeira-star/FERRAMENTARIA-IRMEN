# Ferramentaria Irmen (Desktop Windows)

## Estrutura
- `backend/`: FastAPI + SQLModel + SQLite local.
- `frontend/`: HTML/CSS/JS da interface.
- `desktop/`: Electron + electron-builder (NSIS).

## Execução (desenvolvimento)
### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Desktop
```bash
cd desktop
npm install
npm start
```

## Build Windows
### 1) Gerar backend.exe
```powershell
./build-backend.ps1
```
Saída esperada: `backend/dist/backend.exe`.

### 2) Gerar instalador desktop
```powershell
./build-desktop.ps1
```
Saída esperada: `desktop/release/*.exe`.

### 3) Pipeline completo
```powershell
./build-all.ps1
```

## Instalação
1. Execute o instalador em `desktop/release`.
2. Conclua o assistente NSIS.
3. Abra pelo atalho da área de trabalho.

## Checklist funcional
- Dashboard
- Clientes (cadastro/listagem/ativação)
- Ferramentas (cadastro/listagem/ativação)
- Empréstimos com baixa de saldo
- Devoluções parcial/total
- Histórico de movimentações


### Ícone customizado (opcional, sem versionar binário)
No Windows/PowerShell, antes de rodar `./build-desktop.ps1`:
```powershell
$env:APP_ICON_PATH="C:\icons\app.ico"
./build-desktop.ps1
```
Se não definir, o build usa o ícone padrão do Electron Builder.
