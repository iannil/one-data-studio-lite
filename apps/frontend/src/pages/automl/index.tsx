/**
 * AutoML Page - Automated Machine Learning
 */

import React, { useEffect, useState } from "react";
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Tabs,
  Modal,
  Form,
  Input,
  Select,
  Slider,
  Switch,
  Statistic,
  Row,
  Col,
  Progress,
  message,
  Popconfirm,
} from "antd";
import {
  PlayCircleOutlined,
  StopOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  RocketOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useAutoMLStore } from "@/stores/automl";
import type {
  AutoMLExperiment,
  AutoMLTrial,
  AutoMLModel,
  ExperimentCreateRequest,
  ProblemType,
  SearchAlgorithm,
  ModelType,
  ExperimentStatus,
  TrialStatus,
} from "@/types/automl";

const { TextArea } = Input;
const { Option } = Select;

const AutoMLPage: React.FC = () => {
  const {
    experiments,
    currentExperiment,
    trials,
    models,
    healthStatus,
    experimentsLoading,
    trialsLoading,
    modelsLoading,
    fetchExperiments,
    fetchExperiment,
    createExperiment,
    deleteExperiment,
    startExperiment,
    stopExperiment,
    fetchTrials,
    fetchModels,
    deployModel,
    fetchHealthStatus,
    setCurrentExperiment,
  } = useAutoMLStore();

  const [activeTab, setActiveTab] = useState<string>("experiments");
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [trialModalVisible, setTrialModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchExperiments();
    fetchModels();
    fetchHealthStatus();
  }, [fetchExperiments, fetchModels, fetchHealthStatus]);

  const handleCreateExperiment = async (values: ExperimentCreateRequest) => {
    try {
      await createExperiment(values);
      message.success("Experiment created successfully");
      setCreateModalVisible(false);
      form.resetFields();
      await fetchExperiments();
    } catch (error) {
      message.error("Failed to create experiment");
    }
  };

  const handleStartExperiment = async (experimentId: string) => {
    try {
      await startExperiment({ experiment_id: experimentId });
      message.success("Experiment started");
      await fetchExperiments();
    } catch (error) {
      message.error("Failed to start experiment");
    }
  };

  const handleStopExperiment = async (experimentId: string) => {
    try {
      await stopExperiment(experimentId);
      message.success("Experiment stopped");
      await fetchExperiments();
    } catch (error) {
      message.error("Failed to stop experiment");
    }
  };

  const handleDeleteExperiment = async (experimentId: string) => {
    try {
      await deleteExperiment(experimentId);
      message.success("Experiment deleted");
      await fetchExperiments();
    } catch (error) {
      message.error("Failed to delete experiment");
    }
  };

  const handleViewTrials = async (experiment: AutoMLExperiment) => {
    setCurrentExperiment(experiment);
    await fetchTrials(experiment.id);
    setTrialModalVisible(true);
  };

  const handleDeployModel = async (modelId: string) => {
    try {
      await deployModel(modelId, "staging");
      message.success("Model deployed to staging");
      await fetchModels();
    } catch (error) {
      message.error("Failed to deploy model");
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: "default",
      running: "processing",
      completed: "success",
      failed: "error",
      cancelled: "warning",
      pending: "default",
    };
    return colors[status] || "default";
  };

  const getProblemTypeTag = (type: string) => {
    const colors: Record<string, string> = {
      classification: "blue",
      regression: "green",
      clustering: "purple",
      timeseries: "orange",
    };
    return <Tag color={colors[type] || "default"}>{type}</Tag>;
  };

  const experimentColumns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: AutoMLExperiment) => (
        <Space>
          <span>{name}</span>
          {record.display_name && <span className="text-gray-400">({record.display_name})</span>}
        </Space>
      ),
    },
    {
      title: "Problem Type",
      dataIndex: "problem_type",
      key: "problem_type",
      render: getProblemTypeTag,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (status: ExperimentStatus) => (
        <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: "Progress",
      dataIndex: "progress",
      key: "progress",
      render: (progress: number) => <Progress percent={Math.round(progress * 100)} size="small" />,
    },
    {
      title: "Best Score",
      dataIndex: "best_score",
      key: "best_score",
      render: (score: number | null) => (
        <span>{score !== null ? score.toFixed(4) : "-"}</span>
      ),
    },
    {
      title: "Algorithm",
      dataIndex: "search_algorithm",
      key: "search_algorithm",
      render: (algo: string) => <Tag>{algo}</Tag>,
    },
    {
      title: "Max Trials",
      dataIndex: "max_trials",
      key: "max_trials",
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, record: AutoMLExperiment) => (
        <Space>
          {record.status === "draft" || record.status === "cancelled" ? (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartExperiment(record.id)}
            >
              Start
            </Button>
          ) : record.status === "running" ? (
            <Button
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleStopExperiment(record.id)}
            >
              Stop
            </Button>
          ) : (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleStartExperiment(record.id)}
            >
              Retry
            </Button>
          )}
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewTrials(record)}
          >
            Trials
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this experiment?"
            onConfirm={() => handleDeleteExperiment(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button danger size="small" icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const trialColumns = [
    {
      title: "Trial #",
      dataIndex: "trial_number",
      key: "trial_number",
    },
    {
      title: "Model Type",
      dataIndex: "model_type",
      key: "model_type",
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (status: TrialStatus) => (
        <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: "Train Score",
      dataIndex: "train_score",
      key: "train_score",
      render: (score: number | null) => (
        <span>{score !== null ? score.toFixed(4) : "-"}</span>
      ),
    },
    {
      title: "Val Score",
      dataIndex: "val_score",
      key: "val_score",
      render: (score: number | null) => (
        <span>{score !== null ? score.toFixed(4) : "-"}</span>
      ),
    },
    {
      title: "Test Score",
      dataIndex: "test_score",
      key: "test_score",
      render: (score: number | null) => (
        <span>{score !== null ? score.toFixed(4) : "-"}</span>
      ),
    },
    {
      title: "Duration (s)",
      dataIndex: "duration_seconds",
      key: "duration_seconds",
      render: (duration: number | null) => (
        <span>{duration !== null ? duration.toFixed(2) : "-"}</span>
      ),
    },
  ];

  const modelColumns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
      render: (version: number) => <Tag>v{version}</Tag>,
    },
    {
      title: "Model Type",
      dataIndex: "model_type",
      key: "model_type",
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: "Problem Type",
      dataIndex: "problem_type",
      key: "problem_type",
      render: getProblemTypeTag,
    },
    {
      title: "Deployment",
      dataIndex: "deployment_status",
      key: "deployment_status",
      render: (status: string) => {
        const colors: Record<string, string> = {
          none: "default",
          staging: "processing",
          production: "success",
        };
        return <Tag color={colors[status]}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, record: AutoMLModel) => (
        <Space>
          {record.deployment_status === "none" && (
            <Button
              type="primary"
              size="small"
              icon={<RocketOutlined />}
              onClick={() => handleDeployModel(record.id)}
            >
              Deploy
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: "experiments",
      label: "Experiments",
      children: (
        <Card
          title="AutoML Experiments"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              New Experiment
            </Button>
          }
        >
          <Table
            columns={experimentColumns}
            dataSource={experiments}
            rowKey="id"
            loading={experimentsLoading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: "models",
      label: "Models",
      children: (
        <Card title="Trained Models">
          <Table
            columns={modelColumns}
            dataSource={models}
            rowKey="id"
            loading={modelsLoading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: "overview",
      label: "Overview",
      children: (
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Experiments"
                value={healthStatus?.experiments.total || 0}
                loading={!healthStatus}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Running Experiments"
                value={healthStatus?.experiments.running || 0}
                loading={!healthStatus}
                valueStyle={{ color: "#1890ff" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Completed Experiments"
                value={healthStatus?.experiments.completed || 0}
                loading={!healthStatus}
                valueStyle={{ color: "#52c41a" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Trials"
                value={healthStatus?.trials.total || 0}
                loading={!healthStatus}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Models"
                value={healthStatus?.models.total || 0}
                loading={!healthStatus}
              />
            </Card>
          </Col>
        </Row>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">AutoML</h1>
        <p className="text-gray-500">
          Automated Machine Learning - automated model selection and hyperparameter tuning
        </p>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      {/* Create Experiment Modal */}
      <Modal
        title="Create AutoML Experiment"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={700}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateExperiment}
          initialValues={{
            source_type: "dataframe",
            eval_metric: "accuracy",
            search_algorithm: "random",
            max_trials: 10,
            max_time_minutes: 60,
            model_types: ["xgboost", "lightgbm"],
            enable_auto_feature_engineering: true,
            enable_early_stopping: true,
            tags: [],
          }}
        >
          <Form.Item
            name="name"
            label="Experiment Name"
            rules={[{ required: true, message: "Please enter experiment name" }]}
          >
            <Input placeholder="my-experiment" />
          </Form.Item>

          <Form.Item name="display_name" label="Display Name">
            <Input placeholder="My Experiment" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Describe your experiment..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="problem_type"
                label="Problem Type"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="classification">Classification</Option>
                  <Option value="regression">Regression</Option>
                  <Option value="clustering">Clustering</Option>
                  <Option value="timeseries">Time Series</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="eval_metric"
                label="Evaluation Metric"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="accuracy">Accuracy</Option>
                  <Option value="f1">F1 Score</Option>
                  <Option value="auc">AUC</Option>
                  <Option value="mse">MSE</Option>
                  <Option value="mae">MAE</Option>
                  <Option value="r2">R²</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="target_column"
            label="Target Column"
            rules={[{ required: true }]}
          >
            <Input placeholder="target" />
          </Form.Item>

          <Form.Item
            name="feature_columns"
            label="Feature Columns"
            rules={[{ required: true }]}
          >
            <Select
              mode="tags"
              placeholder="Enter feature column names"
              tokenSeparators={[",", " "]}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="search_algorithm"
                label="Search Algorithm"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="random">Random Search</Option>
                  <Option value="bayesian">Bayesian Optimization</Option>
                  <Option value="genetic">Genetic Algorithm</Option>
                  <Option value="grid">Grid Search</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="max_trials"
                label="Max Trials"
                rules={[{ required: true }]}
              >
                <Slider min={1} max={100} marks={{ 1: "1", 50: "50", 100: "100" }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="model_types"
            label="Model Types"
            rules={[{ required: true }]}
          >
            <Select mode="multiple" placeholder="Select model types">
              <Option value="xgboost">XGBoost</Option>
              <Option value="lightgbm">LightGBM</Option>
              <Option value="random_forest">Random Forest</Option>
              <Option value="linear">Linear</Option>
              <Option value="catboost">CatBoost</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="enable_auto_feature_engineering"
            label="Auto Feature Engineering"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="enable_early_stopping"
            label="Early Stopping"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item name="tags" label="Tags">
            <Select mode="tags" placeholder="Add tags" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Trials Modal */}
      <Modal
        title={`Trials - ${currentExperiment?.name || ""}`}
        open={trialModalVisible}
        onCancel={() => setTrialModalVisible(false)}
        footer={null}
        width={900}
      >
        <Table
          columns={trialColumns}
          dataSource={trials}
          rowKey="id"
          loading={trialsLoading}
          pagination={false}
          size="small"
        />
      </Modal>
    </div>
  );
};

export default AutoMLPage;
