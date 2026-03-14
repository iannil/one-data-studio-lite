# One Data Studio Lite - Jupyter Lab Configuration

c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.open_browser = False
c.ServerApp.allow_root = True

# Allow any origin
c.ServerApp.allow_origin = '*'
c.ServerApp.allow_remote_access = True

# Disable token authentication in favor of platform auth
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.disable_check_xsrf = True

# Enable extensions
c.ExtensionApp.open_browser = False

# File manager settings
c.FileContentsManager.delete_to_trash = False
c.ContentsManager.hide_globs = ['__pycache__', '*.pyc', '.git', '.ipynb_checkpoints']

# Code formatter settings
c.CodeFormatter.formatters = {
    'python': ['black']
}

# LSP settings
c.LabServerApp.extra_labextensions_path = ['/usr/local/share/jupyter/labextensions']

# CPU/Memory limits
c.ResourceUtilization.track_cpu_percent = True
c.ResourceUtilization.cpu_limit = 2.0
c.ResourceUtilization.mem_limit = 4000000000

# Kernel settings
c.MappingKernelManager.default_kernel_name = 'python3'
c.MappingKernelManager.cull_idle_timeout = 3600
c.MappingKernelManager.cull_interval = 300
c.MappingKernelManager.cull_connected = True

# Notebook settings
c.NotebookApp.max_body_size = 100 * 1024 * 1024  # 100MB
c.NotebookApp.max_message_size = 100 * 1024 * 1024

# Execution settings
c.ExecutePreprocessor.timeout = 600
c.ExecutePreprocessor.interrupt_on_timeout = True

# MathJax settings
c.NotebookApp.mathjax_url = 'https://cdn.jsdelivr.net/npm/mathjax@2/MathJax.js?config=TeX-AMS-MML_HTMLorMML-full'

# Template settings
c.JupyterLabTemplate.template_dirs = ['/usr/local/share/jupyter/lab/templates']

# Workspaces
c.WorkspaceManager.max_notebook_instances = 10
c.WorkspaceManager.max_workspace_instances = 5

# Logging
c.ServerApp.log_level = 'INFO'
c.Application.log_format = '[%(name)s]%(highlevelname)s %(message)s'
