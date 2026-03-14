/**
 * IDE Type Definitions
 */

export enum IDEType {
  JUPYTER = 'jupyter',
  VSCODE = 'vscode',
  VSCODE_INSIDERS = 'vscode-insiders',
}

export enum VSCodeStatus {
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPING = 'stopping',
  STOPPED = 'stopped',
  ERROR = 'error',
}

export enum TerminalStatus {
  STARTING = 'starting',
  RUNNING = 'running',
  IDLE = 'idle',
  TERMINATED = 'terminated',
  ERROR = 'error',
}

export interface VSCodeServerConfig {
  version?: string;
  port?: number;
  host?: string;
  without_connection_token?: boolean;
  memory_limit?: string;
  cpu_limit?: string;
  extensions?: string[];
  settings?: Record<string, unknown>;
  enable_password?: boolean;
  password?: string;
  data_dir?: string;
  work_dir?: string;
}

export interface VSCodeInstance {
  id: string;
  notebook_id: number;
  user_id: number;
  status: VSCodeStatus;
  url: string;
  port: number;
  workspace_path?: string;
  created_at: string;
  started_at?: string;
  extensions?: string[];
}

export interface TerminalSession {
  id: string;
  notebook_id: number;
  user_id: number;
  status: TerminalStatus;
  shell: string;
  rows: number;
  cols: number;
  cwd: string;
  created_at: string;
  last_activity: string;
}

export interface TerminalMessage {
  id: string;
  type: string;
  data: string;
  timestamp: string;
}

export interface IDESession {
  id: string;
  notebook_id: number;
  ide_type: IDEType;
  status: string;
  url?: string;
  created_at: string;
}

// IDE Type labels and colors
export const IDE_TYPE_LABELS: Record<IDEType, string> = {
  [IDEType.JUPYTER]: 'Jupyter Lab',
  [IDEType.VSCODE]: 'VS Code',
  [IDEType.VSCODE_INSIDERS]: 'VS Code Insiders',
};

export const IDE_TYPE_COLORS: Record<IDEType, string> = {
  [IDEType.JUPYTER]: '#F37626',
  [IDEType.VSCODE]: '#007ACC',
  [IDEType.VSCODE_INSIDERS]: '#6E3AFF',
};

export const IDE_TYPE_ICONS: Record<IDEType, string> = {
  [IDEType.JUPYTER]: '📓',
  [IDEType.VSCODE]: '💻',
  [IDEType.VSCODE_INSIDERS]: '🚀',
};

// Popular VS Code extensions
export const POPULAR_EXTENSIONS = [
  { id: 'ms-python.python', name: 'Python', description: 'IntelliSense, linting, debugging' },
  { id: 'ms-python.vscode-pylance', name: 'Pylance', description: 'Fast Python language server' },
  { id: 'ms-toolsai.jupyter', name: 'Jupyter', description: 'Jupyter notebook support' },
  { id: 'ms-toolsai.jupyter-keymap', name: 'Jupyter Keymap', description: 'Jupyter keyboard shortcuts' },
  { id: 'ms-toolsai.jupyter-renderers', name: 'Jupyter Renderers', description: 'Notebook renderers' },
  { id: 'ms-vscode.live-server', name: 'Live Server', description: 'Launch local dev server' },
  { id: 'dbaeumer.vscode-eslint', name: 'ESLint', description: 'JavaScript linter' },
  { id: 'esbenp.prettier-vscode', name: 'Prettier', description: 'Code formatter' },
  { id: 'ms-vscode.vscode-typescript-next', name: 'Typecript', description: 'TypeScript language support' },
  { id: 'rust-lang.rust-analyzer', name: 'Rust Analyzer', description: 'Rust language server' },
  { id: 'golang.go', name: 'Go', description: 'Go language support' },
  { id: 'redhat.java', name: 'Java', description: 'Java language support' },
  { id: 'ms-vscode.cpptools', name: 'C/C++', description: 'C++ language support' },
  { id: 'tamasfe.even-better-toml', name: 'Even Better TOML', description: 'TOML language support' },
  { id: 'skylight-g Monaco.monaco-yaml', name: 'YAML', description: 'YAML language support' },
  { id: 'usernamehw.errorlens', name: 'Error Lens', description: 'Inline error display' },
  { id: 'eamodio.gitlens', name: 'GitLens', description: 'Git supercharged' },
  { id: 'pkief.material-icon-theme', name: 'Material Icons', description: 'Material Design Icons' },
  { id: 'zhuangtongfa.material-theme', name: 'One Dark Pro', description: 'One Dark theme' },
  { id: 'github.github-vscode-theme', name: 'GitHub Theme', description: 'GitHub theme' },
];
