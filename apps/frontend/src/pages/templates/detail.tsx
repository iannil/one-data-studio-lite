/**
 * Template Detail Page
 *
 * View detailed information about a workflow template and instantiate it.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Tag,
  Divider,
  Descriptions,
  Rate,
  Tabs,
  Form,
  Input,
  Modal,
  message,
  Badge,
  Tooltip,
  List,
  Avatar,
  Spin,
} from 'antd';
import {
  ArrowLeftOutlined,
  ThunderboltOutlined,
  StarOutlined,
  StarFilled,
  DownloadOutlined,
  EyeOutlined,
  CopyOutlined,
  FileTextOutlined,
  CodeOutlined,
  SettingOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useTemplateStore } from '@/stores/template';

const { TextArea } = Input;

const TemplateDetailPage: React.FC = () => {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();

  const {
    currentTemplate,
    loading,
    error,
    fetchTemplate,
    recordUsage,
    recordDownload,
    addReview,
  } = useTemplateStore();

  const [instantiateModalOpen, setInstantiateModalOpen] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [form] = Form.useForm();

  // Fetch template on mount
  useEffect(() => {
    if (templateId) {
      fetchTemplate(templateId);
    }
  }, [templateId, fetchTemplate]);

  // Handle instantiate
  const handleInstantiate = async (values: any) => {
    if (!templateId) return;

    await recordUsage(templateId);

    // Navigate to workflow editor with template
    navigate(`/workflows/editor/new?template=${templateId}&variables=${JSON.stringify(values.variables)}`);

    message.success('Template instantiated successfully!');
    setInstantiateModalOpen(false);
  };

  // Handle download
  const handleDownload = async () => {
    if (!templateId || !currentTemplate) return;

    await recordDownload(templateId);

    // Create and download JSON file
    const data = JSON.stringify(currentTemplate, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${templateId}.json`;
    a.click();
    URL.revokeObjectURL(url);

    message.success('Template downloaded successfully!');
  };

  // Handle review submit
  const handleReviewSubmit = async (values: any) => {
    if (!templateId) return;

    try {
      await addReview(templateId, {
        rating: values.rating,
        comment: values.comment,
      });

      message.success('Review submitted successfully!');
      setReviewModalOpen(false);
      form.resetFields();

      // Refresh template data
      fetchTemplate(templateId);
    } catch (err: any) {
      message.error(err.message || 'Failed to submit review');
    }
  };

  // Complexity colors
  const complexityColors: Record<string, string> = {
    beginner: 'green',
    intermediate: 'blue',
    advanced: 'orange',
  };

  // Category icons
  const categoryIcons: Record<string, string> = {
    etl: '🔄',
    ml_training: '🧠',
    data_quality: '📊',
    monitoring: '📈',
    batch_inference: '🔮',
    data_sync: '🔄',
    reporting: '📄',
    notification: '🔔',
    backup: '💾',
    data_pipeline: '⚙️',
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!currentTemplate) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <h2>Template not found</h2>
        <Button onClick={() => navigate('/templates')}>Back to Market</Button>
      </div>
    );
  }

  const stats = currentTemplate.stats || {};
  const reviews = currentTemplate.reviews || [];

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/templates')}
          style={{ marginBottom: 16 }}
        >
          Back to Market
        </Button>

        <Row gutter={24}>
          <Col span={18}>
            <Space size="large" align="center">
              <span style={{ fontSize: 64 }}>
                {currentTemplate.icon || categoryIcons[currentTemplate.category] || '📦'}
              </span>
              <div>
                <Space size="middle">
                  <h1 style={{ margin: 0 }}>{currentTemplate.name}</h1>
                  {currentTemplate.official && (
                    <Tag color="blue">Official</Tag>
                  )}
                  {currentTemplate.verified && (
                    <Tag color="green">Verified</Tag>
                  )}
                  {currentTemplate.featured && (
                    <Tag color="gold">Featured</Tag>
                  )}
                </Space>
                <div style={{ marginTop: 8, color: '#666' }}>
                  {currentTemplate.description}
                </div>
                <Space style={{ marginTop: 12 }}>
                  <Rate
                    disabled
                    value={stats.avg_rating || 0}
                  />
                  <span>({stats.rating_count || 0} reviews)</span>
                  <span>•</span>
                  <span>{stats.usage_count || 0} uses</span>
                  <span>•</span>
                  <span>{stats.download_count || 0} downloads</span>
                </Space>
              </div>
            </Space>
          </Col>
          <Col span={6} style={{ textAlign: 'right' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                type="primary"
                size="large"
                icon={<ThunderboltOutlined />}
                block
                onClick={() => setInstantiateModalOpen(true)}
              >
                Use Template
              </Button>
              <Button
                size="large"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                block
              >
                Download
              </Button>
              <Button
                size="large"
                icon={<StarOutlined />}
                onClick={() => setReviewModalOpen(true)}
                block
              >
                Rate & Review
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Main Content */}
        <Row gutter={24}>
          {/* Left Column */}
          <Col span={16}>
            {/* Overview Tab */}
            <Card
              title={
                <Space>
                  <FileTextOutlined />
                  Overview
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Descriptions column={2} bordered>
                <Descriptions.Item label="Category">
                  {categoryIcons[currentTemplate.category]} {currentTemplate.category}
                </Descriptions.Item>
                <Descriptions.Item label="Complexity">
                  <Tag color={complexityColors[currentTemplate.complexity]}>
                    {currentTemplate.complexity}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Author">
                  {currentTemplate.author || 'Unknown'}
                </Descriptions.Item>
                <Descriptions.Item label="Version">
                  {currentTemplate.current_version}
                </Descriptions.Item>
                <Descriptions.Item label="Tasks">
                  {currentTemplate.task_count || 0}
                </Descriptions.Item>
                <Descriptions.Item label="Variables">
                  {currentTemplate.variable_count || 0}
                </Descriptions.Item>
              </Descriptions>

              {currentTemplate.documentation && (
                <>
                  <Divider>Documentation</Divider>
                  <div dangerouslySetInnerHTML={{ __html: currentTemplate.documentation }} />
                </>
              )}

              {currentTemplate.requirements && currentTemplate.requirements.length > 0 && (
                <>
                  <Divider>Requirements</Divider>
                  <List
                    dataSource={currentTemplate.requirements}
                    renderItem={(item: string) => (
                      <List.Item>
                        <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                        {item}
                      </List.Item>
                    )}
                  />
                </>
              )}
            </Card>

            {/* Tasks Tab */}
            <Card
              title={
                <Space>
                  <CodeOutlined />
                  Tasks ({currentTemplate.tasks?.length || 0})
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              {currentTemplate.tasks && currentTemplate.tasks.length > 0 ? (
                <List
                  dataSource={currentTemplate.tasks}
                  renderItem={(task: any, index: number) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          <Avatar style={{ background: '#1890ff' }}>
                            {index + 1}
                          </Avatar>
                        }
                        title={task.name}
                        description={
                          <Space direction="vertical" size="small">
                            <div>{task.description}</div>
                            <Tag color="blue">{task.task_type}</Tag>
                            {task.depends_on && task.depends_on.length > 0 && (
                              <div>
                                Depends on: {task.depends_on.join(', ')}
                              </div>
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
                  No tasks defined
                </div>
              )}
            </Card>

            {/* Reviews Tab */}
            <Card
              title={
                <Space>
                  <StarFilled />
                  Reviews ({reviews.length})
                </Space>
              }
            >
              {reviews.length > 0 ? (
                <List
                  dataSource={reviews}
                  renderItem={(review: any) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          <Avatar style={{ background: '#f56a00' }}>
                            {review.user_name?.charAt(0).toUpperCase()}
                          </Avatar>
                        }
                        title={
                          <Space>
                            <span>{review.user_name}</span>
                            <Rate disabled value={review.rating} style={{ fontSize: 14 }} />
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size="small">
                            <div>{review.comment}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>
                              {new Date(review.created_at).toLocaleDateString()}
                            </div>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
                  No reviews yet. Be the first to review!
                </div>
              )}
            </Card>
          </Col>

          {/* Right Column */}
          <Col span={8}>
            {/* Tags */}
            <Card
              title={
                <Space>
                  <TagOutlined />
                  Tags
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              {currentTemplate.tags && currentTemplate.tags.length > 0 ? (
                <Space wrap>
                  {currentTemplate.tags.map((tag: string) => (
                    <Tag key={tag}>{tag}</Tag>
                  ))}
                </Space>
              ) : (
                <div style={{ color: '#999' }}>No tags</div>
              )}
            </Card>

            {/* Versions */}
            <Card
              title={
                <Space>
                  <SettingOutlined />
                  Versions
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              {currentTemplate.versions && currentTemplate.versions.length > 0 ? (
                <List
                  dataSource={currentTemplate.versions}
                  renderItem={(version: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={<Tag color="blue">{version.version}</Tag>}
                        description={
                          <Space direction="vertical" size="small">
                            <div>{version.changelog}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>
                              by {version.author} • {new Date(version.created_at).toLocaleDateString()}
                            </div>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ color: '#999' }}>No version history</div>
              )}
            </Card>

            {/* Stats */}
            <Card
              title={
                <Space>
                  <EyeOutlined />
                  Statistics
                </Space>
              }
            >
              <Descriptions column={1}>
                <Descriptions.Item label="Total Uses">
                  {stats.usage_count || 0}
                </Descriptions.Item>
                <Descriptions.Item label="Views">
                  {stats.view_count || 0}
                </Descriptions.Item>
                <Descriptions.Item label="Downloads">
                  {stats.download_count || 0}
                </Descriptions.Item>
                <Descriptions.Item label="Forks">
                  {stats.fork_count || 0}
                </Descriptions.Item>
                <Descriptions.Item label="Average Rating">
                  <Rate
                    disabled
                    value={stats.avg_rating || 0}
                    style={{ fontSize: 14 }}
                  />{' '}
                  ({stats.rating_count || 0})
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        </Row>
      </Row>

      {/* Instantiate Modal */}
      <Modal
        title={`Instantiate ${currentTemplate.name}`}
        open={instantiateModalOpen}
        onCancel={() => setInstantiateModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <p style={{ marginBottom: 16 }}>
          Configure the template variables before creating the workflow.
        </p>

        {currentTemplate.variables && currentTemplate.variables.length > 0 ? (
          <Form form={form} layout="vertical" onFinish={handleInstantiate}>
            {currentTemplate.variables.map((variable: any) => (
              <Form.Item
                key={variable.name}
                name={['variables', variable.name]}
                label={variable.label || variable.name}
                description={variable.description}
                rules={variable.required ? [{ required: true, message: `This field is required` }] : []}
                initialValue={variable.default}
              >
                {variable.type === 'textarea' ? (
                  <TextArea rows={4} placeholder={variable.placeholder} />
                ) : variable.type === 'select' ? (
                  <Select placeholder={variable.placeholder}>
                    {variable.options?.map((opt: any) => (
                      <Option key={opt.value} value={opt.value}>
                        {opt.label}
                      </Option>
                    ))}
                  </Select>
                ) : (
                  <Input placeholder={variable.placeholder} />
                )}
              </Form.Item>
            ))}
          </Form>
        ) : (
          <p style={{ color: '#999' }}>This template has no configurable variables.</p>
        )}
      </Modal>

      {/* Review Modal */}
      <Modal
        title="Rate & Review"
        open={reviewModalOpen}
        onCancel={() => setReviewModalOpen(false)}
        onOk={() => form.submit()}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleReviewSubmit}>
          <Form.Item
            name="rating"
            label="Rating"
            rules={[{ required: true, message: 'Please select a rating' }]}
          >
            <Rate style={{ fontSize: 24 }} />
          </Form.Item>

          <Form.Item
            name="comment"
            label="Review (optional)"
          >
            <TextArea
              rows={4}
              placeholder="Share your experience with this template..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

import { TagOutlined } from '@ant-design/icons';
import { Select } from 'antd';
const { Option } = Select;

export default TemplateDetailPage;
