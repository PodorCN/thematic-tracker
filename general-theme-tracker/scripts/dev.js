// Start backend (:8787) and frontend (Vite) together.
// CLI --port/--host flags only forward to the frontend; the backend port stays fixed to avoid conflicts.
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
