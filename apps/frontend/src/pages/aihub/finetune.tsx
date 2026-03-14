/**
 * AIHub Model Fine-tuning Page
 *
 * Configure and launch fine-tuning jobs for AIHub models.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Descriptions,
  Tag,
  Alert,
  Statistic,
  Divider,
  List,
  Progress,
  Modal,
  Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined,
  CodeOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import {
  useAIHubStore,
  useCurrentAIHubModel,
  useFinetuneJobs,
  useAIHubLoading,
} from '@/stores/aihub';

const { Option } = Select;
const { TextArea } = Input;

const AIHubFinetunePage: React.FC = () => {
  const router = useRouter();
  const params = useParams();
  const modelId = params?.modelId as string;

  const [form] = Form.useForm();
  const [costEstimate, setCostEstimate] = useState<any>(null);
  const [estimating, setEstimating] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);

  const {
    currentModel,
    finetuneTemplates,
    finetuneJobs,
    loading,
    fetchModel,
    fetchFinetuneTemplates,
    fetchFinetuneJobs,
    createFinetuneJob,
    startFinetuneJob,
    cancelFinetuneJob,
    deleteFinetuneJob,
    estimateFinetuneCost,
    clearError,
  } = useAIHubStore();

  const [creating, setCreating] = useState(false);
  const [jobDetailVisible, setJobDetailVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<any>(null);

  useEffect(() => {
    if (modelId) {
      fetchModel(modelId);
      fetchFinetuneTemplates(modelId);
      fetchFinetuneJobs(modelId);
    }
  }, [modelId, fetchModel, fetchFinetuneTemplates, fetchFinetuneJobs]);

  const handleEstimateCost = async () => {
    const values = form.getFieldsValue();
    setEstimating(true);
    try {
      const estimate = await estimateFinetuneCost(modelId, {
        method: values.method,
        epochs: values.epochs,
        batch_size: values.batch_size,
      });
      setCostEstimate(estimate);
    } catch (err) {
      message.error('Failed to estimate cost');
    } finally {
      setEstimating(false);
    }
  };

  const handleSelectTemplate = (templateIndex: number) => {
    const template = finetuneTemplates[modelId]?.[templateIndex];
    if (template) {
      const config = template.config;
      form.setFieldsValue({
        method: config.method,
        epochs: 3,
        batch_size: 16,
        learning_rate: 2e-4,
      });
      setSelectedTemplate(templateIndex);
      handleEstimateCost();
    }
  };

  const handleCreateJob = async () => {
    const values = form.getFieldsValue();
    setCreating(true);
    try {
      await createFinetuneJob({
        base_model: modelId,
        dataset_id: values.dataset_id,
        method: values.method,
        epochs: values.epochs,
        batch_size: values.batch_size,
        learning_rate: values.learning_rate,
        use_template: false,
      });
      message.success('Fine-tuning job created');
      fetchFinetuneJobs(modelId);
    } catch (err) {
      message.error('Failed to create job');
    } finally {
      setCreating(false);
    }
  };

  const handleStartJob = async (jobId: string) => {
    try {
      await startFinetuneJob(jobId);
      message.success('Job started');
      fetchFinetuneJobs(modelId);
    } catch (err) {
      message.error('Failed to start job');
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelFinetuneJob(jobId);
      message.success('Job cancelled');
      fetchFinetuneJobs(modelId);
    } catch (err) {
      message.error('Failed to cancel job');
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    try {
      await deleteFinetuneJob(jobId);
      message.success('Job deleted');
      fetchFinetuneJobs(modelId);
    } catch (err) {
      message.error('Failed to delete job');
    }
  };

  const getJobStatusTag = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: string }> = {
      pending: { color: 'default', icon: '⏳' },
      preparing: { color: 'blue', icon: '🔄' },
      training: { color: 'processing', icon: '🚀' },
      evaluating: { color: 'cyan', icon: '📊' },
      saving: { color: 'purple', icon: '💾' },
      completed: { color: 'success', icon: '✅' },
      failed: { color: 'error', icon: '❌' },
      cancelled: { color: 'default', icon: '⏹️' },
    };
    const config = statusConfig[status] || { color: 'default', icon: '⏳' };
    return (
      <Tag color={config.color}>
        {config.icon} {status.toUpperCase()}
      </Tag>
    );
  };

  if (!currentModel) {
    return (
      <div style={{ padding: '100px 0', textAlign: 'center' }}>
        <ClockCircleOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
        <p>Loading model details...</p>
      </div>
    );
  }

  const templates = finetuneTemplates[modelId] || [];

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => router.push('/aihub')}
          >
            Back
          </Button>
        </Col>
        <Col flex="auto">
          <h2 style={{ margin: 0 }}>Fine-tune Model</h2>
          <p style={{ margin: '4px 0 0 0', color: '#666' }}>
            {currentModel.name}
          </p>
        </Col>
      </Row>

      <Row gutter={24}>
        {/* Left Column - Configuration */}
        <Col span={14}>
          {/* Recommended Templates */}
          {templates.length > 0 && (
            <Card
              title="Recommended Templates"
              style={{ marginBottom: '16px' }}
              extra={<InfoCircleOutlined />}
            >
              <Row gutter={16}>
                {templates.map((template, index) => (
                  <Col span={12} key={index} style={{ marginBottom: '16px' }}>
                    <Card
                      size="small"
                      hoverable
                      type={selectedTemplate === index ? 'inner' : 'default'}
                      onClick={() => handleSelectTemplate(index)}
                      style={{
                        borderColor: selectedTemplate === index ? '#1890ff' : undefined,
                      }}
                    >
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <div style={{ fontWeight: 600 }}>{template.name}</div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {template.description}
                        </div>
                        <Divider style={{ margin: '8px 0' }} />
                        <Row justify="space-between" style={{ fontSize: '12px' }}>
                          <Col>
                            <ClockCircleOutlined /> {template.estimated_time}
                          </Col>
                          <Col>
                            <DollarOutlined /> {template.estimated_cost}
                          </Col>
                        </Row>
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          )}

          {/* Fine-tuning Config */}
          <Card title="Fine-tuning Configuration">
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                method: 'lora',
                epochs: 3,
                batch_size: 16,
                learning_rate: 2e-4,
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="dataset_id"
                    label="Dataset ID"
                    rules={[{ required: true, message: 'Enter dataset ID' }]}
                    tooltip="The ID of your training dataset"
                  >
                    <Input placeholder="e.g., dataset-123" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="method"
                    label="Fine-tuning Method"
                    rules={[{ required: true }]}
                    tooltip="Method for parameter-efficient fine-tuning"
                  >
                    <Select onChange={handleEstimateCost}>
                      <Option value="full">Full Fine-tuning</Option>
                      <Option value="lora">LoRA (Recommended)</Option>
                      <Option value="qlora">QLoRA (Most Efficient)</Option>
                      <Option value="adapter">Adapter</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="epochs"
                    label="Epochs"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="batch_size"
                    label="Batch Size"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} max={256} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="learning_rate"
                    label="Learning Rate"
                    rules={[{ required: true }]}
                  >
                    <InputNumber
                      min={0}
                      max={0.01}
                      step={0.0001}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item label="Custom Config (Optional)">
                <TextArea
                  rows={3}
                  placeholder='{"r": 16, "lora_alpha": 32}'
                />
              </Form.Item>

              {/* Cost Estimate */}
              {costEstimate && (
                <Alert
                  type="info"
                  showIcon
                  message="Estimated Cost & Time"
                  description={
                    <Space size="large">
                      <Statistic
                        title="GPU Hours"
                        value={costEstimate.estimated_gpu_hours}
                        precision={1}
                        valueStyle={{ fontSize: '16px' }}
                      />
                      <Statistic
                        title="Estimated Cost"
                        prefix="$"
                        value={costEstimate.estimated_cost_usd}
                        precision={2}
                        valueStyle={{ fontSize: '16px', color: '#52c41a' }}
                      />
                      <Statistic
                        title="Time"
                        value={costEstimate.estimated_time_hours}
                        suffix="hours"
                        precision={1}
                        valueStyle={{ fontSize: '16px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px', color: '#666' }}>Recommended GPU</div>
                        <div style={{ fontWeight: 500 }}>{costEstimate.recommended_gpu_type}</div>
                      </div>
                    </Space>
                  }
                  style={{ marginBottom: '16px' }}
                />
              )}

              <Space>
                <Button
                  icon={<DollarOutlined />}
                  onClick={handleEstimateCost}
                  loading={estimating}
                >
                  Estimate Cost
                </Button>
                <Button
                  type="primary"
                  icon={<CodeOutlined />}
                  onClick={handleCreateJob}
                  loading={creating}
                  size="large"
                >
                  Create Fine-tuning Job
                </Button>
              </Space>
            </Form>
          </Card>
        </Col>

        {/* Right Column - Jobs */}
        <Col span={10}>
          <Card
            title={
              <Space>
                <CodeOutlined />
                Fine-tuning Jobs
              </Space>
            }
          >
            {finetuneJobs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                <CodeOutlined style={{ fontSize: '32px', marginBottom: '8px' }} />
                <p>No fine-tuning jobs yet</p>
              </div>
            ) : (
              <List
                dataSource={finetuneJobs}
                renderItem={(job: any) => (
                  <List.Item
                    actions={[
                      job.status === 'pending' && (
                        <Tooltip title="Start Job">
                          <Button
                            type="link"
                            icon={<PlayCircleOutlined />}
                            onClick={() => handleStartJob(job.job_id)}
                          />
                        </Tooltip>
                      ),
                      job.status === 'training' && (
                        <Tooltip title="Cancel Job">
                          <Button
                            type="link"
                            danger
                            icon={<StopOutlined />}
                            onClick={() => handleCancelJob(job.job_id)}
                          />
                        </Tooltip>
                      ),
                      <Tooltip title="View Details">
                        <Button
                          type="link"
                          onClick={() => {
                            setSelectedJob(job);
                            setJobDetailVisible(true);
                          }}
                        >
                          Details
                        </Button>
                      </Tooltip>,
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <code>{job.job_id.substring(0, 20)}...</code>
                          {getJobStatusTag(job.status)}
                        </Space>
                      }
                      description={
                        <Space direction="vertical" style={{ width: '100%' }} size="small">
                          <div style={{ fontSize: '12px' }}>
                            Dataset: {job.dataset_id}
                          </div>
                          {job.status === 'training' && (
                            <Progress
                              percent={75}
                              size="small"
                              status="active"
                              showInfo={false}
                            />
                          )}
                          {job.status === 'completed' && (
                            <Tag color="green">✅ Completed</Tag>
                          )}
                          <div style={{ fontSize: '11px', color: '#999' }}>
                            Created: {new Date(job.created_at).toLocaleString()}
                          </div>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>

          {/* Quick Stats */}
          <Card title="Job Statistics" style={{ marginTop: '16px' }}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="Total"
                  value={finetuneJobs.length}
                  valueStyle={{ fontSize: '20px' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Running"
                  value={finetuneJobs.filter((j) => j.status === 'training').length}
                  valueStyle={{ fontSize: '20px', color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Completed"
                  value={finetuneJobs.filter((j) => j.status === 'completed').length}
                  valueStyle={{ fontSize: '20px', color: '#1890ff' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Job Detail Modal */}
      <Modal
        title="Job Details"
        open={jobDetailVisible}
        onCancel={() => setJobDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setJobDetailVisible(false)}>
            Close
          </Button>,
          selectedJob?.status === 'completed' && (
            <Button key="deploy" type="primary">
              Deploy Finetuned Model
            </Button>
          ),
        ]}
        width={600}
      >
        {selectedJob && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="Job ID" span={2}>
              <code>{selectedJob.job_id}</code>
            </Descriptions.Item>
            <Descriptions.Item label="Status" span={2}>
              {getJobStatusTag(selectedJob.status)}
            </Descriptions.Item>
            <Descriptions.Item label="Base Model" span={2}>
              {selectedJob.base_model}
            </Descriptions.Item>
            <Descriptions.Item label="Dataset ID" span={2}>
              {selectedJob.dataset_id}
            </Descriptions.Item>
            <Descriptions.Item label="Method" span={2}>
              <Tag>{selectedJob.config?.method?.toUpperCase()}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Created At">
              {new Date(selectedJob.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Started At">
              {selectedJob.started_at
                ? new Date(selectedJob.started_at).toLocaleString()
                : '-'}
            </Descriptions.Item>
            {selectedJob.metrics && Object.keys(selectedJob.metrics).length > 0 && (
              <>
                <Descriptions.Item label="Train Loss" span={2}>
                  {selectedJob.metrics.train_loss?.toFixed(4)}
                </Descriptions.Item>
                <Descriptions.Item label="Val Loss" span={2}>
                  {selectedJob.metrics.val_loss?.toFixed(4)}
                </Descriptions.Item>
                <Descriptions.Item label="Train Accuracy" span={2}>
                  {(selectedJob.metrics.train_accuracy * 100).toFixed(2)}%
                </Descriptions.Item>
              </>
            )}
            {selectedJob.output_model_uri && (
              <Descriptions.Item label="Output Model" span={2}>
                <code>{selectedJob.output_model_uri}</code>
              </Descriptions.Item>
            )}
            {selectedJob.error && (
              <Descriptions.Item label="Error" span={2}>
                <Alert type="error" message={selectedJob.error} />
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default AIHubFinetunePage;
