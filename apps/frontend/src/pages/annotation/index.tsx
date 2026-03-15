/**
 * Annotation Projects List Page
 *
 * Lists all Label Studio annotation projects with create/edit/delete functionality.
 * Supports multi-modal annotation (images, text, audio, video) and quality control.
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Select,
  Switch,
  message,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic,
  Progress,
  Tabs,
  Dropdown,
  Divider,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CloudUploadOutlined,
  DownloadOutlined,
  SettingOutlined,
  LabelOutlined,
  CheckCircleOutlined,
  SoundOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  PictureOutlined,
  SafetyOutlined,
  TeamOutlined,
  MoreOutlined,
  FileSearchOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import { useAnnotationStore, AnnotationProject } from '@/stores/annotation';

const { Option } = Select;
const { TabPane } = Tabs;

// Task type categories
const TASK_TYPE_CATEGORIES = {
  image: {
    label: 'Image',
    icon: <PictureOutlined />,
    types: ['image_classification', 'object_detection', 'segmentation'],
  },
  text: {
    label: 'Text',
    icon: <FileTextOutlined />,
    types: ['text_classification', 'ner'],
  },
  audio: {
    label: 'Audio',
    icon: <SoundOutlined />,
    types: ['audio_classification', 'transcription', 'speaker_diarization'],
  },
  video: {
    label: 'Video',
    icon: <VideoCameraOutlined />,
    types: ['video_classification', 'video_object_detection', 'action_recognition'],
  },
  multimodal: {
    label: 'Multimodal',
    icon: <StarOutlined />,
    types: ['multimodal'],
  },
};

const AnnotationListPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('all');
  const [qualityModalOpen, setQualityModalOpen] = useState(false);
  const [selectedProjectForQuality, setSelectedProjectForQuality] = useState<string | null>(null);

  const {
    projects,
    loading,
    fetchProjects,
    createProject,
    deleteProject,
    clearError,
  } = useAnnotationStore();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedProject, setSelectedProject] = useState<AnnotationProject | null>(null);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreate = async () => {
    const values = form.getFieldsValue();
    setCreating(true);
    try {
      await createProject({
        name: values.name,
        description: values.description,
        task_type: values.task_type,
        use_default_config: values.use_default_config !== false,
        auto_annotation: values.auto_annotation || false,
        mlflow_run_id: values.mlflow_run_id,
      });
      message.success('Annotation project created successfully');
      setCreateModalOpen(false);
      form.resetFields();
    } catch (err) {
      message.error('Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (project: AnnotationProject) => {
    try {
      await deleteProject(project.id);
      message.success('Project deleted');
    } catch (err) {
      message.error('Failed to delete project');
    }
  };

  const getTaskTypeTag = (taskType: string) => {
    const typeMap: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      image_classification: { color: 'blue', icon: <PictureOutlined />, label: 'Image Classification' },
      object_detection: { color: 'purple', icon: <PictureOutlined />, label: 'Object Detection' },
      segmentation: { color: 'cyan', icon: <PictureOutlined />, label: 'Segmentation' },
      text_classification: { color: 'green', icon: <FileTextOutlined />, label: 'Text Classification' },
      ner: { color: 'orange', icon: <FileTextOutlined />, label: 'NER' },
      audio_classification: { color: 'geekblue', icon: <SoundOutlined />, label: 'Audio Classification' },
      transcription: { color: 'geekblue', icon: <SoundOutlined />, label: 'Transcription' },
      speaker_diarization: { color: 'geekblue', icon: <SoundOutlined />, label: 'Speaker Diarization' },
      video_classification: { color: 'magenta', icon: <VideoCameraOutlined />, label: 'Video Classification' },
      video_object_detection: { color: 'magenta', icon: <VideoCameraOutlined />, label: 'Video Detection' },
      action_recognition: { color: 'magenta', icon: <VideoCameraOutlined />, label: 'Action Recognition' },
      multimodal: { color: 'gold', icon: <StarOutlined />, label: 'Multimodal' },
    };
    const info = typeMap[taskType] || { color: 'default', icon: null, label: taskType };
    return (
      <Tag color={info.color} icon={info.icon}>
        {info.label}
      </Tag>
    );
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; icon: React.ReactNode }> = {
      active: { color: 'green', icon: <CheckCircleOutlined /> },
      archived: { color: 'default', icon: null },
      completed: { color: 'blue', icon: <CheckCircleOutlined /> },
      in_review: { color: 'orange', icon: <SafetyOutlined /> },
    };
    const info = statusMap[status] || { color: 'default', icon: null };
    return (
      <Tag color={info.color} icon={info.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  };

  // Filter projects by category
  const getFilteredProjects = () => {
    if (activeTab === 'all') return projects;

    for (const [category, config] of Object.entries(TASK_TYPE_CATEGORIES)) {
      if (activeTab === category) {
        return projects.filter((p) => config.types.includes(p.task_type));
      }
    }
    return projects;
  };

  const filteredProjects = getFilteredProjects();

  const columns = [
    {
      title: 'Project Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: AnnotationProject) => (
        <Space direction="vertical" size={0}>
          <Space>
            <a
              onClick={() => navigate(`/annotation/${record.id}`)}
              style={{ fontWeight: 500 }}
            >
              {name}
            </a>
            {record.auto_annotation && <Tag color="purple">AI</Tag>}
            {record.quality_control && <Tag color="orange">QC</Tag>}
          </Space>
          {record.description && (
            <span style={{ fontSize: '12px', color: '#999' }}>
              {record.description}
            </span>
          )}
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'task_type',
      key: 'task_type',
      render: (taskType: string) => getTaskTypeTag(taskType),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: 'Progress',
      key: 'progress',
      render: (_: any, record: AnnotationProject) => {
        const percent = record.stats.completion_rate || 0;
        return (
          <div style={{ width: 120 }}>
            <Progress
              percent={Math.round(percent)}
              size="small"
              status={percent === 100 ? 'success' : 'active'}
            />
            <span style={{ fontSize: '12px', color: '#666' }}>
              {record.stats.completed_tasks}/{record.stats.total_tasks}
            </span>
          </div>
        );
      },
    },
    {
      title: 'Quality',
      key: 'quality',
      render: (_: any, record: AnnotationProject) => {
        const agreement = record.stats.agreement_score || 0;
        return (
          <Space size="small">
            <Tooltip title="Inter-annotator agreement">
              <Tag color={agreement > 0.8 ? 'green' : agreement > 0.6 ? 'orange' : 'red'}>
                κ: {agreement.toFixed(2)}
              </Tag>
            </Tooltip>
            {record.stats.pending_reviews > 0 && (
              <Badge count={record.stats.pending_reviews} size="small">
                <SafetyOutlined />
              </Badge>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (timestamp: string) => new Date(timestamp).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 160,
      render: (_: any, record: AnnotationProject) => (
        <Space size="small">
          <Tooltip title="View & Annotate">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/annotation/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Quality Control">
            <Button
              type="text"
              icon={<SafetyOutlined />}
              onClick={() => {
                setSelectedProjectForQuality(record.id);
                setQualityModalOpen(true);
              }}
            />
          </Tooltip>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'import',
                  label: 'Import Tasks',
                  icon: <CloudUploadOutlined />,
                  onClick: () => navigate(`/annotation/${record.id}/import`),
                },
                {
                  key: 'export',
                  label: 'Export Annotations',
                  icon: <DownloadOutlined />,
                  onClick: () => navigate(`/annotation/${record.id}/export`),
                },
                {
                  key: 'metrics',
                  label: 'Quality Metrics',
                  icon: <FileSearchOutlined />,
                  onClick: () => navigate(`/annotation/${record.id}/quality`),
                },
                { type: 'divider' },
                {
                  key: 'settings',
                  label: 'Settings',
                  icon: <SettingOutlined />,
                  onClick: () => navigate(`/annotation/${record.id}/settings`),
                },
                {
                  key: 'delete',
                  label: 'Delete',
                  icon: <DeleteOutlined />,
                  danger: true,
                  onClick: () => handleDelete(record),
                },
              ],
            }}
          >
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // Calculate stats
  const totalProjects = projects.length;
  const activeProjects = projects.filter((p) => p.status === 'active').length;
  const totalTasks = projects.reduce((sum, p) => sum + p.stats.total_tasks, 0);
  const completedTasks = projects.reduce((sum, p) => sum + p.stats.completed_tasks, 0);
  const overallProgress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
  const avgAgreement = projects.length > 0
    ? projects.reduce((sum, p) => sum + (p.stats.agreement_score || 0), 0) / projects.length
    : 0;

  return (
    <div style={{ padding: '24px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={0}>
              <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
                <LabelOutlined /> Data Annotation
              </h1>
              <span style={{ color: '#999' }}>
                Multi-modal data labeling with AI assistance and quality control
              </span>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalOpen(true)}
            >
              New Project
            </Button>
          </Col>
        </Row>
      </div>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Projects"
              value={totalProjects}
              prefix={<LabelOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Active"
              value={activeProjects}
              valueStyle={{ color: activeProjects > 0 ? '#52c41a' : undefined }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Tasks"
              value={totalTasks}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Completed"
              value={completedTasks}
              suffix={`/ ${totalTasks}`}
              valueStyle={{
                color: overallProgress > 50 ? '#52c41a' : overallProgress > 0 ? '#faad14' : undefined,
              }}
            />
            <Progress
              percent={Math.round(overallProgress)}
              size="small"
              style={{ marginTop: '8px' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Avg Agreement"
              value={avgAgreement}
              precision={2}
              valueStyle={{ color: avgAgreement > 0.8 ? '#52c41a' : avgAgreement > 0.6 ? '#faad14' : '#ff4d4f' }}
              suffix="κ"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Pending Reviews"
              value={projects.reduce((sum, p) => sum + (p.stats.pending_reviews || 0), 0)}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Category Tabs */}
      <Card
        bodyStyle={{ padding: 0 }}
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ padding: '0 24px' }}
          items={[
            {
              key: 'all',
              label: (
                <span>
                  <LabelOutlined />
                  All ({projects.length})
                </span>
              ),
            },
            ...Object.entries(TASK_TYPE_CATEGORIES).map(([key, config]) => ({
              key,
              label: (
                <span>
                  {config.icon}
                  {config.label} ({projects.filter((p) => config.types.includes(p.task_type)).length})
                </span>
              ),
            })),
          ]}
        />
        <div style={{ flex: 1 }}>
          <Table
            columns={columns}
            dataSource={filteredProjects}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total ${total} projects`,
            }}
            scroll={{ y: 'calc(100vh - 520px)' }}
          />
        </div>
      </Card>

      {/* Create Project Modal */}
      <Modal
        title="Create Annotation Project"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={creating}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Project Name"
            rules={[{ required: true, message: 'Please enter project name' }]}
          >
            <Input placeholder="e.g., Image Classification 2024" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea
              rows={2}
              placeholder="Describe the annotation project..."
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="task_type"
                label="Task Type"
                initialValue="image_classification"
                rules={[{ required: true, message: 'Please select task type' }]}
              >
                <Select>
                  <Select.OptGroup label="Image">
                    <Option value="image_classification">Image Classification</Option>
                    <Option value="object_detection">Object Detection</Option>
                    <Option value="segmentation">Segmentation</Option>
                  </Select.OptGroup>
                  <Select.OptGroup label="Text">
                    <Option value="text_classification">Text Classification</Option>
                    <Option value="ner">Named Entity Recognition</Option>
                  </Select.OptGroup>
                  <Select.OptGroup label="Audio">
                    <Option value="audio_classification">Audio Classification</Option>
                    <Option value="transcription">Transcription</Option>
                    <Option value="speaker_diarization">Speaker Diarization</Option>
                  </Select.OptGroup>
                  <Select.OptGroup label="Video">
                    <Option value="video_classification">Video Classification</Option>
                    <Option value="video_object_detection">Video Object Detection</Option>
                    <Option value="action_recognition">Action Recognition</Option>
                  </Select.OptGroup>
                  <Select.OptGroup label="Multimodal">
                    <Option value="multimodal">Multimodal</Option>
                  </Select.OptGroup>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="mlflow_run_id"
                label="MLflow Run ID"
                tooltip="Use a specific MLflow model for pre-annotation"
              >
                <Input placeholder="Optional" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="use_default_config"
            label="Use Default Labeling Config"
            initialValue={true}
            valuePropName="checked"
          >
            <Switch checkedChildren="Default" unCheckedChildren="Custom" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="auto_annotation"
                label="AI-Assisted Annotation"
                initialValue={false}
                valuePropName="checked"
                tooltip="Use models to generate pre-annotations"
              >
                <Switch checkedChildren="Enabled" unCheckedChildren="Disabled" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="quality_control"
                label="Quality Control"
                initialValue={false}
                valuePropName="checked"
                tooltip="Enable review workflow and consensus"
              >
                <Switch checkedChildren="Enabled" unCheckedChildren="Disabled" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Quality Control Quick Modal */}
      <Modal
        title={
          <Space>
            <SafetyOutlined />
            Quality Control
          </Space>
        }
        open={qualityModalOpen}
        onCancel={() => setQualityModalOpen(false)}
        footer={null}
        width={800}
      >
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <SafetyOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
          <h3 style={{ marginTop: '16px' }}>Quality Control Dashboard</h3>
          <p style={{ color: '#666' }}>
            View detailed quality metrics, pending reviews, and annotator performance
          </p>
          <Button
            type="primary"
            onClick={() => {
              setQualityModalOpen(false);
              navigate(`/annotation/${selectedProjectForQuality}/quality`);
            }}
          >
            Open Quality Dashboard
          </Button>
        </div>
      </Modal>
    </div>
  );
};

export default AnnotationListPage;
