/**
 * New Model Serving Service Page
 *
 * Multi-step wizard for creating new inference services.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Steps,
  Form,
  Input,
  Select,
  Button,
  Space,
  Row,
  Col,
  Switch,
  InputNumber,
  Alert,
  Descriptions,
  Typography,
  Divider,
  Tag,
  message,
  Spin,
} from 'antd';
import {
  CloudServerOutlined,
  ExperimentOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useServingStore,
} from '@/stores/serving';
import type {
  ServingPlatform,
  DeploymentMode,
  PredictorType,
  PredictorConfig,
  CreateServiceRequest,
  RESOURCE_PRESETS,
  AUTOSCALING_PRESETS,
  PLATFORM_OPTIONS,
  DEPLOYMENT_MODE_OPTIONS,
  PREDICTOR_TYPE_OPTIONS,
} from '@/types/serving';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;
const { TextArea } = Input;

const NewServicePage: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  const { createService, createABTest, createCanaryDeployment } = useServingStore();

  // Form state
  const [platform, setPlatform] = useState<ServingPlatform>(ServingPlatform.KSERVE);
  const [mode, setMode] = useState<DeploymentMode>(DeploymentMode.RAW);
  const [predictorType, setPredictorType] = useState<PredictorType>(PredictorType.SKLEARN);
  const [resourcePreset, setResourcePreset] = useState<string>('cpu-medium');
  const [autoscalingPreset, setAutoscalingPreset] = useState<string>('conservative');

  // Model variants for A/B testing
  const [abTestVariants, setAbTestVariants] = useState<Array<{
    name: string;
    model_uri: string;
    traffic_percentage: number;
  }>>([
    { name: 'Control', model_uri: '', traffic_percentage: 50 },
    { name: 'Treatment', model_uri: '', traffic_percentage: 50 },
  ]);

  // Canary config
  const [canaryConfig, setCanaryConfig] = useState({
    baseline_model_uri: '',
    canary_model_uri: '',
    initial_traffic: 10,
  });

  // Loading & validation
  const [isValidating, setIsValidating] = useState(false);
  const [formValid, setFormValid] = useState(false);

  useEffect(() => {
    // Apply presets when changed
    if (resourcePreset) {
      const preset = RESOURCE_PRESETS[resourcePreset];
      if (preset) {
        form.setFieldsValue({
          replicas: preset.replicas || 1,
          cpu_request: preset.resource_requirements?.requests?.cpu || '1000m',
          memory_request: preset.resource_requirements?.requests?.memory || '1Gi',
          cpu_limit: preset.resource_requirements?.limits?.cpu || '2000m',
          memory_limit: preset.resource_requirements?.limits?.memory || '2Gi',
        });
      }
    }
  }, [resourcePreset, form]);

  useEffect(() => {
    if (autoscalingPreset) {
      const preset = AUTOSCALING_PRESETS[autoscalingPreset];
      if (preset) {
        form.setFieldsValue({
          autoscaling_enabled: true,
          min_replicas: preset.min_replicas,
          max_replicas: preset.max_replicas,
          target_requests_per_second: preset.target_requests_per_second,
        });
      }
    }
  }, [autoscalingPreset, form]);

  const steps = [
    { title: 'Basic Info', icon: <CloudServerOutlined /> },
    { title: 'Model Config', icon: <ExperimentOutlined /> },
    { title: 'Resources', icon: <RocketOutlined /> },
    { title: 'Review', icon: <CheckCircleOutlined /> },
  ];

  // Get form values for preview
  const formValues = Form.useWatch([], form);

  const handleNext = async () => {
    try {
      await form.validateFields();
      setCurrentStep((prev) => prev + 1);
    } catch (error) {
      message.warning('Please fill in all required fields');
    }
  };

  const handlePrev = () => {
    setCurrentStep((prev) => prev - 1);
  };

  const handleSubmit = async () => {
    setIsValidating(true);
    try {
      const values = await form.validateFields();

      if (mode === DeploymentMode.RAW) {
        // Single model deployment
        const predictorConfig: PredictorConfig = {
          predictor_type: predictorType,
          model_uri: values.model_uri,
          runtime_version: values.runtime_version,
          protocol: values.protocol || 'v1',
          storage_uri: values.storage_uri,
          framework: values.framework,
          device: values.device || 'cpu',
          replicas: values.replicas || 1,
          resource_requirements: {
            requests: {
              cpu: values.cpu_request || '1000m',
              memory: values.memory_request || '1Gi',
            },
            limits: {
              cpu: values.cpu_limit || '2000m',
              memory: values.memory_limit || '2Gi',
            },
          },
          timeout: values.timeout || 60,
          env: values.env || {},
        };

        const request: CreateServiceRequest = {
          name: values.name,
          namespace: values.namespace || 'default',
          description: values.description,
          tags: values.tags || [],
          platform,
          mode,
          predictor_config: predictorConfig,
          autoscaling_enabled: values.autoscaling_enabled || false,
          min_replicas: values.min_replicas || 1,
          max_replicas: values.max_replicas || 3,
          target_requests_per_second: values.target_requests_per_second || 10,
          enable_logging: values.enable_logging !== false,
        };

        await createService(request);
        message.success('Service deployed successfully');
        navigate('/serving');

      } else if (mode === DeploymentMode.AB_TESTING) {
        // A/B testing deployment
        const request = {
          name: values.name,
          description: values.description,
          variants: abTestVariants,
          success_metric: values.success_metric,
          split_method: values.split_method,
          duration_hours: values.duration_hours,
          min_sample_size: values.min_sample_size || 100,
        };

        await createABTest(request);
        message.success('A/B test created successfully');
        navigate('/serving?tab=abtests');

      } else if (mode === DeploymentMode.CANARY) {
        // Canary deployment
        const request = {
          service_name: values.name,
          baseline_model_uri: canaryConfig.baseline_model_uri,
          canary_model_uri: canaryConfig.canary_model_uri,
          initial_traffic: canaryConfig.initial_traffic,
          strategy: values.canary_strategy || 'linear',
          steps: values.canary_steps || 5,
          duration_minutes: values.canary_duration || 60,
        };

        await createCanaryDeployment(request);
        message.success('Canary deployment created successfully');
        navigate('/serving?tab=canaries');
      }
    } catch (error: any) {
      message.error(error.message || 'Failed to deploy service');
    } finally {
      setIsValidating(false);
    }
  };

  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Card title="Basic Information">
            <Form.Item
              label="Service Name"
              name="name"
              rules={[{ required: true, message: 'Please enter service name' }]}
            >
              <Input placeholder="my-model-service" />
            </Form.Item>

            <Form.Item
              label="Namespace"
              name="namespace"
              initialValue="default"
            >
              <Input placeholder="default" />
            </Form.Item>

            <Form.Item label="Description" name="description">
              <TextArea rows={3} placeholder="Service description..." />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="Platform" required>
                  <Select
                    value={platform}
                    onChange={setPlatform}
                    options={PLATFORM_OPTIONS.map((p) => ({
                      label: p.label,
                      value: p.value,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Deployment Mode" required>
                  <Select
                    value={mode}
                    onChange={setMode}
                    options={DEPLOYMENT_MODE_OPTIONS.map((m) => ({
                      label: `${m.icon} ${m.label}`,
                      value: m.value,
                    }))}
                  />
                </Form.Item>
              </Col>
            </Row>

            {mode === DeploymentMode.AB_TESTING && (
              <Alert
                message="A/B Testing Mode"
                description="A/B testing will route a percentage of traffic to multiple model variants to compare performance."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {mode === DeploymentMode.CANARY && (
              <Alert
                message="Canary Deployment Mode"
                description="Canary deployment will gradually shift traffic from the baseline model to the new canary model."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}
          </Card>
        );

      case 1:
        return (
          <Card title="Model Configuration">
            {mode === DeploymentMode.RAW && (
              <>
                <Form.Item
                  label="Predictor Type"
                  required
                >
                  <Select
                    value={predictorType}
                    onChange={setPredictorType}
                    options={PREDICTOR_TYPE_OPTIONS.map((p) => ({
                      label: p.label,
                      value: p.value,
                    }))}
                  />
                </Form.Item>

                <Form.Item
                  label="Model URI"
                  name="model_uri"
                  rules={[{ required: true, message: 'Please enter model URI' }]}
                  extra="e.g., s3://models/my-model or pvc://model-storage/my-model"
                >
                  <Input placeholder="s3://models/my-model" />
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="Runtime Version" name="runtime_version">
                      <Input placeholder="1.15.0" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="Protocol" name="protocol" initialValue="v1">
                      <Select>
                        <Select.Option value="v1">V1</Select.Option>
                        <Select.Option value="v2">V2</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="Framework" name="framework">
                      <Input placeholder="sklearn, xgboost, pytorch, tensorflow" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="Device" name="device" initialValue="cpu">
                      <Select>
                        <Select.Option value="cpu">CPU</Select.Option>
                        <Select.Option value="gpu">GPU</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Divider>Environment Variables</Divider>
                <Form.List name="env_vars">
                  {(fields, { add, remove }) => (
                    <>
                      {fields.map(({ key, name, ...restField }) => (
                        <Row key={key} gutter={8} style={{ marginBottom: 8 }}>
                          <Col span={10}>
                            <Form.Item
                              {...restField}
                              name={[name, 'key']}
                              rules={[{ required: true, message: 'Required' }]}
                            >
                              <Input placeholder="Key" />
                            </Form.Item>
                          </Col>
                          <Col span={10}>
                            <Form.Item
                              {...restField}
                              name={[name, 'value']}
                              rules={[{ required: true, message: 'Required' }]}
                            >
                              <Input placeholder="Value" />
                            </Form.Item>
                          </Col>
                          <Col span={4}>
                            <Button onClick={() => remove(name)} danger>
                              Remove
                            </Button>
                          </Col>
                        </Row>
                      ))}
                      <Button type="dashed" onClick={() => add()} block>
                        + Add Environment Variable
                      </Button>
                    </>
                  )}
                </Form.List>
              </>
            )}

            {mode === DeploymentMode.AB_TESTING && (
              <>
                <Title level={5}>Model Variants</Title>
                {abTestVariants.map((variant, index) => (
                  <Card
                    key={index}
                    size="small"
                    style={{ marginBottom: 16 }}
                    title={`Variant ${index + 1}: ${variant.name}`}
                  >
                    <Form.Item
                      label="Model URI"
                      required
                      value={variant.model_uri}
                      onChange={(e) => {
                        const newVariants = [...abTestVariants];
                        newVariants[index].model_uri = e.target.value;
                        setAbTestVariants(newVariants);
                      }}
                    >
                      <Input placeholder="s3://models/variant-model" />
                    </Form.Item>

                    {abTestVariants.length > 1 && (
                      <Form.Item label={`Traffic Percentage (${variant.traffic_percentage}%)`}>
                        <Input
                          type="range"
                          min={0}
                          max={100}
                          value={variant.traffic_percentage}
                          onChange={(e) => {
                            const value = parseInt(e.target.value);
                            const otherIndex = index === 0 ? 1 : 0;
                            const otherValue = 100 - value;
                            const newVariants = [...abTestVariants];
                            newVariants[index].traffic_percentage = value;
                            newVariants[otherIndex].traffic_percentage = otherValue;
                            setAbTestVariants(newVariants);
                          }}
                        />
                      </Form.Item>
                    )}
                  </Card>
                ))}

                <Form.Item label="Success Metric" name="success_metric" initialValue="accuracy">
                  <Select>
                    <Select.Option value="accuracy">Accuracy (maximize)</Select.Option>
                    <Select.Option value="precision">Precision (maximize)</Select.Option>
                    <Select.Option value="recall">Recall (maximize)</Select.Option>
                    <Select.Option value="f1_score">F1 Score (maximize)</Select.Option>
                    <Select.Option value="latency">Latency (minimize)</Select.Option>
                    <Select.Option value="throughput">Throughput (maximize)</Select.Option>
                  </Select>
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="Split Method" name="split_method" initialValue="fixed">
                      <Select>
                        <Select.Option value="fixed">Fixed Split</Select.Option>
                        <Select.Option value="epsilon_greedy">Epsilon-Greedy</Select.Option>
                        <Select.Option value="thompson_sampling">Thompson Sampling</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="Duration (hours)" name="duration_hours">
                      <InputNumber min={1} max={720} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>
              </>
            )}

            {mode === DeploymentMode.CANARY && (
              <>
                <Title level={5}>Canary Configuration</Title>

                <Form.Item
                  label="Baseline Model URI"
                  required
                >
                  <Input
                    placeholder="s3://models/baseline-model"
                    value={canaryConfig.baseline_model_uri}
                    onChange={(e) =>
                      setCanaryConfig({ ...canaryConfig, baseline_model_uri: e.target.value })
                    }
                  />
                </Form.Item>

                <Form.Item
                  label="Canary (New) Model URI"
                  required
                >
                  <Input
                    placeholder="s3://models/canary-model"
                    value={canaryConfig.canary_model_uri}
                    onChange={(e) =>
                      setCanaryConfig({ ...canaryConfig, canary_model_uri: e.target.value })
                    }
                  />
                </Form.Item>

                <Form.Item label={`Initial Canary Traffic: ${canaryConfig.initial_traffic}%`}>
                  <Input
                    type="range"
                    min={1}
                    max={50}
                    value={canaryConfig.initial_traffic}
                    onChange={(e) =>
                      setCanaryConfig({ ...canaryConfig, initial_traffic: parseInt(e.target.value) })
                    }
                  />
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="Strategy" name="canary_strategy" initialValue="linear">
                      <Select>
                        <Select.Option value="linear">Linear</Select.Option>
                        <Select.Option value="exponential">Exponential</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="Number of Steps" name="canary_steps" initialValue={5}>
                      <InputNumber min={2} max={20} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item label="Total Duration (minutes)" name="canary_duration" initialValue={60}>
                  <InputNumber min={10} max={1440} style={{ width: '100%' }} />
                </Form.Item>
              </>
            )}
          </Card>
        );

      case 2:
        return (
          <Card title="Resource Configuration">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="Resource Preset">
                  <Select value={resourcePreset} onChange={setResourcePreset}>
                    <Select.Option value="cpu-small">CPU Small (1 core, 512MB)</Select.Option>
                    <Select.Option value="cpu-medium">CPU Medium (2 cores, 1GB)</Select.Option>
                    <Select.Option value="cpu-large">CPU Large (4 cores, 2GB)</Select.Option>
                    <Select.Option value="gpu-single">GPU Single (1 GPU, 2 cores, 4GB)</Select.Option>
                    <Select.Option value="gpu-quad">GPU Quad (4 GPU, 8 cores, 16GB)</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Initial Replicas" name="replicas" initialValue={1}>
                  <InputNumber min={1} max={100} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Divider>Resource Requests</Divider>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="CPU Request" name="cpu_request" initialValue="1000m">
                  <Input placeholder="1000m" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Memory Request" name="memory_request" initialValue="1Gi">
                  <Input placeholder="1Gi" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="CPU Limit" name="cpu_limit" initialValue="2000m">
                  <Input placeholder="2000m" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Memory Limit" name="memory_limit" initialValue="2Gi">
                  <Input placeholder="2Gi" />
                </Form.Item>
              </Col>
            </Row>

            <Divider>Autoscaling</Divider>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="Autoscaling Preset">
                  <Select value={autoscalingPreset} onChange={setAutoscalingPreset}>
                    <Select.Option value="conservative">Conservative (1-3 replicas)</Select.Option>
                    <Select.Option value="moderate">Moderate (2-5 replicas)</Select.Option>
                    <Select.Option value="aggressive">Aggressive (2-10 replicas)</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="Enable Autoscaling"
                  name="autoscaling_enabled"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="Min Replicas" name="min_replicas" initialValue={1}>
                  <InputNumber min={1} max={100} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Max Replicas" name="max_replicas" initialValue={3}>
                  <InputNumber min={1} max={100} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label="Target RPS"
                  name="target_requests_per_second"
                  initialValue={10}
                >
                  <InputNumber min={1} max={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              label="Enable Request Logging"
              name="enable_logging"
              valuePropName="checked"
              initialValue={true}
            >
              <Switch />
            </Form.Item>
          </Card>
        );

      case 3:
        return (
          <Card title="Review & Deploy">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Service Name" span={2}>
                {formValues?.name || '-'}
              </Descriptions.Item>

              <Descriptions.Item label="Namespace">
                {formValues?.namespace || 'default'}
              </Descriptions.Item>

              <Descriptions.Item label="Platform">
                <Tag>{platform.toUpperCase()}</Tag>
              </Descriptions.Item>

              <Descriptions.Item label="Deployment Mode" span={2}>
                {DEPLOYMENT_MODE_OPTIONS.find((m) => m.value === mode)?.label || mode}
              </Descriptions.Item>

              {mode === DeploymentMode.RAW && (
                <>
                  <Descriptions.Item label="Predictor Type">
                    {PREDICTOR_TYPE_OPTIONS.find((p) => p.value === predictorType)?.label || predictorType}
                  </Descriptions.Item>

                  <Descriptions.Item label="Model URI">
                    <Text code>{formValues?.model_uri || '-'}</Text>
                  </Descriptions.Item>

                  <Descriptions.Item label="Replicas">
                    {formValues?.replicas || 1}
                  </Descriptions.Item>

                  <Descriptions.Item label="Autoscaling">
                    {formValues?.autoscaling_enabled ? (
                      <Tag color="blue">
                        {formValues?.min_replicas}-{formValues?.max_replicas} replicas @{' '}
                        {formValues?.target_requests_per_second} RPS
                      </Tag>
                    ) : (
                      <Tag>Disabled</Tag>
                    )}
                  </Descriptions.Item>

                  <Descriptions.Item label="CPU" span={2}>
                    Request: {formValues?.cpu_request || '1000m'} / Limit:{' '}
                    {formValues?.cpu_limit || '2000m'}
                  </Descriptions.Item>

                  <Descriptions.Item label="Memory" span={2}>
                    Request: {formValues?.memory_request || '1Gi'} / Limit:{' '}
                    {formValues?.memory_limit || '2Gi'}
                  </Descriptions.Item>
                </>
              )}

              {mode === DeploymentMode.AB_TESTING && (
                <>
                  <Descriptions.Item label="Variants" span={2}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {abTestVariants.map((v, i) => (
                        <Tag key={i}>
                          {v.name}: {v.traffic_percentage}% traffic
                        </Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>

                  <Descriptions.Item label="Success Metric">
                    {formValues?.success_metric || 'accuracy'}
                  </Descriptions.Item>

                  <Descriptions.Item label="Split Method">
                    {formValues?.split_method || 'fixed'}
                  </Descriptions.Item>
                </>
              )}

              {mode === DeploymentMode.CANARY && (
                <>
                  <Descriptions.Item label="Baseline Model" span={2}>
                    <Text code>{canaryConfig.baseline_model_uri || '-'}</Text>
                  </Descriptions.Item>

                  <Descriptions.Item label="Canary Model" span={2}>
                    <Text code>{canaryConfig.canary_model_uri || '-'}</Text>
                  </Descriptions.Item>

                  <Descriptions.Item label="Initial Traffic">
                    {canaryConfig.initial_traffic}%
                  </Descriptions.Item>

                  <Descriptions.Item label="Strategy">
                    {formValues?.canary_strategy || 'linear'}
                  </Descriptions.Item>

                  <Descriptions.Item label="Steps">
                    {formValues?.canary_steps || 5}
                  </Descriptions.Item>

                  <Descriptions.Item label="Duration">
                    {formValues?.canary_duration || 60} minutes
                  </Descriptions.Item>
                </>
              )}
            </Descriptions>

            {mode === DeploymentMode.RAW && (
              <Alert
                message="Deployment Summary"
                description={`Service will be deployed with ${formValues?.replicas || 1} initial replica(s), ${
                  formValues?.autoscaling_enabled ? 'autoscaling enabled' : 'fixed replicas'
                }.`}
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </Card>
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/serving')}
        style={{ marginBottom: 24 }}
      >
        Back to Services
      </Button>

      <Card>
        <Title level={3}>Deploy New Inference Service</Title>
        <Paragraph type="secondary">
          Configure and deploy a new model inference service with support for A/B testing and canary deployments.
        </Paragraph>

        <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />

        <Form form={form} layout="vertical">
          {renderStepContent()}
        </Form>

        <Divider />

        <Row justify="space-between">
          <Col>
            {currentStep > 0 && (
              <Button onClick={handlePrev}>Previous</Button>
            )}
          </Col>
          <Col>
            <Space>
              {currentStep < steps.length - 1 ? (
                <Button type="primary" onClick={handleNext}>
                  Next <ArrowRightOutlined />
                </Button>
              ) : (
                <Button
                  type="primary"
                  onClick={handleSubmit}
                  loading={isValidating}
                  icon={<RocketOutlined />}
                >
                  Deploy Service
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default NewServicePage;
