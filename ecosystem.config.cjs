module.exports = {
  apps: [
    {
      name: 'paper-lib-backend',
      cwd: '/home/huapad/paper-lib',
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
      cwd: '/home/huapad/paper-lib',
      script: 'run-frontend.sh',
      interpreter: 'bash',
      env: {
        NODE_ENV: 'development'
      },
      autorestart: true,
      max_restarts: 999,
      restart_delay: 3000,
      min_uptime: '10s',
      max_memory_restart: '500M'
    }
  ]
};
