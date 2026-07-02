const path = require('path');

const CWD = path.resolve(__dirname);

module.exports = {
  apps: [
    {
      name: 'paper-lib-backend',
      cwd: CWD,
      script: 'run-backend.sh',
      interpreter: 'bash',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      autorestart: true,
      max_restarts: 999,
      restart_delay: 3000,
      min_uptime: '10s',
      max_memory_restart: '500M'
    },
    {
      name: 'paper-lib-frontend',
      cwd: CWD,
      script: 'run-frontend.sh',
      interpreter: 'bash',
      env: {
        NODE_ENV: 'development',
        API_TARGET: 'http://10.8.8.28:9000',
        PORT: '3000'
      },
      autorestart: true,
      max_restarts: 999,
      restart_delay: 3000,
      min_uptime: '10s',
      max_memory_restart: '500M'
    }
  ]
};
