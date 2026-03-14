/**
 * AIHub Model Deployment Page
 *
 * Configure and deploy AIHub models with one-click.
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
  InputNumber,
  Switch,
  Select,
  message,
  Descriptions,
  Tag,
  Progress,
  Alert,
  Statistic,
  Divider,
} from 'antd';
import {
  ArrowLeftOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import {
  useAIHubStore,
  useCurrentAIHubModel,
  useAIHubLoading,
} from '@/stores/aihub';

const { Option } = Select;

const AIHubDeployPage: React.FC = () => {
  const router = useRouter();
  const params = useParams();
  const modelId = params?.modelId as string;

  const [form] = Form.useForm();

  const {
    currentModel,
    deploymentTemplate,
    deployments,
    loading,
    fetchModel,
    fetchDeploymentTemplate,
    fetchDeployments,
    createDeployment,
    clearError,
  } = useAIHubStore();

  const [deploying, setDeploying] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<string | null>(null);

  useEffect(() => {
    if (modelId) {
      fetchModel(modelId);
      fetchDeploymentTemplate(modelId);
      fetchDeployments(modelId);
    }
  }, [modelId, fetchModel, fetchDeploymentTemplate, fetchDeployments]);

  const handleDeploy = async () => {
    const values = form.getFieldsValue();
    setDeploying(true);
    try {
      await createDeployment({
        model_id: modelId,
        name: values.name,
        replicas: values.replicas,
        gpu_enabled: values.gpu_enabled,
        gpu_type: values.gpu_type,
        gpu_count: values.gpu_count,
        autoscaling_enabled: values.autoscaling_enabled,
        autoscaling_min: values.autoscaling_min,
        autoscaling_max: values.autoscaling_max,
      });
      message.success('Deployment created successfully');
      fetchDeployments(modelId);
    } catch (err) {
      message.error('Failed to create deployment');
    } finally {
      setDeploying(false);
    }
  };

  const loadTemplate = () => {
    if (deploymentTemplate) {
      form.setFieldsValue({
        name: `${currentModel?.id}-deployment`,
        replicas: deploymentTemplate.replicas,
        gpu_enabled: deploymentTemplate.gpu_enabled,
        gpu_count: deploymentTemplate.gpu_count,
        gpu_type: deploymentTemplate.gpu_type,
        autoscaling_enabled: deploymentTemplate.autoscaling?.enabled,
        autoscaling_min: deploymentTemplate.autoscaling?.min_replicas,
        autoscaling_max: deploymentTemplate.autoscaling?.max_replicas,
      });
    }
  };

  useEffect(() => {
    if (deploymentTemplate && !form.isFieldsTouched()) {
      loadTemplate();
    }
  }, [deploymentTemplate]);

  if (!currentModel) {
    return (
      <div style={{ padding: '100px 0', textAlign: 'center' }}>
        <ClockCircleOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
        <p>Loading model details...</p>
      </div>
    );
  }

  const modelDeployments = deployments.filter((d) => d.model_id === modelId);

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
          <h2 style={{ margin: 0 }}>Deploy Model</h2>
          <p style={{ margin: '4px 0 0 0', color: '#666' }}>
            {currentModel.name}
          </p>
        </Col>
      </Row>

      <Row gutter={24}>
        {/* Left Column - Configuration */}
        <Col span={14}>
          {/* Model Info */}
          <Card title="Model Information" style={{ marginBottom: '16px' }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="Model ID">
                <code>{currentModel.id}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Category">
                <Tag>{currentModel.category.replace('_', ' ')}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Framework">
                <Tag>{currentModel.framework}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Parameters">
                {currentModel.parameter_size}
              </Descriptions.Item>
              <Descriptions.Item label="GPU Memory">
                {currentModel.gpu_memory_mb
                  ? `${(currentModel.gpu_memory_mb / 1024).toFixed(1)} GB`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Provider">
                {currentModel.provider}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* Deployment Config */}
          <Card title="Deployment Configuration" extra={
            <Button size="small" onClick={loadTemplate}>
              Load Template
            </Button>
          }>
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                name: `${currentModel.id}-deployment`,
                replicas: 1,
                gpu_enabled: true,
                gpu_count: 1,
                gpu_type: 'A100',
                autoscaling_enabled: true,
                autoscaling_min: 1,
                autoscaling_max: 5,
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="name"
                    label="Deployment Name"
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="replicas"
                    label="Replicas"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} max={10} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">GPU Configuration</Divider>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="gpu_enabled"
                    label="Enable GPU"
                    valuePropName="checked"
                  >
                    <Switch checkedChildren="Enabled" unCheckedChildren="Disabled" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="gpu_count"
                    label="GPU Count"
                  >
                    <InputNumber min={1} max={8} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="gpu_type"
                    label="GPU Type"
                  >
                    <Select>
                      <Option value="A100">NVIDIA A100</Option>
                      <Option value="V100">NVIDIA V100</Option>
                      <Option value="T4">NVIDIA T4</Option>
                      <Option value="A10G">NVIDIA A10G</Option>
                      <Option value="L4">NVIDIA L4</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">Autoscaling</Divider>

              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item
                    name="autoscaling_enabled"
                    label="Enable"
                    valuePropName="checked"
                  >
                    <Switch checkedChildren="On" unCheckedChildren="Off" />
                  </Form.Item>
                </Col>
                <Col span={9}>
                  <Form.Item
                    name="autoscaling_min"
                    label="Min Replicas"
                  >
                    <InputNumber min={1} max={10} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={9}>
                  <Form.Item
                    name="autoscaling_max"
                    label="Max Replicas"
                  >
                    <InputNumber min={1} max={10} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Alert
                message="Estimated Cost"
                description={`$${(form.getFieldValue('gpu_count') || 1) * 2}/hour per replica`}
                type="info"
                showIcon
                style={{ marginTop: '16px' }}
              />

              <Button
                type="primary"
                icon={<RocketOutlined />}
                onClick={handleDeploy}
                loading={deploying}
                block
                style={{ marginTop: '24px' }}
                size="large"
              >
                Deploy Model
              </Button>
            </Form>
          </Card>
        </Col>

        {/* Right Column - Existing Deployments */}
        <Col span={10}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                Active Deployments
              </Space>
            }
          >
            {modelDeployments.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                <RocketOutlined style={{ fontSize: '32px', marginBottom: '8px' }} />
                <p>No active deployments</p>
              </div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                {modelDeployments.map((deployment) => (
                  <Card key={deployment.deployment_id} size="small">
                    <Space direction="vertical" style={{ width: '100%' }} size="small">
                      <Row justify="space-between" align="middle">
                        <Col>
                          <strong>{deployment.name}</strong>
                        </Col>
                        <Col>
                          <Tag
                            color={
                              deployment.status === 'running'
                                ? 'green'
                                : deployment.status === 'failed'
                                ? 'red'
                                : 'blue'
                            }
                          >
                            {deployment.status.toUpperCase()}
                          </Tag>
                        </Col>
                      </Row>
                      {deployment.endpoint && (
                        <div>
                          <a href={deployment.endpoint} target="_blank" rel="noopener noreferrer">
                            {deployment.endpoint}
                          </a>
                        </div>
                      )}
                      <Row gutter={16}>
                        <Col span={12}>
                          <small>Replicas: {deployment.ready_replicas}/{deployment.replicas}</small>
                        </Col>
                        <Col span={12}>
                          <small>
                            Created: {new Date(deployment.created_at).toLocaleDateString()}
                          </small>
                        </Col>
                      </Row>
                      {deployment.status === 'running' && (
                        <Progress
                          percent={100}
                          size="small"
                          status="success"
                          showInfo={false}
                        />
                      )}
                      {deployment.status === 'deploying' && (
                        <Progress
                          percent={50}
                          size="small"
                          status="active"
                          showInfo={false}
                        />
                      )}
                    </Space>
                  </Card>
                ))}
              </Space>
            )}
          </Card>

          {/* Quick Stats */}
          <Card title="Quick Stats" style={{ marginTop: '16px' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Deployments"
                  value={modelDeployments.length}
                  prefix={<DatabaseOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Running"
                  value={modelDeployments.filter((d) => d.status === 'running').length}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AIHubDeployPage;
