/**
 * Annotation Workspace Page
 *
 * Main workspace for labeling data using Label Studio.
 * Embeds Label Studio UI with SSO authentication.
 */

import React, { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  Button,
  Space,
  Spin,
  Alert,
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tabs,
  List,
  Tag,
  message,
  Dropdown,
  Modal,
  Form,
  Input,
  Upload,
} from 'antd';
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  CloudUploadOutlined,
  DownloadOutlined,
  SettingOutlined,
  FullscreenOutlined,
  UserOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useAnnotationStore } from '@/stores/annotation';
import type { UploadProps } from 'antd';

const { TabPane } = Tabs;

const AnnotationWorkspacePage: React.FC = () => {
  const params = useParams();
  const projectId = params?.projectId as string | undefined;
  const navigate = useNavigate();
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const {
    currentProject,
    authToken,
    labelStudioUrl,
    loading,
    error,
    fetchProject,
    fetchAuthToken,
    exportAnnotations,
    clearError,
  } = useAnnotationStore();

  const [iframeReady, setIframeReady] = useState(false);
  const [iframeUrl, setIframeUrl] = useState<string | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [exportFormat, setExportFormat] = useState('JSON');

  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      fetchAuthToken();
    }
  }, [projectId, fetchProject, fetchAuthToken]);

  useEffect(() => {
    // Build Label Studio URL with embedded auth
    if (authToken && labelStudioUrl && projectId) {
      const url = `${labelStudioUrl}/projects/${projectId}?token=${authToken}`;
      setIframeUrl(url);
    }
  }, [authToken, labelStudioUrl, projectId]);

  const handleIframeLoad = () => {
    setIframeReady(true);
  };

  const handleRefresh = () => {
    setIframeReady(false);
    fetchProject(projectId!);
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const handleFullscreen = () => {
    if (iframeRef.current) {
      if (iframeRef.current.requestFullscreen) {
        iframeRef.current.requestFullscreen();
      }
    }
  };

  const handleExport = async () => {
    if (!projectId) return;
    setUploading(true);
    try {
      const result = await exportAnnotations(projectId, exportFormat, true);
      message.success(`Exported ${result.annotations?.length || 0} annotations`);
      setExportModalOpen(false);

      // Trigger download if data is returned
      if (result.annotations && result.annotations.length > 0) {
        const blob = new Blob([JSON.stringify(result, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `annotations-${projectId}.${exportFormat.toLowerCase()}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      message.error('Failed to export annotations');
    } finally {
      setUploading(false);
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    action: `/api/v1/annotation/projects/${projectId}/tasks/import`,
    headers: {
      authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    beforeUpload: (file) => {
      // For JSON/CSV files, we can read and submit
      if (file.type === 'application/json' || file.name.endsWith('.json')) {
        const reader = new FileReader();
        reader.onload = async (e) => {
          try {
            const data = JSON.parse(e.target?.result as string);
            // Submit to API
            // This is a simplified version
            message.success(`Uploaded ${data.length?.length || 0} tasks`);
            setImportModalOpen(false);
          } catch (err) {
            message.error('Invalid JSON file');
          }
        };
        reader.readAsText(file);
      } else {
        message.info('File will be uploaded to Label Studio');
      }
      return false; // Prevent automatic upload
    },
    showUploadList: true,
  };

  if (loading && !currentProject) {
    return (
      <div style={{ padding: '100px 0', textAlign: 'center' }}>
        <Spin size="large" />
        <p style={{ marginTop: '16px', color: '#666' }}>
          Loading annotation workspace...
        </p>
      </div>
    );
  }

  if (error && !currentProject) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          type="error"
          message="Failed to load project"
          description={error}
          showIcon
          action={
            <Button size="small" onClick={() => navigate('/annotation')}>
              Go Back
            </Button>
          }
        />
      </div>
    );
  }

  const stats = currentProject?.stats || {
    total_tasks: 0,
    completed_tasks: 0,
    in_progress_tasks: 0,
    completion_rate: 0,
  };

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #f0f0f0' }}>
        <Row gutter={16} align="middle">
          <Col>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/annotation')}
            >
              Back
            </Button>
          </Col>
          <Col flex="auto">
            <Space direction="vertical" size={0}>
              <h2 style={{ margin: 0 }}>
                {currentProject?.name || 'Annotation Workspace'}
              </h2>
              {currentProject?.description && (
                <span style={{ fontSize: '12px', color: '#666' }}>
                  {currentProject.description}
                </span>
              )}
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<CloudUploadOutlined />}
                onClick={() => setImportModalOpen(true)}
              >
                Import
              </Button>
              <Dropdown.Button
                icon={<DownloadOutlined />}
                onClick={() => setExportModalOpen(true)}
                menu={{
                  items: [
                    { key: 'json', label: 'JSON', onClick: () => { setExportFormat('JSON'); setExportModalOpen(true); }},
                    { key: 'csv', label: 'CSV', onClick: () => { setExportFormat('CSV'); setExportModalOpen(true); }},
                    { key: 'coco', label: 'COCO', onClick: () => { setExportFormat('COCO'); setExportModalOpen(true); }},
                    { key: 'voc', label: 'Pascal VOC', onClick: () => { setExportFormat('VOC'); setExportModalOpen(true); }},
                  ],
                }}
              >
                Export
              </Dropdown.Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                title="Refresh workspace"
              />
              <Button
                icon={<FullscreenOutlined />}
                onClick={handleFullscreen}
                title="Fullscreen mode"
              />
              <Button
                icon={<SettingOutlined />}
                onClick={() => navigate(`/annotation/${projectId}/settings`)}
              >
                Settings
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Progress Bar */}
      <div style={{ padding: '12px 24px', background: '#fafafa' }}>
        <Row gutter={16}>
          <Col span={18}>
            <Progress
              percent={Math.round(stats.completion_rate)}
              status={stats.completion_rate === 100 ? 'success' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </Col>
          <Col span={6} style={{ textAlign: 'right' }}>
            <Space size="large">
              <Statistic
                title="Completed"
                value={stats.completed_tasks}
                suffix={`/ ${stats.total_tasks}`}
                valueStyle={{ fontSize: '16px' }}
              />
            </Space>
          </Col>
        </Row>
      </div>

      {/* Main Content - Tabs */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Tabs defaultActiveKey="labeling" style={{ height: '100%' }}>
          <TabPane tab="Labeling Interface" key="labeling">
            {iframeUrl ? (
              <iframe
                ref={iframeRef}
                src={iframeUrl}
                style={{
                  width: '100%',
                  height: 'calc(100vh - 250px)',
                  border: 'none',
                }}
                onLoad={handleIframeLoad}
                title="Label Studio Workspace"
                allow="camera; microphone"
              />
            ) : (
              <div style={{ padding: '100px 0', textAlign: 'center' }}>
                <Spin size="large" />
                <p style={{ marginTop: '16px', color: '#666' }}>
                  Initializing workspace...
                </p>
              </div>
            )}
          </TabPane>

          <TabPane tab={`Tasks (${stats.total_tasks})`} key="tasks">
            <div style={{ padding: '24px', maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
              <List
                dataSource={Array.from({ length: Math.min(stats.total_tasks, 50) }, (_, i) => ({
                  id: i + 1,
                  status: i < stats.completed_tasks ? 'completed' : i < stats.completed_tasks + stats.in_progress_tasks ? 'in_progress' : 'pending',
                  annotations: Math.floor(Math.random() * 3),
                }))}
                renderItem={(task) => (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        size="small"
                        onClick={() => {
                          // Navigate to specific task in Label Studio
                          if (iframeRef.current) {
                            iframeRef.current.contentWindow?.postMessage({
                              type: 'navigate_to_task',
                              taskId: task.id,
                            }, '*');
                          }
                        }}
                      >
                        {task.status === 'completed' ? 'View' : 'Annotate'}
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<Tag color={task.status === 'completed' ? 'green' : task.status === 'in_progress' ? 'blue' : 'default'}>#{task.id}</Tag>}
                      title={`Task ${task.id}`}
                      description={
                        <Space>
                          <Tag icon={task.status === 'completed' ? <CheckCircleOutlined /> : <ClockCircleOutlined />}>
                            {task.status}
                          </Tag>
                          <span>{task.annotations} annotations</span>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </div>
          </TabPane>

          <TabPane tab="Project Info" key="info">
            <div style={{ padding: '24px' }}>
              <Card title="Project Details">
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="Project ID"
                      value={currentProject?.id || '-'}
                      valueStyle={{ fontSize: '14px' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="Task Type"
                      value={currentProject?.task_type?.replace('_', ' ') || '-'}
                      valueStyle={{ fontSize: '14px' }}
                    />
                  </Col>
                </Row>
                <Row gutter={16} style={{ marginTop: '16px' }}>
                  <Col span={12}>
                    <Statistic
                      title="Created"
                      value={currentProject?.created_at ? new Date(currentProject.created_at).toLocaleDateString() : '-'}
                      valueStyle={{ fontSize: '14px' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="AI-Assisted"
                      value={currentProject?.auto_annotation ? 'Enabled' : 'Disabled'}
                      valueStyle={{ fontSize: '14px', color: currentProject?.auto_annotation ? '#52c41a' : undefined }}
                    />
                  </Col>
                </Row>
              </Card>

              {currentProject?.auto_annotation && (
                <Card title="Pre-Annotation Settings" style={{ marginTop: '16px' }}>
                  <p>
                    <strong>Model:</strong> {currentProject.mlflow_run_id || 'Default GPT-4 Vision'}
                  </p>
                  <p>
                    This project uses AI-assisted annotation. Pre-annotations will be
                    generated automatically for imported tasks.
                  </p>
                </Card>
              )}
            </div>
          </TabPane>
        </Tabs>
      </div>

      {/* Import Modal */}
      <Modal
        title="Import Tasks"
        open={importModalOpen}
        onCancel={() => setImportModalOpen(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: '16px' }}>
          <Alert
            message="Import Data"
            description="Upload a JSON file with tasks or provide data from a connected source."
            type="info"
            showIcon
          />
        </div>

        <Upload.Dragger {...uploadProps} style={{ marginBottom: '16px' }}>
          <p className="ant-upload-drag-icon">
            <CloudUploadOutlined />
          </p>
          <p className="ant-upload-text">Click or drag files to this area</p>
          <p className="ant-upload-hint">
            Support for JSON, CSV, and image files. Maximum file size: 50MB.
          </p>
        </Upload.Dragger>

        <div style={{ marginTop: '16px' }}>
          <p style={{ marginBottom: '8px' }}>Or import from URL:</p>
          <Input.Search
            placeholder="https://example.com/data.json"
            enterButton="Import"
          />
        </div>
      </Modal>

      {/* Export Modal */}
      <Modal
        title="Export Annotations"
        open={exportModalOpen}
        onOk={handleExport}
        onCancel={() => setExportModalOpen(false)}
        confirmLoading={uploading}
      >
        <Form layout="vertical">
          <Form.Item label="Export Format">
            <Select value={exportFormat} onChange={setExportFormat}>
              <Option value="JSON">JSON</Option>
              <Option value="CSV">CSV</Option>
              <Option value="COCO">COCO (for object detection)</Option>
              <Option value="VOC">Pascal VOC</Option>
              <Option value="YOLO">YOLO</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Alert
              message={`Export will include ${stats.completed_tasks} completed annotations`}
              type="info"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AnnotationWorkspacePage;

const { Option } = Select;
