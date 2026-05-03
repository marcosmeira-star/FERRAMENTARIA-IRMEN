const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

const API_HOST = '127.0.0.1';
const API_PORT = 8765;
const API_HEALTH = `http://${API_HOST}:${API_PORT}/health`;
let backendProc = null;

function log(msg, err) {
  const suffix = err ? ` :: ${err.message || err}` : '';
  console.log(`[Ferramentaria] ${msg}${suffix}`);
}

function resolveFrontendPath() {
  const filePath = app.isPackaged
    ? path.join(process.resourcesPath, 'frontend', 'index.html')
    : path.join(__dirname, '..', 'frontend', 'index.html');
  log(`caminho resolvido do frontend: ${filePath}`);
  return filePath;
}

function resolveBackendCommand() {
  if (app.isPackaged) {
    const exePath = path.join(process.resourcesPath, 'backend', 'backend.exe');
    log(`caminho resolvido do backend: ${exePath}`);
    return { cmd: exePath, args: [] };
  }
  const backendDir = path.join(__dirname, '..', 'backend');
  const pyEntry = path.join(backendDir, 'main.py');
  log(`caminho resolvido do backend: ${pyEntry}`);
  return { cmd: 'python', args: [pyEntry] };
}

async function waitBackend(timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(API_HEALTH);
      if (response.ok) return true;
    } catch (_) {
      // retry
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function startBackend() {
  const { cmd, args } = resolveBackendCommand();
  backendProc = spawn(cmd, args, {
    cwd: path.join(__dirname, '..', 'backend'),
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  backendProc.stdout.on('data', (d) => log(`backend stdout: ${d.toString().trim()}`));
  backendProc.stderr.on('data', (d) => log(`backend stderr: ${d.toString().trim()}`));
  backendProc.on('error', (e) => log('falha ao iniciar backend', e));
  backendProc.on('exit', (code) => log(`backend finalizado com código ${code}`));
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    show: false,
    webPreferences: { contextIsolation: true },
  });

  const backendReady = await waitBackend();
  if (!backendReady) {
    log('falha de conexão com a API');
    await win.loadURL('data:text/html,<h2>Falha ao conectar ao backend. Reinicie o aplicativo.</h2>');
    win.show();
    return;
  }

  const frontendPath = resolveFrontendPath();
  try {
    await win.loadFile(frontendPath);
    win.show();
  } catch (e) {
    log('falha ao carregar frontend', e);
    await win.loadURL('data:text/html,<h2>Falha ao carregar interface.</h2>');
    win.show();
  }
}

const singleLock = app.requestSingleInstanceLock();
if (!singleLock) {
  app.quit();
} else {
  app.on('second-instance', () => log('segunda instância bloqueada'));
  app.whenReady().then(async () => {
    startBackend();
    await createWindow();
  });
  app.on('window-all-closed', () => {
    if (backendProc) backendProc.kill();
    if (process.platform !== 'darwin') app.quit();
  });
}
