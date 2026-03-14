/**
 * VS Code Viewer Component
 *
 * Embeds VS Code Server in an iframe
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Tooltip,
  Tabs,
  Input,
  Select,
  Modal,
  message,
  Badge,
  Typography,
  Alert,
  Spin,
  Divider,
} from 'antd';
import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  ExpandOutlined,
  FolderOpenOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useIDEStore } from '@/stores/ide';
import { VSCodeInstance, POPULAR_EXTENSIONS } from '@/types/ide';
import TerminalPanel from './TerminalPanel';
import styles from './VSCodeViewer.module.scss';

const { Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

interface VSCodeViewerProps {
  instance: VSCodeInstance;
  onClose: () => void;
}

const VSCodeViewer: React.FC<VSCodeViewerProps> = ({ instance, onClose }) => {
  const { installExtension, startVSCodeInstance, stopVSCodeInstance } = useIDEStore();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState('editor');
  const [isExtensionModalVisible, setIsExtensionModalVisible] = useState(false);
  const [selectedExtension, setSelectedExtension] = useState<string | null>(null);
  const [installingExtension, setInstallingExtension] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Auto-start instance if not running
  useEffect(() => {
    if (instance.status === 'stopped') {
      startVSCodeInstance(instance.id);
    }
  }, [instance.id, instance.status, startVSCodeInstance]);

  const handleToggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    if (!isFullscreen && iframeRef.current) {
      iframeRef.current.requestFullscreen();
    }
  };

  const handleReload = () => {
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const handleOpenInNewTab = () => {
    window.open(instance.url, '_blank');
  };

  const handleInstallExtension = async () => {
    if (!selectedExtension) {
      message.warning('Please select an extension');
      return;
    }

    setInstallingExtension(true);
    try {
      await installExtension(instance.id, selectedExtension);
      message.success('Extension installed successfully');
      setIsExtensionModalVisible(false);
      setSelectedExtension(null);
      handleReload();
    } catch (error: any) {
      message.error(error.message || 'Failed to install extension');
    } finally {
      setInstallingExtension(false);
    }
  };

  const isRunning = instance.status === 'running';
  const extensionCount = instance.extensions?.length || 0;

  return (
    <div className={styles.vscodeViewer}>
      {/* Toolbar */}
      <div className={styles.toolbar}>
        <Space>
          <Text strong>VS Code</Text>
          <Tag color={isRunning ? 'success' : 'warning'}>
            {instance.status.toUpperCase()}
          </Tag>
          {extensionCount > 0 && (
            <Tag>{extensionCount} extensions</Tag>
          )}
        </Space>

        <Space>
          <Tooltip title="Install Extension">
            <Button
              type="text"
              icon={<PlusOutlined />}
              onClick={() => setIsExtensionModalVisible(true)}
              disabled={!isRunning}
            >
              Extension
            </Button>
          </Tooltip>
          <Tooltip title="Open in New Tab">
            <Button
              type="text"
              icon={<ExpandOutlined />}
              onClick={handleOpenInNewTab}
            >
              Open
            </Button>
          </Tooltip>
          <Tooltip title="Reload">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={handleReload}
            >
              Reload
            </Button>
          </Tooltip>
          <Tooltip title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}>
            <Button
              type="text"
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={handleToggleFullscreen}
            />
          </Tooltip>
        </Space>
      </div>

      {/* Content */}
      <div className={styles.content}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          className={styles.tabs}
        >
          <TabPane
            tab={
              <span>
                <FolderOpenOutlined />
                Editor
              </span>
            }
            key="editor"
          >
            {!isRunning ? (
              <div className={styles.loadingContainer}>
                <Spin size="large" tip="Starting VS Code Server..." />
              </div>
            ) : (
              <iframe
                ref={iframeRef}
                src={instance.url}
                className={styles.editorFrame}
                title="VS Code Editor"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
              />
            )}
          </TabPane>

          <TabPane
            tab={
              <span>
                <ThunderboltOutlined />
                Terminal
              </span>
            }
            key="terminal"
          >
            <TerminalPanel notebookId={instance.notebook_id} />
          </TabPane>

          <TabPane
            tab={
              <span>
                <SettingOutlined />
                Settings
              </span>
            }
            key="settings"
          >
            <div className={styles.settingsPanel}>
              <Card title="Instance Information" size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">Instance ID:</Text>
                    <Text code>{instance.id}</Text>
                  </div>
                  <div>
                    <Text type="secondary">URL:</Text>
                    <Text code copyable>{instance.url}</Text>
                  </div>
                  <div>
                    <Text type="secondary">Port:</Text>
                    <Text>{instance.port}</Text>
                  </div>
                  <div>
                    <Text type="secondary">Workspace:</Text>
                    <Text>{instance.workspace_path || '/default'}</Text>
                  </div>
                  <div>
                    <Text type="secondary">Created:</Text>
                    <Text>{new Date(instance.created_at).toLocaleString()}</Text>
                  </div>
                </Space>
              </Card>

              <Card title="Installed Extensions" size="small">
                {instance.extensions && instance.extensions.length > 0 ? (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {instance.extensions.map((ext, index) => (
                      <Tag key={index} closable>
                        {ext}
                      </Tag>
                    ))}
                  </Space>
                ) : (
                  <Text type="secondary">No extensions installed</Text>
                )}
              </Card>

              <Alert
                message="VS Code Server"
                description="This is a web-based version of Visual Studio Code running in the browser. It provides most of the features of the desktop application including extensions, themes, and IntelliSense."
                type="info"
                showIcon
              />
            </div>
          </TabPane>
        </Tabs>
      </div>

      {/* Extension Installation Modal */}
      <Modal
        title="Install Extension"
        open={isExtensionModalVisible}
        onOk={handleInstallExtension}
        onCancel={() => {
          setIsExtensionModalVisible(false);
          setSelectedExtension(null);
        }}
        okText="Install"
        okButtonProps={{ loading: installingExtension }}
      >
        <Select
          showSearch
          style={{ width: '100%' }}
          placeholder="Search for an extension"
          value={selectedExtension}
          onChange={setSelectedExtension}
          options={POPULAR_EXTENSIONS.map((ext) => ({
            label: `${ext.name} - ${ext.description}`,
            value: ext.id,
          }))}
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
        />
        <Divider />
        <Text type="secondary">
          Popular extensions include Python, Jupyter, ESLint, Prettier, GitLens, and more.
        </Text>
      </Modal>
    </div>
  );
};

export default VSCodeViewer;
