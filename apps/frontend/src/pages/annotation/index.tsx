/**
 * Annotation Projects List Page
 *
 * Lists all Label Studio annotation projects with create/edit/delete functionality.
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
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import { useAnnotationStore, AnnotationProject } from '@/stores/annotation';

const { Option } = Select;

const AnnotationListPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();

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
    const typeMap: Record<string, { color: string; icon: string }> = {
      image_classification: { color: 'blue', icon: 'IMG' },
      object_detection: { color: 'purple', icon: 'OBJ' },
      segmentation: { color: 'cyan', icon: 'SEG' },
      text_classification: { color: 'green', icon: 'TXT' },
      ner: { color: 'orange', icon: 'NER' },
      multimodal: { color: 'magenta', icon: 'MUL' },
    };
    const info = typeMap[taskType] || { color: 'default', icon: 'UNK' };
    return (
      <Tag color={info.color}>
        {info.icon} {task_type.replace('_', ' ')}
      </Tag>
    );
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; icon: React.ReactNode }> = {
      active: { color: 'green', icon: <CheckCircleOutlined /> },
      archived: { color: 'default', icon: null },
      completed: { color: 'blue', icon: <CheckCircleOutlined /> },
    };
    const info = statusMap[status] || { color: 'default', icon: null };
    return (
      <Tag color={info.color} icon={info.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  };

  const columns = [
    {
      title: 'Project Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: AnnotationProject) => (
        <Space>
          <a
            onClick={() => navigate(`/annotation/${record.id}`)}
            style={{ fontWeight: 500 }}
          >
            {name}
          </a>
          {record.auto_annotation && <Tag color="purple">AI-Assisted</Tag>}
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
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (timestamp: string) => new Date(timestamp).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      render: (_: any, record: AnnotationProject) => (
        <Space size="small">
          <Tooltip title="View & Annotate">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/annotation/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Import Tasks">
            <Button
              type="text"
              icon={<CloudUploadOutlined />}
              onClick={() => navigate(`/annotation/${record.id}/import`)}
            />
          </Tooltip>
          <Tooltip title="Export">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => navigate(`/annotation/${record.id}/export`)}
            />
          </Tooltip>
          <Tooltip title="Settings">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => navigate(`/annotation/${record.id}/settings`)}
            />
          </Tooltip>
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

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>
            <LabelOutlined /> Data Annotation
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            Label Studio integration for multi-modal data labeling
          </p>
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

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Projects"
              value={totalProjects}
              prefix={<LabelOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Projects"
              value={activeProjects}
              valueStyle={{ color: activeProjects > 0 ? '#52c41a' : undefined }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Tasks"
              value={totalTasks}
            />
          </Card>
        </Col>
        <Col span={6}>
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
      </Row>

      {/* Projects Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} projects`,
          }}
        />
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

          <Form.Item
            name="task_type"
            label="Task Type"
            initialValue="image_classification"
            rules={[{ required: true, message: 'Please select task type' }]}
          >
            <Select>
              <Option value="image_classification">Image Classification</Option>
              <Option value="object_detection">Object Detection</Option>
              <Option value="segmentation">Segmentation</Option>
              <Option value="text_classification">Text Classification</Option>
              <Option value="ner">Named Entity Recognition</Option>
              <Option value="multimodal">Multi-modal</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="use_default_config"
            label="Use Default Labeling Config"
            initialValue={true}
            valuePropName="checked"
          >
            <Switch checkedChildren="Default" unCheckedChildren="Custom" />
          </Form.Item>

          <Form.Item
            name="auto_annotation"
            label="Enable AI-Assisted Annotation"
            initialValue={false}
            valuePropName="checked"
            tooltip="Use models to generate pre-annotations"
          >
            <Switch checkedChildren="Enabled" unCheckedChildren="Disabled" />
          </Form.Item>

          <Form.Item
            name="mlflow_run_id"
            label="MLflow Run ID (Optional)"
            tooltip="Use a specific MLflow model for pre-annotation"
          >
            <Input placeholder="e.g., abc123def456" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AnnotationListPage;
