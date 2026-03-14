/**
 * IDE Selection and Management Page
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Tag,
  Space,
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
  Alert,
  Tabs,
  List,
  Badge,
  Tooltip,
  message,
  Progress,
  Spin,
} from 'antd';
import {
  LaptopOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  DeleteOutlined,
  ExpandOutlined,
  CodeOutlined,
  TerminalOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useIDEStore } from '@/stores/ide';
import { IDEType, IDE_TYPE_LABELS, IDE_TYPE_ICONS, IDE_TYPE_COLORS, VSCodeStatus, POPULAR_EXTENSIONS } from '@/types/ide';
import VSCodeViewer from '@/components/ide/VSCodeViewer';
import TerminalPanel from '@/components/ide/TerminalPanel';
import styles from './ide.module.scss';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface IDECardProps {
  ideType: IDEType;
  onSelect: (type: IDEType) => void;
}

const IDECard: React.FC<IDECardProps> = ({ ideType, onSelect }) => {
  const config = {
    [IDEType.JUPYTER]: {
      title: 'JupyterLab',
      description: 'Interactive notebook environment with code, markdown, and visualization support.',
      features: ['Interactive Notebooks', 'Rich Visualizations', 'File Browser', 'Python Kernel'],
      icon: '📓',
    },
    [IDEType.VSCODE]: {
      title: 'VS Code',
      description: 'Full-featured code editor with extensions, IntelliSense, and integrated terminal.',
      features: ['Syntax Highlighting', 'Code Completion', 'Integrated Terminal', 'Extension Market'],
      icon: '💻',
    },
    [IDEType.VSCODE_INSIDERS]: {
      title: 'VS Code Insiders',
      description: 'Pre-release version of VS Code with latest features and updates.',
      features: ['Latest Features', 'Early Access', 'All VS Code Features', 'Extension Support'],
      icon: '🚀',
    },
  }[ideType];

  return (
    <Card
      className={styles.ideCard}
      hoverable
      onClick={() => onSelect(ideType)}
      style={{ borderTop: `4px solid ${IDE_TYPE_COLORS[ideType]}` }}
    >
      <div className={styles.ideHeader}>
        <span className={styles.ideIcon}>{config.icon}</span>
        <Title level={4} className={styles.ideTitle}>{config.title}</Title>
      </div>
      <Paragraph className={styles.ideDescription}>{config.description}</Paragraph>
      <div className={styles.ideFeatures}>
        {config.features.map((feature, index) => (
          <Tag key={index} color="blue">{feature}</Tag>
        ))}
      </div>
      <Button type="primary" block icon={<LaptopOutlined />}>
        Open {config.title}
      </Button>
    </Card>
  );
};

interface InstanceCardProps {
  instance: {
    id: string;
    notebook_id: number;
    status: string;
    url: string;
    port: number;
    workspace_path?: string;
    created_at: string;
    started_at?: string;
    extensions?: string[];
  };
  onOpen: (instance: any) => void;
  onStart: (instanceId: string) => void;
  onStop: (instanceId: string) => void;
  onRestart: (instanceId: string) => void;
  onDelete: (instanceId: string) => void;
}

const InstanceCard: React.FC<InstanceCardProps> = ({
  instance,
  onOpen,
  onStart,
  onStop,
  onRestart,
  onDelete,
}) => {
  const getStatusConfig = () => {
    switch (instance.status) {
      case VSCodeStatus.RUNNING:
        return { color: 'success', icon: <CheckCircleOutlined />, text: 'Running' };
      case VSCodeStatus.STARTING:
        return { color: 'processing', icon: <LoadingOutlined />, text: 'Starting...' };
      case VSCodeStatus.STOPPING:
        return { color: 'warning', icon: <LoadingOutlined />, text: 'Stopping...' };
      case VSCodeStatus.STOPPED:
        return { color: 'default', icon: <ExclamationCircleOutlined />, text: 'Stopped' };
      case VSCodeStatus.ERROR:
        return { color: 'error', icon: <ExclamationCircleOutlined />, text: 'Error' };
      default:
        return { color: 'default', icon: null, text: instance.status };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <Card
      className={styles.instanceCard}
      size="small"
      extra={
        <Badge
          status={statusConfig.color as any}
          text={statusConfig.text}
        />
      }
    >
      <div className={styles.instanceInfo}>
        <Text strong>Instance #{instance.id.slice(-8)}</Text>
        <Text type="secondary" className={styles.instanceDetail}>
          Port: {instance.port}
        </Text>
        <Text type="secondary" className={styles.instanceDetail}>
          Created: {new Date(instance.created_at).toLocaleString()}
        </Text>
      </div>

      {instance.extensions && instance.extensions.length > 0 && (
        <div className={styles.extensionsSection}>
          <Text type="secondary" className={styles.extensionsLabel}>
            Extensions ({instance.extensions.length}):
          </Text>
          <div className={styles.extensionsList}>
            {instance.extensions.slice(0, 3).map((ext, i) => (
              <Tag key={i} size="small">{ext}</Tag>
            ))}
            {instance.extensions.length > 3 && (
              <Tag size="small">+{instance.extensions.length - 3}</Tag>
            )}
          </div>
        </div>
      )}

      <Space className={styles.instanceActions}>
        {instance.status === VSCodeStatus.RUNNING ? (
          <>
            <Button
              type="primary"
              size="small"
              icon={<ExpandOutlined />}
              onClick={() => onOpen(instance)}
            >
              Open
            </Button>
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => onStop(instance.id)}
            >
              Stop
            </Button>
          </>
        ) : instance.status === VSCodeStatus.STOPPED || instance.status === VSCodeStatus.ERROR ? (
          <>
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => onStart(instance.id)}
            >
              Start
            </Button>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => onRestart(instance.id)}
            >
              Restart
            </Button>
          </>
        ) : (
          <Button size="small" disabled icon={<LoadingOutlined />}>
            {instance.status}
          </Button>
        )}
        <Button
          size="small"
          danger
          icon={<DeleteOutlined />}
          onClick={() => onDelete(instance.id)}
        >
          Delete
        </Button>
      </Space>
    </Card>
  );
};

const IDEPage: React.FC = () => {
  const {
    vscodeInstances,
    vscodeLoading,
    fetchVSCodeInstances,
    createVSCodeInstance,
    startVSCodeInstance,
    stopVSCodeInstance,
    restartVSCodeInstance,
    deleteVSCodeInstance,
    currentInstance,
    setCurrentInstance,
  } = useIDEStore();

  const [isNewInstanceModalVisible, setIsNewInstanceModalVisible] = useState(false);
  const [selectedNotebookId, setSelectedNotebookId] = useState<number | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchVSCodeInstances();
    // Poll for status updates
    const interval = setInterval(fetchVSCodeInstances, 10000);
    return () => clearInterval(interval);
  }, [fetchVSCodeInstances]);

  const handleSelectIDE = async (ideType: IDEType) => {
    // For now, only VS Code is supported
    if (ideType === IDEType.VSCODE || ideType === IDEType.VSCODE_INSIDERS) {
      setIsNewInstanceModalVisible(true);
    } else {
      message.info('JupyterLab is available through the existing notebook system.');
    }
  };

  const handleCreateInstance = async () => {
    try {
      const values = await form.validateFields();
      const notebookId = values.notebookId || 1; // Default notebook

      const config = {
        version: ideType === IDEType.VSCODE_INSIDERS ? 'insiders' : 'stable',
        extensions: values.extensions || [],
        memory_limit: values.memoryLimit ? `${values.memoryLimit}G` : undefined,
        cpu_limit: values.cpuLimit ? `${values.cpuLimit}` : undefined,
        enable_password: values.enablePassword || false,
        password: values.password || undefined,
      };

      await createVSCodeInstance(notebookId, config);
      message.success('VS Code instance created successfully');
      setIsNewInstanceModalVisible(false);
      form.resetFields();
    } catch (error: any) {
      message.error(error.message || 'Failed to create instance');
    }
  };

  const handleStartInstance = async (instanceId: string) => {
    try {
      await startVSCodeInstance(instanceId);
      message.success('Instance starting...');
    } catch (error: any) {
      message.error(error.message || 'Failed to start instance');
    }
  };

  const handleStopInstance = async (instanceId: string) => {
    try {
      await stopVSCodeInstance(instanceId);
      message.success('Instance stopping...');
    } catch (error: any) {
      message.error(error.message || 'Failed to stop instance');
    }
  };

  const handleRestartInstance = async (instanceId: string) => {
    try {
      await restartVSCodeInstance(instanceId);
      message.success('Instance restarting...');
    } catch (error: any) {
      message.error(error.message || 'Failed to restart instance');
    }
  };

  const handleDeleteInstance = async (instanceId: string) => {
    Modal.confirm({
      title: 'Delete VS Code Instance?',
      content: 'This will stop and remove the VS Code instance. Workspace data will be preserved unless you choose to remove it.',
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteVSCodeInstance(instanceId);
          message.success('Instance deleted');
        } catch (error: any) {
          message.error(error.message || 'Failed to delete instance');
        }
      },
    });
  };

  const runningCount = vscodeInstances.filter((i) => i.status === VSCodeStatus.RUNNING).length;
  const stoppedCount = vscodeInstances.filter((i) => i.status === VSCodeStatus.STOPPED).length;

  return (
    <div className={styles.idePage}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <Title level={2}>
            <LaptopOutlined className={styles.titleIcon} />
            Online IDE
          </Title>
          <Text type="secondary">Choose your development environment</Text>
        </div>
      </div>

      <Alert
        message="Development Environments"
        description="Select an IDE type to start coding. VS Code provides a full-featured editor with extensions, while JupyterLab offers interactive notebooks."
        type="info"
        showIcon
        className={styles.infoAlert}
      />

      <Card title="Select IDE Type" className={styles.ideSelectionCard}>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <IDECard ideType={IDEType.JUPYTER} onSelect={handleSelectIDE} />
          </Col>
          <Col span={8}>
            <IDECard ideType={IDEType.VSCODE} onSelect={handleSelectIDE} />
          </Col>
          <Col span={8}>
            <IDECard ideType={IDEType.VSCODE_INSIDERS} onSelect={handleSelectIDE} />
          </Col>
        </Row>
      </Card>

      <Card
        title={
          <Space>
            <CodeOutlined />
            <span>My VS Code Instances</span>
            <Badge count={runningCount} showZero />
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsNewInstanceModalVisible(true)}
          >
            New Instance
          </Button>
        }
        className={styles.instancesCard}
      >
        {vscodeLoading ? (
          <div className={styles.loadingContainer}>
            <Spin size="large" tip="Loading instances..." />
          </div>
        ) : vscodeInstances.length === 0 ? (
          <div className={styles.emptyState}>
            <CodeOutlined className={styles.emptyIcon} />
            <Title level={4}>No VS Code Instances</Title>
            <Text type="secondary">Create a new instance to start coding</Text>
          </div>
        ) : (
          <Row gutter={[16, 16]}>
            {vscodeInstances.map((instance) => (
              <Col span={8} key={instance.id}>
                <InstanceCard
                  instance={instance}
                  onOpen={(inst) => setCurrentInstance(inst)}
                  onStart={handleStartInstance}
                  onStop={handleStopInstance}
                  onRestart={handleRestartInstance}
                  onDelete={handleDeleteInstance}
                />
              </Col>
            ))}
          </Row>
        )}
      </Card>

      {/* New Instance Modal */}
      <Modal
        title="Create New VS Code Instance"
        open={isNewInstanceModalVisible}
        onOk={handleCreateInstance}
        onCancel={() => {
          setIsNewInstanceModalVisible(false);
          form.resetFields();
        }}
        okText="Create Instance"
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="notebookId"
            label="Notebook ID"
            rules={[{ required: true, message: 'Please enter notebook ID' }]}
            initialValue={1}
          >
            <InputNumber style={{ width: '100%' }} min={1} placeholder="Notebook ID" />
          </Form.Item>

          <Form.Item
            name="extensions"
            label="Extensions"
            tooltip="Popular extensions to pre-install"
          >
            <Select
              mode="tags"
              placeholder="Select extensions"
              options={POPULAR_EXTENSIONS.map((ext) => ({
                label: `${ext.name} - ${ext.description}`,
                value: ext.id,
              }))}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="memoryLimit" label="Memory Limit (GB)">
                <InputNumber min={1} max={32} placeholder="Memory" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cpuLimit" label="CPU Limit">
                <InputNumber min={1} max={8} placeholder="CPU" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="enablePassword" valuePropName="checked">
            <Switch /> <span style={{ marginLeft: 8 }}>Enable Password Protection</span>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.enablePassword !== curr.enablePassword}>
            {({ getFieldValue }) =>
              getFieldValue('enablePassword') ? (
                <Form.Item
                  name="password"
                  label="Password"
                  rules={[{ required: true, message: 'Please enter a password' }]}
                >
                  <Input.Password placeholder="Enter password" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>

      {/* VS Code Viewer Modal */}
      <Modal
        title={null}
        open={!!currentInstance}
        onCancel={() => setCurrentInstance(null)}
        footer={null}
        width="90vw"
        style={{ top: 20 }}
        bodyStyle={{ padding: 0, height: 'calc(100vh - 200px)' }}
      >
        {currentInstance && (
          <VSCodeViewer
            instance={currentInstance}
            onClose={() => setCurrentInstance(null)}
          />
        )}
      </Modal>
    </div>
  );
};

export default IDEPage;
