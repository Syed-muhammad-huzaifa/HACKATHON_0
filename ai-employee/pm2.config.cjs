module.exports = {
  apps: [{
    name: 'ai-watcher',
    script: '/home/syedhuzaifa/.local/bin/uv',
    args: 'run ai-watch',
    cwd: '/home/syedhuzaifa/final_hackthon_0/ai-employee',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: './src',
      VAULT_PATH: '/mnt/c/AI_Hackthon',
      CLAUDE_ENTRY: 'ccr',
      CLAUDE_MODE: 'code',
      CLAUDE_TIMEOUT_SECONDS: '180'
    }
  }, {
    name: 'ai-orchestrator',
    script: '/home/syedhuzaifa/.local/bin/uv',
    args: 'run ai-orchestrate',
    cwd: '/home/syedhuzaifa/final_hackthon_0/ai-employee',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: './src',
      VAULT_PATH: '/mnt/c/AI_Hackthon',
      CLAUDE_ENTRY: 'ccr',
      CLAUDE_MODE: 'code',
      CLAUDE_TIMEOUT_SECONDS: '180'
    }
  }]
};
