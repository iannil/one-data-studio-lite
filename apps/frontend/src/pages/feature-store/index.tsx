/**
 * Feature Store Page
 *
 * Provides UI for managing features, feature groups, feature views, and feature services.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Tabs,
  Button,
  Table,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Typography,
  message,
  Statistic,
  Alert,
  Tooltip,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  ApiOutlined,
  RocketOutlined,
  ReloadOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useFeatureStoreStore } from '@/stores/feature-store';
import {
  DATA_TYPE_LABELS,
  DATA_TYPE_COLORS,
  FEATURE_STORE_TYPE_LABELS,
  FEATURE_STORE_TYPE_COLORS,
  FeatureStoreType,
  DataType,
} from '@/types/feature-store';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

const FeatureStorePage: React.FC = () => {
  const {
    entities,
    featureGroups,
    features,
    featureViews,
    featureServices,
    groupsLoading,
    featuresLoading,
    viewsLoading,
    servicesLoading,
    healthStatus,
    fetchEntities,
    fetchFeatureGroups,
    fetchFeatures,
    fetchFeatureViews,
    fetchFeatureServices,
    fetchHealthStatus,
    createEntity,
    createFeatureGroup,
    createFeatureView,
    createFeatureService,
    deleteFeatureGroup,
    deployFeatureService,
  } = useFeatureStoreStore();

  const [activeTab, setActiveTab] = useState('overview');

  // Modals
  const [isEntityModalVisible, setIsEntityModalVisible] = useState(false);
  const [isGroupModalVisible, setIsGroupModalVisible] = useState(false);
  const [isViewModalVisible, setIsViewModalVisible] = useState(false);
  const [isServiceModalVisible, setIsServiceModalVisible] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);

  const [entityForm] = Form.useForm();
  const [groupForm] = Form.useForm();
  const [viewForm] = Form.useForm();
  const [serviceForm] = Form.useForm();

  useEffect(() => {
    // Initial data load
    fetchHealthStatus();
    fetchFeatureGroups();
    fetchFeatureViews();
    fetchFeatureServices();
    fetchEntities();
  }, []);

  const handleCreateEntity = async () => {
    try {
      const values = await entityForm.validateFields();
      await createEntity(values);
      message.success('Entity created successfully');
      setIsEntityModalVisible(false);
      entityForm.resetFields();
      fetchEntities();
    } catch (error: any) {
      message.error(error.message || 'Failed to create entity');
    }
  };

  const handleCreateGroup = async () => {
    try {
      const values = await groupForm.validateFields();
      await createFeatureGroup(values);
      message.success('Feature group created successfully');
      setIsGroupModalVisible(false);
      groupForm.resetFields();
      fetchFeatureGroups();
    } catch (error: any) {
      message.error(error.message || 'Failed to create feature group');
    }
  };

  const handleCreateView = async () => {
    try {
      const values = await viewForm.validateFields();
      await createFeatureView(values);
      message.success('Feature view created successfully');
      setIsViewModalVisible(false);
      viewForm.resetFields();
      fetchFeatureViews();
    } catch (error: any) {
      message.error(error.message || 'Failed to create feature view');
    }
  };

  const handleCreateService = async () => {
    try {
      const values = await serviceForm.validateFields();
      await createFeatureService(values);
      message.success('Feature service created successfully');
      setIsServiceModalVisible(false);
      serviceForm.resetFields();
      fetchFeatureServices();
    } catch (error: any) {
      message.error(error.message || 'Failed to create feature service');
    }
  };

  const handleViewFeatures = (group: any) => {
    setSelectedGroup(group);
    fetchFeatures(group.id);
    setActiveTab('features');
  };

  const handleDeployService = async (serviceId: string) => {
    try {
      await deployFeatureService(serviceId);
      message.success('Feature service deployed successfully');
    } catch (error: any) {
      message.error(error.message || 'Failed to deploy service');
    }
  };

  const groupColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.display_name || name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'store_type',
      key: 'store_type',
      render: (type: string) => {
        const config: any = {
          offline: { label: 'Offline', color: 'blue', icon: <DatabaseOutlined /> },
          online: { label: 'Online', color: 'green', icon: <ThunderboltOutlined /> },
          hybrid: { label: 'Hybrid', color: 'purple', icon: <AppstoreOutlined /> },
        }[type];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        );
      },
    },
    {
      title: 'Features',
      dataIndex: 'feature_count',
      key: 'feature_count',
      render: (count: number) => <Tag>{count} features</Tag>,
    },
    {
      title: 'Rows',
      dataIndex: 'row_count',
      key: 'row_count',
      render: (count: number) => count?.toLocaleString() || '0',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          <Tooltip title="View Features">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewFeatures(record)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => deleteFeatureGroup(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const serviceColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.display_name || name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Endpoint',
      dataIndex: 'endpoint_path',
      key: 'endpoint_path',
      render: (path: string) => (
        <Text code copyable>{path}</Text>
      ),
    },
    {
      title: 'Deployment',
      dataIndex: 'deployment_status',
      key: 'deployment_status',
      render: (status: string, record: any) => (
        <Space>
          <Tag color={status === 'deployed' ? 'success' : 'default'}>
            {status}
          </Tag>
          {status !== 'deployed' && (
            <Button
              size="small"
              type="primary"
              icon={<RocketOutlined />}
              onClick={() => handleDeployService(record.id)}
            >
              Deploy
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: 'Requests',
      dataIndex: 'total_requests',
      key: 'total_requests',
      render: (count: number) => count?.toLocaleString() || '0',
    },
    {
      title: 'Latency',
      dataIndex: 'avg_latency_ms',
      key: 'avg_latency_ms',
      render: (latency: number) => `${latency?.toFixed(2) || 0}ms`,
    },
  ];

  const featureColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.display_name || name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Data Type',
      dataIndex: 'data_type',
      key: 'data_type',
      render: (type: DataType) => (
        <Tag color={DATA_TYPE_COLORS[type]}>
          {DATA_TYPE_LABELS[type]}
        </Tag>
      ),
    },
    {
      title: 'Null %',
      dataIndex: 'null_percentage',
      key: 'null_percentage',
      render: (pct: number) => `${pct?.toFixed(1) || 0}%`,
    },
    {
      title: 'Mean',
      dataIndex: 'mean_value',
      key: 'mean_value',
      render: (val: number) => val?.toFixed(2) || 'N/A',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <DatabaseOutlined style={{ marginRight: 12 }} />
          Feature Store
        </Title>
        <Text type="secondary">
          Manage features, feature groups, and online serving for ML models
        </Text>
      </div>

      <Alert
        message="Feature Store Overview"
        description="The Feature Store provides a centralized repository for features, enabling offline storage for training and online serving for inference."
        type="info"
        showIcon
        closable
        style={{ marginBottom: 24 }}
      />

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="Overview" key="overview">
          {healthStatus && (
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Entities"
                    value={healthStatus.entities.total}
                    prefix={<AppstoreOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Feature Groups"
                    value={healthStatus.feature_groups.total}
                    prefix={<DatabaseOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Features"
                    value={healthStatus.features.total}
                    prefix={<AppstoreOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="Deployed Services"
                    value={healthStatus.feature_services.deployed}
                    prefix={<ApiOutlined />}
                    suffix={`/ ${healthStatus.feature_services.total}`}
                  />
                </Card>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Card title="Quick Actions" extra={<Button type="link">More</Button>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button
                    block
                    icon={<PlusOutlined />}
                    onClick={() => setIsEntityModalVisible(true)}
                  >
                    Create Entity
                  </Button>
                  <Button
                    block
                    icon={<PlusOutlined />}
                    onClick={() => setIsGroupModalVisible(true)}
                  >
                    Create Feature Group
                  </Button>
                  <Button
                    block
                    icon={<PlusOutlined />}
                    onClick={() => setIsViewModalVisible(true)}
                  >
                    Create Feature View
                  </Button>
                  <Button
                    block
                    icon={<PlusOutlined />}
                    onClick={() => setIsServiceModalVisible(true)}
                  >
                    Create Feature Service
                  </Button>
                </Space>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Storage Distribution">
                {healthStatus?.feature_groups.by_store_type && (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text>Offline Storage</Text>
                      <Progress
                        percent={70}
                        strokeColor="#1890ff"
                        format={() => `${healthStatus.feature_groups.by_store_type.offline || 0} groups`}
                      />
                    </div>
                    <div>
                      <Text>Online Storage</Text>
                      <Progress
                        percent={20}
                        strokeColor="#52c41a"
                        format={() => `${healthStatus.feature_groups.by_store_type.online || 0} groups`}
                      />
                    </div>
                    <div>
                      <Text>Hybrid Storage</Text>
                      <Progress
                        percent={10}
                        strokeColor="#722ed1"
                        format={() => `${healthStatus.feature_groups.by_store_type.hybrid || 0} groups`}
                      />
                    </div>
                  </Space>
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <span>
              <DatabaseOutlined />
              Feature Groups ({featureGroups.length})
            </span>
          }
          key="groups"
        >
          <Card
            title="Feature Groups"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setIsGroupModalVisible(true)}
              >
                Create Group
              </Button>
            }
          >
            <Table
              columns={groupColumns}
              dataSource={featureGroups}
              rowKey="id"
              loading={groupsLoading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <AppstoreOutlined />
              Features ({features.length})
            </span>
          }
          key="features"
        >
          <Card
            title={selectedGroup ? `Features in ${selectedGroup.display_name || selectedGroup.name}` : 'All Features'}
            extra={
              <Button
                icon={<ReloadOutlined />}
                onClick={() => selectedGroup ? fetchFeatures(selectedGroup.id) : fetchFeatures()}
              >
                Refresh
              </Button>
            }
          >
            <Table
              columns={featureColumns}
              dataSource={features}
              rowKey="id"
              loading={featuresLoading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <EyeOutlined />
              Feature Views ({featureViews.length})
            </span>
          }
          key="views"
        >
          <Card
            title="Feature Views"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setIsViewModalVisible(true)}
              >
                Create View
              </Button>
            }
          >
            <Table
              columns={[
                { title: 'Name', dataIndex: 'name', key: 'name' },
                { title: 'Type', dataIndex: 'view_type', key: 'view_type' },
                { title: 'Serving Mode', dataIndex: 'serving_mode', key: 'serving_mode' },
                { title: 'Status', dataIndex: 'status', key: 'status' },
              ]}
              dataSource={featureViews}
              rowKey="id"
              loading={viewsLoading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane
          tab={
            <span>
              <ApiOutlined />
              Feature Services ({featureServices.length})
            </span>
          }
          key="services"
        >
          <Card
            title="Feature Services"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setIsServiceModalVisible(true)}
              >
                Create Service
              </Button>
            }
          >
            <Table
              columns={serviceColumns}
              dataSource={featureServices}
              rowKey="id"
              loading={servicesLoading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* Create Entity Modal */}
      <Modal
        title="Create Entity"
        open={isEntityModalVisible}
        onOk={handleCreateEntity}
        onCancel={() => setIsEntityModalVisible(false)}
      >
        <Form form={entityForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., user, product, transaction" />
          </Form.Item>
          <Form.Item name="display_name" label="Display Name">
            <Input placeholder="Display name" />
          </Form.Item>
          <Form.Item name="entity_type" label="Entity Type">
            <Select placeholder="Select type">
              <Option value="user">User</Option>
              <Option value="product">Product</Option>
              <Option value="transaction">Transaction</Option>
              <Option value="session">Session</Option>
            </Select>
          </Form.Item>
          <Form.Item name="join_keys" label="Join Keys">
            <Select mode="tags" placeholder="Enter join keys" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Feature Group Modal */}
      <Modal
        title="Create Feature Group"
        open={isGroupModalVisible}
        onOk={handleCreateGroup}
        onCancel={() => setIsGroupModalVisible(false)}
        width={600}
      >
        <Form form={groupForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="Feature group name" />
          </Form.Item>
          <Form.Item name="display_name" label="Display Name">
            <Input placeholder="Display name" />
          </Form.Item>
          <Form.Item name="store_type" label="Storage Type" initialValue={FeatureStoreType.OFFLINE}>
            <Select>
              <Option value={FeatureStoreType.OFFLINE}>Offline (Data Warehouse)</Option>
              <Option value={FeatureStoreType.ONLINE}>Online (Low Latency)</Option>
              <Option value={FeatureStoreType.HYBRID}>Hybrid (Both)</Option>
            </Select>
          </Form.Item>
          <Form.Item name="primary_keys" label="Primary Keys">
            <Select mode="tags" placeholder="Enter primary key columns" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Feature View Modal */}
      <Modal
        title="Create Feature View"
        open={isViewModalVisible}
        onOk={handleCreateView}
        onCancel={() => setIsViewModalVisible(false)}
        width={600}
      >
        <Form form={viewForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="Feature view name" />
          </Form.Item>
          <Form.Item name="feature_group_id" label="Feature Group" rules={[{ required: true }]}>
            <Select placeholder="Select feature group">
              {featureGroups.map((g) => (
                <Option key={g.id} value={g.id}>
                  {g.display_name || g.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="feature_ids" label="Features" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="Select features">
              {features.map((f) => (
                <Option key={f.id} value={f.id}>
                  {f.display_name || f.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Feature Service Modal */}
      <Modal
        title="Create Feature Service"
        open={isServiceModalVisible}
        onOk={handleCreateService}
        onCancel={() => setIsServiceModalVisible(false)}
        width={600}
      >
        <Form form={serviceForm} layout="vertical">
          <Form.Item name="name" label="Service Name" rules={[{ required: true }]}>
            <Input placeholder="Service name" />
          </Form.Item>
          <Form.Item name="feature_view_ids" label="Feature Views" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="Select feature views">
              {featureViews.map((v) => (
                <Option key={v.id} value={v.id}>
                  {v.display_name || v.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="serving_type" label="Serving Type" initialValue="low_latency">
            <Select>
              <Option value="low_latency">Low Latency</Option>
              <Option value="batch">Batch</Option>
              <Option value="streaming">Streaming</Option>
            </Select>
          </Form.Item>
          <Form.Item name="enable_cache" label="Enable Cache" valuePropName="checked">
            <Select>
              <Option value={true}>Yes</Option>
              <Option value={false}>No</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FeatureStorePage;
