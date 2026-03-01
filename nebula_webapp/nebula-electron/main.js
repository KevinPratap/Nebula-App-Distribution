const electron = require('electron');
const { app, BrowserWindow, ipcMain, globalShortcut, Menu, Tray, nativeImage, dialog, screen } = electron;
const { join, dirname } = require('path');
const { spawn } = require('child_process');
const { readFileSync } = require('fs');

let mainWindow = null;
let sidecarProcess = null;
let tray = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 830,
        height: 600,
        show: false,
        autoHideMenuBar: true,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: false,
        maximizable: false,
        fullscreenable: false,
        icon: join(__dirname, 'public/logo.png'),
        webPreferences: {
            preload: join(__dirname, 'preload.js'),
            sandbox: false,
            contextIsolation: true
        }
    });

    const devUrl = 'http://localhost:5173';
    const isDev = !app.isPackaged;

    const loadWithRetry = (url, attempts = 0) => {
        const loadPromise = isDev
            ? mainWindow.loadURL(url)
            : mainWindow.loadFile(join(__dirname, 'dist', 'index.html'));

        loadPromise.then(() => {
            console.log(`Successfully loaded UI`);
            mainWindow.show();
            console.log('Main: Window should be visible now. isVisible:', mainWindow.isVisible());
            mainWindow.focus();
        }).catch(e => {
            if (isDev && attempts < 20) {
                console.log(`Failed to load dev URL, retrying in 1s... (${attempts + 1}/20)`);
                setTimeout(() => loadWithRetry(url, attempts + 1), 1000);
            } else {
                console.error(`Failed to load UI:`, e);
            }
        });
    };

    loadWithRetry(devUrl);

    createTray();
    registerShortcuts();
    startSidecar();
}

function createTray() {
    const iconPath = join(__dirname, 'public/logo.png');
    const icon = nativeImage.createFromPath(iconPath);
    tray = new Tray(icon.resize({ width: 20, height: 20 }));

    const contextMenu = Menu.buildFromTemplate([
        { label: 'Show Assistant', click: () => mainWindow?.show() },
        { label: 'Hide Assistant', click: () => mainWindow?.hide() },
        { type: 'separator' },
        { label: 'Quit', click: () => app.quit() }
    ]);

    tray.setToolTip('Nebula Assistant');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow?.show();
            mainWindow?.focus();
        }
    });

    tray.on('double-click', () => {
        mainWindow?.show();
        mainWindow?.focus();
    });
}

function registerShortcuts(key = 'F2') {
    globalShortcut.unregisterAll();

    // Alt+Space: Show/Hide Toggle
    globalShortcut.register('Alt+Space', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow?.show();
            mainWindow?.focus();
        }
    });

    if (!key) return;

    try {
        const success = globalShortcut.register(key, () => {
            mainWindow?.webContents.send('hotkey-triggered');
        });
        if (!success) {
            console.error(`Main: Failed to register hotkey: ${key}`);
            mainWindow?.webContents.send('status-received', { msg: `HOTKEY ${key} IN USE`, is_error: true });
        } else {
            console.log(`Main: Registered activation hotkey: ${key}`);
        }
    } catch (e) {
        console.error("Hotkey registration exception:", e);
    }

    // --- Window Positioning Shortcuts (v51.29) ---
    globalShortcut.register('Alt+Shift+1', () => repositionWindow('top'));
    globalShortcut.register('Alt+Shift+2', () => repositionWindow('middle'));
    globalShortcut.register('Alt+Shift+3', () => repositionWindow('bottom'));
}

function repositionWindow(zone) {
    if (!mainWindow) return;
    const { width: winWidth, height: winHeight } = mainWindow.getBounds();
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: scrWidth, height: scrHeight } = primaryDisplay.workAreaSize;

    const x = Math.floor((scrWidth - winWidth) / 2);
    let y = 0;

    if (zone === 'top') {
        y = 20; // 20px gap from top v51.31
    } else if (zone === 'middle') {
        y = Math.floor((scrHeight - winHeight) / 2);
    } else if (zone === 'bottom') {
        y = Math.floor(scrHeight - winHeight - 40); // 40px margin from bottom
    }

    mainWindow.setPosition(x, y, true);
    console.log(`Main: Repositioned window to ${zone} -> [${x}, ${y}]`);
}

function startSidecar() {
    const rootDir = __dirname;
    let pythonPath;
    let scriptPath;
    let args;

    if (app.isPackaged) {
        pythonPath = join(process.resourcesPath, 'engine_sidecar.exe');
        scriptPath = ''; // Not needed for EXE
        args = [];
    } else {
        pythonPath = join(rootDir, '.venv/Scripts/python.exe');
        scriptPath = join(rootDir, 'engine_sidecar.py');
        args = [scriptPath];
    }

    console.log(`Main: Starting sidecar from ${pythonPath}`);

    sidecarProcess = spawn(pythonPath, args, {
        cwd: rootDir,
        env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONHTTPSVERIFY: '0' },
        windowsHide: true
    });

    sidecarProcess.on('error', (err) => {
        console.error('Failed to start sidecar:', err);
    });

    sidecarProcess.on('exit', (code, signal) => {
        console.error(`Sidecar Process exited with code ${code} and signal ${signal}`);
        if (mainWindow && !mainWindow.isDestroyed() && mainWindow.webContents) {
            mainWindow.webContents.send('error-received', { msg: 'AI Engine Disconnected' });
        }
    });

    let sidecarBuffer = '';
    sidecarProcess.stdout.on('data', (data) => {
        sidecarBuffer += data.toString();
        const lines = sidecarBuffer.split('\n');

        // Keep the last partial line in the buffer
        sidecarBuffer = lines.pop();

        lines.filter(l => l.trim()).forEach(line => {
            try {
                const json = JSON.parse(line);
                if (json.type !== 'volume') {
                    console.log(`Main: Routing ${json.type} to UI`);
                }
                mainWindow?.webContents.send(`${json.type}-received`, json.payload);
            } catch (e) {
                // If it's not JSON, it's a debug log
                console.log('Sidecar Raw:', line);
            }
        });
    });

    sidecarProcess.stderr.on('data', (data) => {
        console.error(`Sidecar Error: ${data}`);
    });

    // Forward Main stdin to Sidecar for manual testing (Diagnostic)
    process.stdin.on('data', (data) => {
        if (sidecarProcess) {
            sidecarProcess.stdin.write(data);
        }
    });
}

ipcMain.on('toggle-listening', (_, enabled) => {
    console.log(`Main: Received toggle-listening -> ${enabled}`);
    if (sidecarProcess) {
        console.log(`Main: Sending toggle-listening to sidecar -> ${enabled}`);
        sidecarProcess.stdin.write(JSON.stringify({ action: 'toggle-listening', payload: enabled }) + '\n');
    }
});

ipcMain.handle('get-platform', () => {
    console.log('Main: IPC [get-platform] invoke');
    return process.platform;
});

ipcMain.on('set-opacity', (_, level) => {
    if (mainWindow) {
        mainWindow.setOpacity(level / 255);
    }
});

ipcMain.on('update-stealth', (_, enabled) => {
    if (mainWindow) {
        mainWindow.setContentProtection(enabled);
        mainWindow.setSkipTaskbar(enabled);
    }
});

ipcMain.on('re-register-hotkey', (_, key) => {
    registerShortcuts(key);
});

ipcMain.handle('open-file-dialog', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog({
        properties: ['openFile'],
        filters: [{ name: 'Documents', extensions: ['txt', 'pdf', 'doc', 'docx'] }]
    });
    if (!canceled && filePaths.length > 0) {
        const filePath = filePaths[0];
        const ext = filePath.split('.').pop().toLowerCase();

        if (ext === 'txt') {
            try {
                return readFileSync(filePath, 'utf-8');
            } catch (e) {
                console.error("Main: File read error:", e);
                return null;
            }
        } else {
            // PDF or Word — let sidecar handle it
            console.log(`Main: Delegating binary parsing for: ${filePath}`);
            return { type: 'link', path: filePath };
        }
    }
    return null;
});

ipcMain.on('send-to-sidecar', (_, { action, payload }) => {
    console.log(`Main: IPC [send-to-sidecar] action=${action}`);
    if (sidecarProcess && sidecarProcess.stdin.writable) {
        console.log(`Main: Routing ${action} to sidecar`);
        const msg = JSON.stringify({ action, payload }) + '\n';
        sidecarProcess.stdin.write(msg);
    } else {
        console.error(`Main: Cannot send ${action}, sidecar not available`);
    }
});

ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    win?.setIgnoreMouseEvents(ignore, options);
});

let isDrawerOpen = false;
let mouseMonitorInterval = null;

ipcMain.on('set-drawer-status', (_, open) => {
    isDrawerOpen = open;
});

function startMouseMonitor() {
    if (mouseMonitorInterval) clearInterval(mouseMonitorInterval);

    mouseMonitorInterval = setInterval(() => {
        if (!mainWindow || mainWindow.isDestroyed() || !mainWindow.isVisible()) return;

        try {
            const point = screen.getCursorScreenPoint();
            const bounds = mainWindow.getBounds();

            const isWithinWin = (
                point.x >= bounds.x &&
                point.x <= bounds.x + bounds.width &&
                point.y >= bounds.y &&
                point.y <= bounds.y + bounds.height
            );

            if (!isWithinWin) {
                if (mainWindow.isIgnored !== true) {
                    mainWindow.setIgnoreMouseEvents(true, { forward: true });
                    mainWindow.isIgnored = true;
                }
                return;
            }

            const rx = point.x - bounds.x;
            const ry = point.y - bounds.y;

            // V33.5: Expanded Hit zones to include sub-pill stack (ry <= 150)
            const overPill = (rx >= 0 && rx <= 830 && ry >= 0 && ry <= 150);
            const overDrawer = isDrawerOpen && (ry > 150);

            if (overPill || overDrawer) {
                if (mainWindow.isIgnored !== false) {
                    mainWindow.setIgnoreMouseEvents(false);
                    mainWindow.isIgnored = false;
                }
            } else {
                if (mainWindow.isIgnored !== true) {
                    mainWindow.setIgnoreMouseEvents(true, { forward: true });
                    mainWindow.isIgnored = true;
                }
            }
        } catch (e) {
            console.error("Mouse monitor error:", e);
        }
    }, 100);
}

app.whenReady().then(() => {
    createWindow();
    startMouseMonitor();
});

app.on('will-quit', () => {
    if (mouseMonitorInterval) clearInterval(mouseMonitorInterval);
    globalShortcut.unregisterAll();
    if (sidecarProcess) sidecarProcess.kill();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
