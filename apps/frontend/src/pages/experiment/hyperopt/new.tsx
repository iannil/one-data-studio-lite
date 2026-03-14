/**
 * New Hyperparameter Optimization Study Page
 *
 * Form for creating a new hyperparameter optimization study.
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
  Radio,
  InputNumber,
  Switch,
  Alert,
  Collapse,
  Modal,
  Slider,
} from 'antd';
import {
  ArrowLeftOutlined,
  RocketOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  MinusCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useHyperoptStore } from '@/stores/hyperopt';
import { useExperimentStore } from '@/stores/experiment';
import type {
  SamplerType,
  PrunerType,
  SearchSpaceConfig,
  HyperparamType,
} from '@/stores/hyperopt';

const { Step } = Steps;
const { TextArea } = Input;
const { Panel } = Collapse;

interface HyperparamField {
  key: string;
  name: string;
  type: HyperparamType;
  config: any;
}

const NewStudyPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [creating, setCreating] = useState(false);
  const [useTemplate, setUseTemplate] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');

  const { createStudy, templates, fetchTemplates } = useHyperoptStore();
  const { experiments } = useExperimentStore();

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const steps = [
    { title: 'Basic', icon: <RocketOutlined />, description: 'Basic configuration' },
    { title: 'Search Space', icon: <SettingOutlined />, description: 'Define hyperparameters' },
    { title: 'Settings', icon: <ThunderboltOutlined />, description: 'Optimization settings' },
    { title: 'Review', icon: <CheckCircleOutlined />, description: 'Review and submit' },
  ];

  const handleTemplateChange = async (templateId: string) => {
    setSelectedTemplate(templateId);
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      form.setFieldsValue({
        name: `${template.name} - ${Date.now().toString().slice(-4)}`,
        metric: template.metric,
        direction: template.direction,
        sampler: template.sampler || 'tpe',
        n_trials: template.n_trials || 100,
      });
      setUseTemplate(true);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);

      const study = await createStudy({
        name: values.name,
        experiment_id: values.experiment_id,
        project_id: values.project_id,
        metric: values.metric,
        direction: values.direction,
        sampler: values.sampler,
        pruner: values.pruner,
        n_trials: values.n_trials,
        timeout_hours: values.timeout_hours,
        n_jobs: values.n_jobs,
        n_warmup_steps: values.n_warmup_steps,
        early_stopping_rounds: values.early_stopping_rounds,
        early_stopping_threshold: values.early_stopping_threshold,
        search_space: values.search_space,
      });

      message.success('Study created successfully');
      navigate(`/experiments/hyperopt/${study.study_id}`);
    } catch (err: any) {
      message.error(err.message || 'Failed to create study');
    } finally {
      setCreating(false);
    }
  };

  // Basic Step Content
  const BasicStep = () => (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        <Col span={14}>
          <Form.Item
            label="Study Name"
            name="name"
            rules={[{ required: true, message: 'Enter study name' }]}
          >
            <Input placeholder="my-optimization-study" />
          </Form.Item>

          <Form.Item label="Description" name="description">
            <TextArea rows={3} placeholder="Describe your optimization study..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Metric"
                name="metric"
                rules={[{ required: true }]}
                tooltip="The metric to optimize"
              >
                <Select
                  placeholder="Select metric"
                  showSearch
                  options={[
                    { value: 'accuracy', label: 'Accuracy' },
                    { value: 'loss', label: 'Loss' },
                    { value: 'f1', label: 'F1 Score' },
                    { value: 'precision', label: 'Precision' },
                    { value: 'recall', label: 'Recall' },
                    { value: 'auc', label: 'AUC' },
                    { value: 'mse', label: 'MSE' },
                    { value: 'mae', label: 'MAE' },
                    { value: 'eval_loss', label: 'Eval Loss' },
                    { value: 'custom', label: 'Custom Metric' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Direction"
                name="direction"
                rules={[{ required: true }]}
                tooltip="Maximize or minimize the metric"
              >
                <Radio.Group>
                  <Radio value="maximize">Maximize</Radio>
                  <Radio value="minimize">Minimize</Radio>
                </Radio.Group>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Experiment" name="experiment_id">
            <Select
              placeholder="Associate with experiment (optional)"
              allowClear
              showSearch
              options={experiments.map((exp) => ({
                value: exp.id,
                label: exp.name,
              }))}
            />
          </Form.Item>
        </Col>

        <Col span={10}>
          <Card title="Templates" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {templates.map((template) => (
                <Button
                  key={template.id}
                  block={
                    selectedTemplate === template.id
                      ? ({ type: 'primary' })
                      : undefined
                  }
                  onClick={() => handleTemplateChange(template.id)}
                >
                  {template.name}
                </Button>
              ))}
            </Space>
          </Card>

          <Alert
            message="About Hyperparameter Optimization"
            description="Automatically find the best hyperparameters for your model using advanced optimization algorithms."
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Col>
      </Row>
    </div>
  );

  // Search Space Step Content
  const SearchSpaceStep = () => (
    <div style={{ padding: '24px' }}>
      <Form.List name="search_space_params">
        {(fields, { add, remove }) => (
          <>
            {fields.map((field, index) => (
              <Card
                key={field.key}
                size="small"
                style={{ marginBottom: 16 }}
                extra={
                  <Button
                    type="text"
                    danger
                    icon={<MinusCircleOutlined />}
                    onClick={() => remove(field.name)}
                  />
                }
              >
                <Row gutter={16}>
                  <Col span={6}>
                    <Form.Item
                      {...field}
                      name={[field.name, 'name']}
                      label="Parameter Name"
                      rules={[{ required: true }]}
                    >
                      <Input placeholder="learning_rate" />
                    </Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item
                      {...field}
                      name={[field.name, 'type']}
                      label="Type"
                      rules={[{ required: true }]}
                    >
                      <Select placeholder="Select type">
                        <Select.Option value="categorical">Categorical</Select.Option>
                        <Select.Option value="float_uniform">Float (Uniform)</Select.Option>
                        <Select.Option value="float_log_uniform">Float (Log Uniform)</Select.Option>
                        <Select.Option value="float_discrete_uniform">Float (Discrete)</Select.Option>
                        <Select.Option value="int_uniform">Int (Uniform)</Select.Option>
                        <Select.Option value="int_log_uniform">Int (Log Uniform)</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item noStyle shouldUpdate={(prev, curr) => prev.search_space_params?.[index]?.type !== curr.search_space_params?.[index]?.type}>
                      {({ getFieldValue }) => {
                        const type = getFieldValue(['search_space_params', field.name, 'type']);
                        return (
                          <>
                            {type === 'categorical' && (
                              <Form.Item
                                {...field}
                                name={[field.name, 'choices']}
                                label="Choices"
                                rules={[{ required: true }]}
                              >
                                <Select
                                  mode="tags"
                                  placeholder="Enter choices"
                                  options={[
                                    { value: 'adam', label: 'adam' },
                                    { value: 'adamw', label: 'adamw' },
                                    { value: 'sgd', label: 'sgd' },
                                    { value: 'rmsprop', label: 'rmsprop' },
                                  ]}
                                />
                              </Form.Item>
                            )}
                            {type === 'float_uniform' && (
                              <>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'low']}
                                    label="Low"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} placeholder="0.0001" />
                                  </Form.Item>
                                </Col>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'high']}
                                    label="High"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} placeholder="0.1" />
                                  </Form.Item>
                                </Col>
                              </>
                            )}
                            {type === 'float_log_uniform' && (
                              <>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'low']}
                                    label="Low (log)"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} min={0} placeholder="1e-5" />
                                  </Form.Item>
                                </Col>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'high']}
                                    label="High (log)"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} placeholder="1e-1" />
                                  </Form.Item>
                                </Col>
                              </>
                            )}
                            {type === 'float_discrete_uniform' && (
                              <Row gutter={8}>
                                <Col span={8}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'low']}
                                    label="Low"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                                <Col span={8}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'high']}
                                    label="High"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} />
                                  </Form.Item>
                                </Col>
                                <Col span={8}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'q']}
                                    label="Step"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
                                  </Form.Item>
                                </Col>
                              </Row>
                            )}
                            {type === 'int_uniform' && (
                              <>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'low']}
                                    label="Low"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} placeholder="1" />
                                  </Form.Item>
                                </Col>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'high']}
                                    label="High"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} placeholder="100" />
                                  </Form.Item>
                                </Col>
                              </>
                            )}
                            {type === 'int_log_uniform' && (
                              <>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'low']}
                                    label="Low (log)"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} min={1} placeholder="2" />
                                  </Form.Item>
                                </Col>
                                <Col span={12}>
                                  <Form.Item
                                    {...field}
                                    name={[field.name, 'high']}
                                    label="High (log)"
                                    rules={[{ required: true }]}
                                  >
                                    <InputNumber style={{ width: '100%' }} placeholder="256" />
                                  </Form.Item>
                                </Col>
                              </>
                            )}
                          </>
                        );
                      }}
                    </Form.Item>
                  </Col>
                </Row>
              </Card>
            ))}
            <Button
              type="dashed"
              onClick={() => add()}
              block
              icon={<PlusOutlined />}
            >
              Add Hyperparameter
            </Button>
          </>
        )}
      </Form.List>

      <Alert
        message="Search Space Tips"
        description={
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>Use <strong>categorical</strong> for discrete options like optimizer types</li>
            <li>Use <strong>float_log_uniform</strong> for learning rates and scale parameters</li>
            <li>Use <strong>int_uniform</strong> for batch sizes, layer counts</li>
            <li>Use <strong>pruning</strong> to stop unpromising trials early</li>
          </ul>
        }
        type="info"
        showIcon
        style={{ marginTop: 16 }}
      />
    </div>
  );

  // Settings Step Content
  const SettingsStep = () => (
    <div style={{ padding: '24px' }}>
      <Collapse
        defaultActiveKey={['sampler', 'trials']}
        items={[
          {
            key: 'sampler',
            label: 'Sampling Algorithm',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="Sampler"
                    name="sampler"
                    tooltip="Algorithm for suggesting hyperparameters"
                  >
                    <Select>
                      <Select.Option value="tpe">
                        <Space>
                          <strong>TPE</strong>
                          <span style={{ color: '#999' }}>- Best for most cases</span>
                        </Space>
                      </Select.Option>
                      <Select.Option value="random">
                        <Space>
                          <strong>Random</strong>
                          <span style={{ color: '#999' }}>- Baseline comparison</span>
                        </Space>
                      </Select.Option>
                      <Select.Option value="cmaes">
                        <Space>
                          <strong>CMA-ES</strong>
                          <span style={{ color: '#999' }}>- Continuous parameters</span>
                        </Space>
                      </Select.Option>
                      <Select.Option value="grid">
                        <Space>
                          <strong>Grid</strong>
                          <span style={{ color: '#999' }}>- Exhaustive search</span>
                        </Space>
                      </Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="Pruner"
                    name="pruner"
                    tooltip="Stop unpromising trials early"
                  >
                    <Select>
                      <Select.Option value="none">No Pruning</Select.Option>
                      <Select.Option value="median">Median Pruner</Select.Option>
                      <Select.Option value="successive_halving">Successive Halving</Select.Option>
                      <Select.Option value="hyperband">Hyperband</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
          {
            key: 'trials',
            label: 'Trial Settings',
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="Number of Trials"
                    name="n_trials"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="Timeout (hours)" name="timeout_hours">
                    <InputNumber min={0.1} max={720} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Parallel Jobs"
                    name="n_jobs"
                    tooltip="Number of parallel trials"
                  >
                    <InputNumber min={1} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
          {
            key: 'early_stopping',
            label: 'Early Stopping',
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="Warmup Steps"
                    name="n_warmup_steps"
                    tooltip="Trials before pruning starts"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Early Stopping Rounds"
                    name="early_stopping_rounds"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="Threshold"
                    name="early_stopping_threshold"
                  >
                    <InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </div>
  );

  // Review Step Content
  const ReviewStep = () => {
    const values = form.getFieldsValue();

    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="Ready to Create Study"
          description="Review your configuration before submitting the optimization study."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Row gutter={16}>
          <Col span={12}>
            <Card title="Basic Configuration" size="small">
              <Row gutter={[8, 8]}>
                <Col span={8}>Name:</Col>
                <Col span={16}>{values.name}</Col>
                <Col span={8}>Metric:</Col>
                <Col span={16}>
                  <Tag color={values.direction === 'maximize' ? 'green' : 'orange'}>
                    {values.direction}
                  </Tag> {values.metric}
                </Col>
                <Col span={8}>Sampler:</Col>
                <Col span={16}>
                  <Tag>{values.sampler?.toUpperCase()}</Tag>
                </Col>
                <Col span={8}>Pruner:</Col>
                <Col span={16}>
                  <Tag>{values.pruner || 'none'}</Tag>
                </Col>
              </Row>
            </Card>
          </Col>

          <Col span={12}>
            <Card title="Trial Settings" size="small">
              <Row gutter={[8, 8]}>
                <Col span={12}>Trials:</Col>
                <Col span={12}>{values.n_trials}</Col>
                <Col span={12}>Timeout:</Col>
                <Col span={12}>{values.timeout_hours ? `${values.timeout_hours}h` : '-'}</Col>
                <Col span={12}>Parallel Jobs:</Col>
                <Col span={12}>{values.n_jobs}</Col>
              </Row>
            </Card>
          </Col>
        </Row>

        {values.search_space_params && values.search_space_params.length > 0 && (
          <Card title="Search Space" size="small" style={{ marginTop: 16 }}>
            <Row gutter={[16, 8]}>
              {values.search_space_params.map((param: any, index: number) => (
                <Col span={8} key={index}>
                  <Tag color="blue">{param.name}</Tag>
                  <Tag>{param.type}</Tag>
                </Col>
              ))}
            </Row>
          </Card>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <Breadcrumb
          items={[
            { title: 'Experiments', href: '/experiments' },
            { title: 'Hyperparameter Optimization', href: '/experiments/hyperopt' },
            { title: 'New Study' },
          ]}
          style={{ marginBottom: 12 }}
        />
        <Row justify="space-between" align="middle">
          <Col>
            <h1 style={{ margin: 0 }}>
              <RocketOutlined /> New Optimization Study
            </h1>
          </Col>
          <Col>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/experiments/hyperopt')}>
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
      <Card style={{ marginTop: 16 }}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            direction: 'maximize',
            metric: 'accuracy',
            sampler: 'tpe',
            pruner: 'none',
            n_trials: 100,
            n_jobs: 1,
            n_warmup_steps: 10,
            early_stopping_rounds: 20,
            early_stopping_threshold: 0.0,
          }}
        >
          {currentStep === 0 && <BasicStep />}
          {currentStep === 1 && <SearchSpaceStep />}
          {currentStep === 2 && <SettingsStep />}
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
              {currentStep < 3 && (
                <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
                  Next
                </Button>
              )}
              {currentStep === 3 && (
                <Button
                  type="primary"
                  loading={creating}
                  onClick={handleSubmit}
                  icon={<RocketOutlined />}
                >
                  Create Study
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default NewStudyPage;
