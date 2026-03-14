/**
 * New Training Job Page
 *
 * Form for creating a new distributed training job.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Form,
  Input,
  Select,
  Row,
  Col,
  Divider,
  Tag,
  Tooltip,
  message,
  Steps,
  Breadcrumb,
  Switch,
  InputNumber,
  Alert,
  Slider,
  Radio,
  Collapse,
  Modal,
  Statistic,
} from 'antd';
import {
  ArrowLeftOutlined,
  RocketOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  useTrainingStore,
  useTrainingTemplates,
  useTrainingBackends,
} from '@/stores/training';
import type {
  TrainingConfig,
  TrainingBackend,
  DistributedStrategy,
  ResourceConfig,
  TrainingTemplate,
  GPU_PRESETS,
  STRATEGY_PRESETS,
} from '@/types/training';

const { Panel } = Collapse;
const { Step } = Steps;
const { TextArea } = Input;

const NewTrainingJobPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = setSearchParams();

  const { createJob, validateConfig } = useTrainingStore();
  const templates = useTrainingTemplates();
  const backends = useTrainingBackends();

  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [creating, setCreating] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TrainingTemplate | null>(null);
  const [resourcePreset, setResourcePreset] = useState<string>('single-gpu');
  const [strategyPreset, setStrategyPreset] = useState<string>('pytorch-ddp');
  const [validationResult, setValidationResult] = useState<any>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Handle clone from URL
  useEffect(() => {
    const cloneFrom = searchParams.get('clone');
    if (cloneFrom) {
      // Would load job and populate form
      message.info('Cloning from template: ' + cloneFrom);
    }
  }, [searchParams]);

  const steps = [
    { title: 'Framework', icon: <RocketOutlined />, description: 'Choose training framework' },
    { title: 'Resources', icon: <ThunderboltOutlined />, description: 'Configure compute resources' },
    { title: 'Hyperparameters', icon: <SettingOutlined />, description: 'Set training parameters' },
    { title: 'Review', icon: <CheckCircleOutlined />, description: 'Review and submit' },
  ];

  // Handle template selection
  const handleSelectTemplate = useCallback((template: TrainingTemplate) => {
    setSelectedTemplate(template);
    form.setFieldsValue({
      backend: template.framework,
      strategy: template.strategy,
      entry_point: template.entry_point,
      hyperparameters: template.hyperparameters,
    });
    setCurrentStep(1); // Skip to resources
  }, [form]);

  // Handle resource preset
  const handleResourcePreset = (preset: string) => {
    setResourcePreset(preset);
    const config = GPU_PRESETS[preset] as Partial<ResourceConfig>;
    form.setFieldsValue({
      resources: { ...form.getFieldValue('resources'), ...config },
    });
  };

  // Handle strategy preset
  const handleStrategyPreset = (preset: string) => {
    setStrategyPreset(preset);
    const config = STRATEGY_PRESETS[preset];
    form.setFieldsValue({
      backend: config.backend,
      strategy: config.strategy,
    });

    // Update resource recommendation
    if (preset === 'pytorch-ddp' || preset === 'pytorch-fsdp') {
      form.setFieldsValue({
        num_processes_per_node: 4,
      });
    }
  };

  // Validate configuration
  const handleValidate = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const config = buildConfigFromValues(values);

      const result = await validateConfig(config);
      setValidationResult(result);

      if (!result.valid) {
        message.error('Configuration validation failed');
        return false;
      }

      setCurrentStep(3);
      return true;
    } catch (err) {
      message.error('Please fix form errors');
      return false;
    }
  }, [form, validateConfig]);

  // Build config from form values
  const buildConfigFromValues = (values: any): TrainingConfig => {
    return {
      name: values.name,
      description: values.description,
      experiment_id: values.experiment_id,
      tags: values.tags || [],
      backend: values.backend,
      strategy: values.strategy,
      entry_point: values.entry_point,
      entry_point_args: values.entry_point_args || [],
      working_dir: values.working_dir,
      hyperparameters: values.hyperparameters || {},
      data_config: values.data_config || {},
      model_config: values.model_config || {},
      num_nodes: values.num_nodes || 1,
      num_processes_per_node: values.num_processes_per_node || 1,
      master_addr: values.master_addr || 'localhost',
      master_port: values.master_port,
      checkpoint_path: values.checkpoint_path,
      resume_from_checkpoint: values.resume_from_checkpoint,
      save_frequency: values.save_frequency || 1000,
      save_total_limit: values.save_total_limit || 3,
      max_steps: values.max_steps,
      max_epochs: values.max_epochs,
      max_duration: values.max_duration,
      resources: values.resources || {
        gpu_count: 1,
        gpu_type: 'nvidia.com/gpu',
      },
      environment: values.environment || {},
      pip_packages: values.pip_packages || [],
      image: values.image,
      namespace: values.namespace || 'default',
      log_level: values.log_level || 'INFO',
    } as TrainingConfig;
  };

  // Submit job
  const handleSubmit = useCallback(async () => {
    setCreating(true);
    try {
      const values = await form.validateFields();
      const config = buildConfigFromValues(values);

      const job = await createJob(config);

      message.success('Training job created successfully');
      navigate(`/training/jobs/${job.job_id}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to create training job');
    } finally {
      setCreating(false);
    }
  }, [createJob, navigate]);

  // Framework Step Content
  const FrameworkStep = () => (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        <Col span={14}>
          <Form.Item
            label="Job Name"
            name="name"
            rules={[{ required: true, message: 'Enter job name' }]}
          >
            <Input placeholder="my-training-job" />
          </Form.Item>

          <Form.Item label="Description" name="description">
            <TextArea rows={3} placeholder="Describe your training job..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Framework"
                name="backend"
                rules={[{ required: true }]}
              >
                <Select placeholder="Select framework">
                  <Select.Option value="pytorch">PyTorch</Select.Option>
                  <Select.Option value="tensorflow">TensorFlow</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Strategy"
                name="strategy"
                rules={[{ required: true }]}
                tooltip="Distributed training strategy"
              >
                <Select placeholder="Select strategy">
                  <Select.Option value="ddp">DDP (PyTorch)</Select.Option>
                  <Select.Option value="fsdp">FSDP (PyTorch)</Select.Option>
                  <Select.Option value="deepspeed">DeepSpeed (PyTorch)</Select.Option>
                  <Select.Option value="mirrored">Mirrored (TF)</Select.Option>
                  <Select.Option value="multi_worker_mirrored">Multi-Worker (TF)</Select.Option>
                  <Select.Option value="tpu">TPU (TF)</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Training Script"
            name="entry_point"
            rules={[{ required: true, message: 'Enter training script path' }]}
            tooltip="Path to your Python training script"
          >
            <Input placeholder="train.py" />
          </Form.Item>

          <Form.Item
            label="Script Arguments"
            name="entry_point_args"
            tooltip="Command line arguments for your script"
          >
            <Select
              mode="tags"
              placeholder="Add arguments..."
              options={[
                { value: '--batch_size=32', label: '--batch_size=32' },
                { value: '--epochs=100', label: '--epochs=100' },
                { value: '--lr=0.001', label: '--lr=0.001' },
              ]}
            />
          </Form.Item>

          <Form.Item label="Working Directory" name="working_dir">
            <Input placeholder="/workspace/training" />
          </Form.Item>
        </Col>

        <Col span={10}>
          <Card title="Strategy Presets" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block={strategyPreset !== 'pytorch-ddp'}
                type={strategyPreset === 'pytorch-ddp' ? 'primary' : 'default'}
                onClick={() => handleStrategyPreset('pytorch-ddp')}
              >
                PyTorch DDP (Multi-GPU)
              </Button>
              <Button
                block={strategyPreset !== 'pytorch-fsdp'}
                type={strategyPreset === 'pytorch-fsdp' ? 'primary' : 'default'}
                onClick={() => handleStrategyPreset('pytorch-fsdp')}
              >
                PyTorch FSDP (Sharded)
              </Button>
              <Button
                block={strategyPreset !== 'tf-mirrored'}
                type={strategyPreset === 'tf-mirrored' ? 'primary' : 'default'}
                onClick={() => handleStrategyPreset('tf-mirrored')}
              >
                TensorFlow Mirrored
              </Button>
              <Button
                block={strategyPreset !== 'tf-tpu'}
                type={strategyPreset === 'tf-tpu' ? 'primary' : 'default'}
                onClick={() => handleStrategyPreset('tf-tpu')}
              >
                TensorFlow TPU
              </Button>
            </Space>
          </Card>

          <Card title="Templates" size="small" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {templates.slice(0, 4).map((template) => (
                <Button
                  key={template.id}
                  block
                  onClick={() => handleSelectTemplate(template)}
                >
                  {template.name}
                </Button>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );

  // Resources Step Content
  const ResourcesStep = () => (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        <Col span={16}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Number of Nodes"
                name="num_nodes"
                rules={[{ required: true }]}
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Processes per Node"
                name="num_processes_per_node"
                rules={[{ required: true }]}
                tooltip="Typically equals GPU count per node"
              >
                <InputNumber min={1} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider>GPU Configuration</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="GPU Count"
                name={['resources', 'gpu_count']}
                rules={[{ required: true }]}
              >
                <InputNumber min={0} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="GPU Type"
                name={['resources', 'gpu_type']}
                tooltip="Kubernetes GPU device type"
              >
                <Select>
                  <Select.Option value="nvidia.com/gpu">NVIDIA GPU</Select.Option>
                  <Select.Option value="nvidia.com/a100-80gb">A100 80GB</Select.Option>
                  <Select.Option value="nvidia.com/a100-40gb">A100 40GB</Select.Option>
                  <Select.Option value="nvidia.com/v100">V100</Select.Option>
                  <Select.Option value="nvidia.com/rtx3090">RTX 3090</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="CPU Request" name={['resources', 'cpu_request']}>
                <InputNumber min={1} max={128} style={{ width: '100%' }} addonAfter="cores" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Memory Request" name={['resources', 'memory_request']}>
                <Select>
                  <Select.Option value="8Gi">8 GB</Select.Option>
                  <Select.Option value="16Gi">16 GB</Select.Option>
                  <Select.Option value="32Gi">32 GB</Select.Option>
                  <Select.Option value="64Gi">64 GB</Select.Option>
                  <Select.Option value="128Gi">128 GB</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Col>

        <Col span={8}>
          <Card title="Resource Presets" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                block={resourcePreset !== 'single-gpu'}
                type={resourcePreset === 'single-gpu' ? 'primary' : 'default'}
                onClick={() => handleResourcePreset('single-gpu')}
              >
                Single GPU
              </Button>
              <Button
                block={resourcePreset !== 'single-a100'}
                type={resourcePreset === 'single-a100' ? 'primary' : 'default'}
                onClick={() => handleResourcePreset('single-a100')}
              >
                Single A100
              </Button>
              <Button
                block={resourcePreset !== 'quad-gpu'}
                type={resourcePreset === 'quad-gpu' ? 'primary' : 'default'}
                onClick={() => handleResourcePreset('quad-gpu')}
              >
                4x GPU (Single Node)
              </Button>
              <Button
                block={resourcePreset !== 'eight-gpu'}
                type={resourcePreset === 'eight-gpu' ? 'primary' : 'default'}
                onClick={() => handleResourcePreset('eight-gpu')}
              >
                8x GPU (Single Node)
              </Button>
              <Button
                block={resourcePreset !== 'ddp-4nodes'}
                type={resourcePreset === 'ddp-4nodes' ? 'primary' : 'default'}
                onClick={() => handleResourcePreset('ddp-4nodes')}
              >
                4 Node DDP (32x GPU)
              </Button>
            </Space>
          </Card>

          {form.getFieldValue('num_nodes') &&
           form.getFieldValue('num_processes_per_node') && (
            <Card
              title="Estimated Resources"
              size="small"
              style={{ marginTop: 16 }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="Total GPUs"
                    value={
                      form.getFieldValue('num_nodes') *
                      form.getFieldValue('num_processes_per_node')
                    }
                    suffix="×"
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="Effective Batch"
                    value={
                      (form.getFieldValue('hyperparameters')?.batch_size || 32) *
                      form.getFieldValue('num_nodes') *
                      form.getFieldValue('num_processes_per_node')
                    }
                  />
                </Col>
              </Row>
            </Card>
          )}
        </Col>
      </Row>

      <Divider orientation="left">Advanced Settings</Divider>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="Master Address" name="master_addr">
            <Input placeholder="localhost (for single node)" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Master Port" name="master_port">
            <InputNumber min={1024} max={65535} style={{ width: '100%' }} placeholder="29500" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="Docker Image" name="image">
            <Select
              showSearch
              placeholder="Select or enter image"
              options={[
                { value: 'pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime', label: 'PyTorch 2.0 (CUDA 11.7)' },
                { value: 'pytorch/pytorch:2.0.0-cuda12.1-cudnn8-runtime', label: 'PyTorch 2.0 (CUDA 12.1)' },
                { value: 'tensorflow/tensorflow:2.13.0-gpu', label: 'TensorFlow 2.13 (GPU)' },
                { value: 'tensorflow/tensorflow:2.13.0-tpu', label: 'TensorFlow 2.13 (TPU)' },
              ]}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Namespace" name="namespace">
            <Input placeholder="default" />
          </Form.Item>
        </Col>
      </Row>
    </div>
  );

  // Hyperparameters Step Content
  const HyperparametersStep = () => (
    <div style={{ padding: '24px' }}>
      <Collapse
        defaultActiveKey={['training', 'checkpointing', 'logging']}
        items={[
          {
            key: 'training',
            label: 'Training Parameters',
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="Batch Size" name={['hyperparameters', 'batch_size']}>
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="Learning Rate" name={['hyperparameters', 'lr']}>
                    <Input placeholder="0.001" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="Epochs" name="max_epochs">
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="Max Steps" name="max_steps">
                    <InputNumber min={1} style={{ width: '100%' }} placeholder="Override epochs" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="Weight Decay" name={['hyperparameters', 'weight_decay']}>
                    <Input placeholder="0.0001" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="Momentum" name={['hyperparameters', 'momentum']}>
                    <Input placeholder="0.9" />
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
          {
            key: 'checkpointing',
            label: 'Checkpointing',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="Checkpoint Path" name="checkpoint_path">
                    <Input placeholder="/checkpoints/{job_id}" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Resume From" name="resume_from_checkpoint">
                    <Input placeholder="Path to checkpoint" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Save Frequency (steps)" name="save_frequency">
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Max Checkpoints" name="save_total_limit">
                    <InputNumber min={1} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
          {
            key: 'logging',
            label: 'Logging',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="Log Level" name="log_level">
                    <Select>
                      <Select.Option value="DEBUG">DEBUG</Select.Option>
                      <Select.Option value="INFO">INFO</Select.Option>
                      <Select.Option value="WARNING">WARNING</Select.Option>
                      <Select.Option value="ERROR">ERROR</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Log Frequency (steps)" name="log_frequency">
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
          {
            key: 'optimization',
            label: 'Optimization',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="Mixed Precision">
                    <Switch />
                    <span style={{ marginLeft: 8 }}>AMP (Automatic Mixed Precision)</span>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Gradient Checkpointing">
                    <Switch />
                    <span style={{ marginLeft: 8 }}>Save memory</span>
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
        ]}
      />

      <Divider>Additional Packages</Divider>

      <Form.Item
        label="Pip Packages"
        name="pip_packages"
        tooltip="Additional Python packages to install"
      >
        <Select
          mode="tags"
          placeholder="Add packages..."
          options={[
            { value: 'transformers', label: 'transformers' },
            { value: 'datasets', label: 'datasets' },
            { value: 'accelerate', label: 'accelerate' },
            { value: 'deepspeed', label: 'deepspeed' },
            { value: 'wandb', label: 'wandb' },
          ]}
        />
      </Form.Item>

      <Divider>Environment Variables</Divider>

      <Form.List name="environment">
        {(fields, { add, remove }) => (
          <>
            {fields.map((field, index) => (
              <Row key={index} gutter={8} style={{ marginBottom: 8 }}>
                <Col flex={2}>
                  <Form.Item
                    {...field}
                    name={[field.name, 'key']}
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="Variable name" />
                  </Form.Item>
                </Col>
                <Col flex={3}>
                  <Form.Item
                    {...field}
                    name={[field.name, 'value']}
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="Variable value" />
                  </Form.Item>
                </Col>
                <Col>
                  <Button
                    type="text"
                    danger
                    icon={<MinusCircleOutlined />}
                    onClick={() => remove(field.name)}
                  />
                </Col>
              </Row>
            ))}
            <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
              Add Environment Variable
            </Button>
          </>
        )}
      </Form.List>
    </div>
  );

  // Review Step Content
  const ReviewStep = () => {
    const values = form.getFieldsValue();
    const totalGPUs = (values.num_nodes || 1) * (values.resources?.gpu_count || 1);

    return (
      <div style={{ padding: '24px' }}>
        {validationResult && validationResult.valid && (
          <Alert
            type="success"
            message="Configuration Validated"
            description={
              validationResult.estimated_cost && (
                <span>
                  Estimated cost: ${validationResult.estimated_cost.estimated_cost.toFixed(2)} USD
                  ({validationResult.estimated_cost.gpu_hours} GPU hours)
                </span>
              )
            }
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {validationResult && !validationResult.valid && (
          <Alert
            type="error"
            message="Configuration Errors"
            description={validationResult.errors?.join(', ')}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Row gutter={24}>
          <Col span={12}>
            <Card title="Job Configuration" size="small">
              <Row gutter={[8, 16]}>
                <Col span={8}>Name:</Col>
                <Col span={16}>{values.name}</Col>
                <Col span={8}>Framework:</Col>
                <Col span={16}>
                  <Tag color="blue">{values.backend}</Tag>
                  <Tag color="green">{values.strategy}</Tag>
                </Col>
                <Col span={8}>Nodes:</Col>
                <Col span={16}>{values.num_nodes}</Col>
                <Col span={8}>Processes/Node:</Col>
                <Col span={16}>{values.num_processes_per_node}</Col>
                <Col span={8}>Total GPUs:</Col>
                <Col span={16}>{totalGPUs}</Col>
                <Col span={8}>Script:</Col>
                <Col span={16}>{values.entry_point}</Col>
              </Row>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Hyperparameters" size="small">
              {values.hyperparameters && Object.keys(values.hyperparameters).length > 0 ? (
                <Row gutter={[8, 8]}>
                  {Object.entries(values.hyperparameters).map(([key, value]) => (
                    <>
                      <Col span={12}>{key}:</Col>
                      <Col span={12}>{String(value)}</Col>
                    </>
                  ))}
                </Row>
              ) : (
                <div style={{ textAlign: 'center', color: '#999' }}>No hyperparameters set</div>
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={24} style={{ marginTop: 16 }}>
          <Col span={12}>
            <Card title="Resources" size="small">
              <Row gutter={[8, 8]}>
                <Col span={12}>GPU Type:</Col>
                <Col span={12}>{values.resources?.gpu_type || '-'}</Col>
                <Col span={12}>Memory:</Col>
                <Col span={12}>{values.resources?.memory_request || '-'}</Col>
                <Col span={12}>CPU:</Col>
                <Col span={12}>{values.resources?.cpu_request || '-'}</Col>
              </Row>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Checkpointing" size="small">
              <Row gutter={[8, 8]}>
                <Col span={12}>Path:</Col>
                <Col span={12}>{values.checkpoint_path || '-'}</Col>
                <Col span={12}>Save Frequency:</Col>
                <Col span={12}>{values.save_frequency || '-'} steps</Col>
                <Col span={12}>Max Checkpoints:</Col>
                <Col span={12}>{values.save_total_limit || '-'}</Col>
              </Row>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  return (
    <div style={{ padding: '24px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Breadcrumb
          items={[
            { title: 'Training', href: '/training' },
            { title: 'New Job' },
          ]}
          style={{ marginBottom: 12 }}
        />
        <Row justify="space-between" align="middle">
          <Col>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
              <RocketOutlined /> New Training Job
            </h1>
          </Col>
          <Col>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/training')}>
              Back
            </Button>
          </Col>
        </Row>
      </div>

      {/* Steps */}
      <Card>
        <Steps current={currentStep} items={steps} />
      </Card>

      {/* Form */}
      <Card style={{ marginTop: 16, flex: 1 }}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            backend: 'pytorch',
            strategy: 'ddp',
            num_nodes: 1,
            num_processes_per_node: 1,
            master_addr: 'localhost',
            save_frequency: 1000,
            save_total_limit: 3,
            log_level: 'INFO',
            log_frequency: 100,
            namespace: 'default',
            resources: {
              gpu_count: 1,
              gpu_type: 'nvidia.com/gpu',
            },
          }}
        >
          {currentStep === 0 && <FrameworkStep />}
          {currentStep === 1 && <ResourcesStep />}
          {currentStep === 2 && <HyperparametersStep />}
          {currentStep === 3 && <ReviewStep />}
        </Form>
      </Card>

      {/* Footer Actions */}
      <Card style={{ marginTop: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            {currentStep > 0 && (
              <Button onClick={() => setCurrentStep(currentStep - 1)}>
                Previous
              </Button>
            )}
          </Col>
          <Col>
            <Space>
              {currentStep === 0 && (
                <Button onClick={() => handleValidate()}>
                  Next
                </Button>
              )}
              {currentStep === 1 && (
                <Button onClick={() => setCurrentStep(2)}>
                  Next
                </Button>
              )}
              {currentStep === 2 && (
                <Button onClick={() => handleValidate()}>
                  Review
                </Button>
              )}
              {currentStep === 3 && (
                <>
                  <Button onClick={() => setCurrentStep(2)}>
                    Previous
                  </Button>
                  <Button
                    type="primary"
                    loading={creating}
                    disabled={validationResult && !validationResult.valid}
                    onClick={handleSubmit}
                  >
                    Submit Job
                  </Button>
                </>
              )}
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default NewTrainingJobPage;
