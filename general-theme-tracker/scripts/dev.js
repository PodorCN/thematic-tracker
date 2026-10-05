// 同时启动 backend (:8787) 与 frontend (Vite)。
// CLI 的 --port/--host 参数只转发给前端；backend 端口固定，避免冲突。
const { spawn } = require('child_process');
const path = require('path');

const extra = process.argv.slice(2); // e.g. --port 7100
const root = path.join(__dirname, '..');

const backend = spawn(process.execPath, [path.join(root, 'backend', 'server.js')], {
  stdio: 'inherit',
});

const frontend = spawn('npm', ['run', 'dev', '--', ...extra], {
  cwd: path.join(root, 'frontend'),
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

let shuttingDown = false;
function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  backend.kill('SIGTERM');
  frontend.kill('SIGTERM');
  setTimeout(() => process.exit(0), 300);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
backend.on('exit', shutdown);
frontend.on('exit', shutdown);
