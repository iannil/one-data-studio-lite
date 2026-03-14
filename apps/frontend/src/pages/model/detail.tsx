/**
 * Model Detail Page
 *
 * Shows model details with version history, deployment config, and stage management.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Tag,
  Button,
  Space,
  Tooltip,
  Statistic,
  Descriptions,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Tabs,
  Drawer,
  Popconfirm,
  Progress,
} from 'antd';
import {
  ArrowLeftOutlined,
  RocketOutlined,
  DeploymentIcon,
  TagOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  RollbackOutlined,
  BranchesOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useRouter, useParams } from 'next/navigation';
import { useModelStore } from '@/stores/model';
import type { ModelVersion, RegisteredModel } from '@/stores/model';

const { TabPane } = Tabs;
const { Search } = Input;

const ModelDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const params = useParams();
  const modelName = params?.modelName as string | undefined;
  const [registerForm] = Form.useForm();
  const [deployForm] = Form.useForm();

  const {
    currentModel,
    modelVersions,
    deployments,
    loading,
    fetchModel,
    fetchModelVersions,
    registerModelVersion,
    deleteModelVersion,
    transitionModelStage,
    createDeployment,
    setCurrentVersion,
    clearError,
  } = useModelStore();

  const [registerModalOpen, setRegisterModalOpen] = useState(false);
  const [deployModalOpen, setDeployModalOpen] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null);
  const [experimentRuns, setExperimentRuns] = useState<any[]>([]);

  useEffect(() => {
    if (modelName) {
      fetchModel(modelName);
      fetchModelVersions(modelName);
    }
  }, [modelName, fetchModel, fetchModelVersions]);

  const handleRegisterVersion = async () => {
    const values = registerForm.getFieldsValue();
    setRegistering(true);
    try {
      await registerModelVersion({
        name: modelName!,
        run_id: values.run_id,
        artifact_path: values.artifact_path || 'model',
        model_type: values.model_type || 'sklearn',
        description: values.description,
      });
      message.success('Model version registered successfully');
      setRegisterModalOpen(false);
      registerForm.resetFields();
      fetchModelVersions(modelName!);
    } catch (err) {
      message.error('Failed to register model version');
    } finally {
      setRegistering(false);
    }
  };

  const handleTransitionStage = async (version: ModelVersion, stage: string) => {
    try {
      await transitionModelStage(modelName!, version.version, stage);
      message.success(`Transitioned to ${stage}`);
    } catch (err) {
      message.error('Failed to transition stage');
    }
  };

  const handleDeleteVersion = async (version: ModelVersion) => {
    try {
      await deleteModelVersion(modelName!, version.version);
      message.success('Model version deleted');
    } catch (err) {
      message.error('Failed to delete model version');
    }
  };

  const handleDeploy = async () => {
    const values = deployForm.getFieldsValue();
    setDeploying(true);
    try {
      await createDeployment({
        name: values.name,
        model_name: modelName!,
        model_version: selectedVersion!.version,
        replicas: values.replicas || 1,
        gpu_enabled: values.gpu_enabled || false,
        gpu_type: values.gpu_type,
        gpu_count: values.gpu_count || 1,
        cpu: values.cpu,
        memory: values.memory,
        endpoint: values.endpoint,
        traffic_percentage: values.traffic_percentage || 100,
        framework: values.framework || 'sklearn',
        autoscaling_enabled: values.autoscaling_enabled || false,
        autoscaling_min: values.autoscaling_min || 1,
        autoscaling_max: values.autoscaling_max || 3,
        description: values.description,
      });
      message.success('Deployment created successfully');
      setDeployModalOpen(false);
      deployForm.resetFields();
      navigate('/models?tab=deployments');
    } catch (err) {
      message.error('Failed to create deployment');
    } finally {
      setDeploying(false);
    }
  };

  const getStageTag = (stage: string) => {
    const colors: Record<string, string> = {
      'None': 'default',
      'Staging': 'blue',
      'Production': 'green',
      'Archived': 'red',
    };
    return <Tag color={colors[stage] || 'default'}>{stage}</Tag>;
  };

  const versionColumns = [
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag>v{version}</Tag>,
    },
    {
      title: 'Stage',
      dataIndex: 'current_stage',
      key: 'current_stage',
      render: (stage: string) => getStageTag(stage),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag>{status || 'READY'}</Tag>,
    },
    {
      title: 'Run',
      dataIndex: 'run_name',
      key: 'run_name',
      render: (name: string) => name || '-',
    },
    {
      title: 'Created',
      dataIndex: 'creation_time',
      key: 'creation_time',
      width: 180,
      render: (timestamp: number) => new Date(timestamp).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_: any, version: ModelVersion) => (
        <Space size="small">
          {version.current_stage !== 'Production' && (
            <>
              {version.current_stage !== 'Staging' && (
                <Tooltip title="Move to Staging">
                  <Button
                    type="text"
                    size="small"
                    onClick={() => handleTransitionStage(version, 'Staging')}
                  >
                    Staging
                  </Button>
                </Tooltip>
              )}
              <Tooltip title="Move to Production">
                <Button
                  type="text"
                  size="small"
                  onClick={() => handleTransitionStage(version, 'Production')}
                >
                  Production
                </Button>
              </Tooltip>
            </>
          )}
          {version.current_stage !== 'Archived' && (
            <Tooltip title="Archive">
              <Button
                type="text"
                size="small"
                onClick={() => handleTransitionStage(version, 'Archived')}
              >
                Archive
              </Button>
            </Tooltip>
          )}
          <Tooltip title="Deploy">
            <Button
              type="text"
              size="small"
              icon={<RocketOutlined />}
              onClick={() => {
                setSelectedVersion(version);
                setDeployModalOpen(true);
              }}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this version?"
            onConfirm={() => handleDeleteVersion(version)}
          >
            <Button type="text" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const productionVersion = modelVersions.find((v) => v.current_stage === 'Production');
  const stagingVersion = modelVersions.find((v) => v.current_stage === 'Staging');
  const activeDeployments = deployments.filter(
    (d) => d.model_name === modelName && d.status === 'running'
  );

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/models')}
          >
            Back
          </Button>
        </Col>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>{currentModel?.name}</h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            {currentModel?.description || 'No description'}
          </p>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setRegisterModalOpen(true)}
          >
            Register Version
          </Button>
        </Col>
      </Row>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Versions"
              value={modelVersions.length}
              prefix={<TagOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Production Version"
              value={productionVersion ? productionVersion.version : '-'}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Staging Version"
              value={stagingVersion ? stagingVersion.version : '-'}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active Deployments"
              value={activeDeployments.length}
              prefix={<DeploymentIcon />}
            />
          </Card>
        </Col>
      </Row>

      {/* Content Tabs */}
      <Card>
        <Tabs defaultActiveKey="versions">
          <TabPane tab={`Versions (${modelVersions.length})`} key="versions">
            <Table
              columns={versionColumns}
              dataSource={modelVersions}
              rowKey="version"
              loading={loading}
              pagination={false}
            />
          </TabPane>

          <TabPane tab={`Deployments (${activeDeployments.length})`} key="deployments">
            {activeDeployments.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                No active deployments for this model
              </div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                {activeDeployments.map((deployment) => (
                  <Card
                    key={deployment.id}
                    size="small"
                    title={deployment.name}
                    extra={
                      <Button
                        type="link"
                        onClick={() => navigate(`/models/deployments/${deployment.id}`)}
                      >
                        View Details
                      </Button>
                    }
                  >
                    <Descriptions column={3} size="small">
                      <Descriptions.Item label="Version">
                        {deployment.model_version}
                      </Descriptions.Item>
                      <Descriptions.Item label="Framework">
                        <Tag>{deployment.framework}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="Status">
                        <Tag color="green">{deployment.status}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="Replicas">
                        {deployment.replicas}
                      </Descriptions.Item>
                      <Descriptions.Item label="Traffic">
                        {deployment.traffic_percentage}%
                      </Descriptions.Item>
                      <Descriptions.Item label="GPU">
                        {deployment.gpu_enabled ? (
                          <Tag color="purple">
                            {deployment.gpu_type || 'GPU'}: {deployment.gpu_count}
                          </Tag>
                        ) : (
                          'None'
                        )}
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                ))}
              </Space>
            )}
          </TabPane>
        </Tabs>
      </Card>

      {/* Register Version Modal */}
      <Modal
        title="Register Model Version"
        open={registerModalOpen}
        onOk={handleRegisterVersion}
        onCancel={() => {
          setRegisterModalOpen(false);
          registerForm.resetFields();
        }}
        confirmLoading={registering}
        width={600}
      >
        <Form form={registerForm} layout="vertical">
          <Form.Item
            name="run_id"
            label="Run ID"
            rules={[{ required: true, message: 'Enter run ID' }]}
            tooltip="The MLflow run ID that produced the model"
          >
            <Input placeholder="run_id" />
          </Form.Item>

          <Form.Item
            name="artifact_path"
            label="Artifact Path"
            tooltip="Path to model artifact within the run"
          >
            <Input placeholder="model" />
          </Form.Item>

          <Form.Item
            name="model_type"
            label="Model Type"
            initialValue="sklearn"
          >
            <Select>
              <Select.Option value="sklearn">scikit-learn</Select.Option>
              <Select.Option value="pytorch">PyTorch</Select.Option>
              <Select.Option value="tensorflow">TensorFlow</Select.Option>
              <Select.Option value="xgboost">XGBoost</Select.Option>
              <Select.Option value="lightgbm">LightGBM</Select.Option>
              <Select.Option value="spacy">spaCy</Select.Option>
              <Select.Option value="statsmodels">Statsmodels</Select.Option>
              <Select.Option value="pyfunc">Python Function</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Describe this model version..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Deploy Modal */}
      <Modal
        title="Deploy Model"
        open={deployModalOpen}
        onOk={handleDeploy}
        onCancel={() => {
          setDeployModalOpen(false);
          deployForm.resetFields();
          setSelectedVersion(null);
        }}
        confirmLoading={deploying}
        width={600}
      >
        <Form form={deployForm} layout="vertical">
          <Form.Item
            name="name"
            label="Deployment Name"
            rules={[{ required: true, message: 'Enter deployment name' }]}
            initialValue={`${modelName}-${selectedVersion?.version || '1'}`}
          >
            <Input />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="replicas" label="Replicas" initialValue={1}>
                <Input type="number" min={1} max={10} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="traffic_percentage" label="Traffic (%)" initialValue={100}>
                <Input type="number" min={0} max={100} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Resources">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="cpu" label="CPU" initialValue="1">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="memory" label="Memory" initialValue="2Gi">
                  <Input />
                </Form.Item>
              </Col>
            </Row>
          </Form.Item>

          <Form.Item label="GPU Configuration">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="gpu_enabled" valuePropName="checked" initialValue={false}>
                  <Switch checkedChildren="Enable" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="gpu_type" label="GPU Type">
                  <Select placeholder="Select GPU type">
                    <Select.Option value="nvidia.com/gpu">NVIDIA GPU</Select.Option>
                    <Select.Option value="nvidia.com/a100">NVIDIA A100</Select.Option>
                    <Select.Option value="nvidia.com/v100">NVIDIA V100</Select.Option>
                    <Select.Option value="nvidia.com/t4">NVIDIA T4</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="gpu_count" label="GPU Count" initialValue={1}>
              <Input type="number" min={1} max={8} />
            </Form.Item>
          </Form.Item>

          <Form.Item label="Autoscaling">
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="autoscaling_enabled" valuePropName="checked" initialValue={false}>
                  <Switch checkedChildren="Enable" />
                </Form.Item>
              </Col>
              <Col span={9}>
                <Row gutter={8}>
                  <Col span={12}>
                    <Form.Item name="autoscaling_min" label="Min" initialValue={1}>
                      <Input type="number" min={1} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="autoscaling_max" label="Max" initialValue={3}>
                      <Input type="number" min={1} />
                    </Form.Item>
                  </Col>
                </Row>
              </Col>
            </Row>
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Describe this deployment..." />
          </Form.Item>

          <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
        <p style={{ margin: 0, fontSize: '12px', color: '#666' }}>
          <strong>Model:</strong> {currentModel?.name}
          <br />
          <strong>Version:</strong> v{selectedVersion?.version}
          <br />
          <strong>Run:</strong> {selectedVersion?.run_name || selectedVersion?.run_id?.substring(0, 8)}
        </p>
      </div>
        </Form>
      </Modal>
    </div>
  );
};

export default ModelDetailPage;
