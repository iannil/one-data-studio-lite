import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Row,
  Col,
  Statistic,
  Progress,
  Tabs,
  DatePicker,
  Switch,
} from 'antd';
import {
  TeamOutlined,
  PlusOutlined,
  EditOutlined,
  DatabaseOutlined,
  SearchOutlined,
  ReloadOutlined,
  CrownOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

type TenantStatus = 'active' | 'suspended' | 'expired';
type TenantPlan = 'free' | 'basic' | 'professional' | 'enterprise';

interface Tenant {
  id: string;
  name: string;
  code: string;
  status: TenantStatus;
  plan: TenantPlan;
  maxUsers: number;
  maxStorage: number;
  currentUsers: number;
  currentStorage: number;
  expireDate: string;
  contactPerson: string;
  contactPhone: string;
  contactEmail: string;
  createdAt: string;
}

const DEMO_TENANTS: Tenant[] = [
  {
    id: '1',
    name: '科技发展有限公司',
    code: 'TECH001',
    status: 'active',
    plan: 'enterprise',
    maxUsers: 100,
    maxStorage: 1024,
    currentUsers: 68,
    currentStorage: 756,
    expireDate: '2026-12-31',
    contactPerson: '张总',
    contactPhone: '13800138001',
    contactEmail: 'zhang@tech.com',
    createdAt: '2025-01-15',
  },
  {
    id: '2',
    name: '数据智能科技有限公司',
    code: 'DATA002',
    status: 'active',
    plan: 'professional',
    maxUsers: 50,
    maxStorage: 512,
    currentUsers: 42,
    currentStorage: 389,
    expireDate: '2026-06-30',
    contactPerson: '李经理',
    contactPhone: '13900139002',
    contactEmail: 'li@dataintel.com',
    createdAt: '2025-03-20',
  },
  {
    id: '3',
    name: '互联网创业公司',
    code: 'NET003',
    status: 'active',
    plan: 'basic',
    maxUsers: 20,
    maxStorage: 100,
    currentUsers: 15,
    currentStorage: 72,
    expireDate: '2026-03-31',
    contactPerson: '王主管',
    contactPhone: '13700137003',
    contactEmail: 'wang@netstartup.com',
    createdAt: '2025-08-10',
  },
  {
    id: '4',
    name: '咨询服务中心',
    code: 'CONS004',
    status: 'suspended',
    plan: 'free',
    maxUsers: 5,
    maxStorage: 10,
    currentUsers: 3,
    currentStorage: 5,
    expireDate: '2026-01-31',
    contactPerson: '赵老师',
    contactPhone: '13600136004',
    contactEmail: 'zhao@consult.com',
    createdAt: '2025-10-05',
  },
  {
    id: '5',
    name: '贸易集团有限公司',
    code: 'TRADE005',
    status: 'expired',
    plan: 'professional',
    maxUsers: 50,
    maxStorage: 256,
    currentUsers: 48,
    currentStorage: 245,
    expireDate: '2025-12-31',
    contactPerson: '刘总监',
    contactPhone: '13500135005',
    contactEmail: 'liu@tradegroup.com',
    createdAt: '2025-02-14',
  },
];

const STATUS_OPTIONS = [
  { label: '正常', value: 'active' },
  { label: '暂停', value: 'suspended' },
  { label: '过期', value: 'expired' },
];

const PLAN_OPTIONS = [
  { label: '免费版', value: 'free' },
  { label: '基础版', value: 'basic' },
  { label: '专业版', value: 'professional' },
  { label: '企业版', value: 'enterprise' },
];

const Tenants: React.FC = () => {
  const [tenants, setTenants] = useState<Tenant[]>(DEMO_TENANTS);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<TenantStatus | 'all'>('all');
  const [planFilter, setPlanFilter] = useState<TenantPlan | 'all'>('all');
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingTenant(null);
    form.resetFields();
    form.setFieldsValue({
      status: 'active',
      plan: 'basic',
      maxUsers: 20,
      maxStorage: 100,
      currentUsers: 0,
      currentStorage: 0,
    });
    setModalVisible(true);
  };

  const handleEdit = (tenant: Tenant) => {
    setEditingTenant(tenant);
    form.setFieldsValue(tenant);
    setModalVisible(true);
  };

  const handleDelete = (id: string) => {
    setTenants(tenants.filter((t) => t.id !== id));
    message.success('租户删除成功');
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingTenant) {
        setTenants((prev) =>
          prev.map((t) =>
            t.id === editingTenant.id ? { ...t, ...values } : t
          )
        );
        message.success('租户更新成功');
      } else {
        const newTenant: Tenant = {
          id: Date.now().toString(),
          name: values.name,
          code: values.code,
          status: values.status,
          plan: values.plan,
          maxUsers: values.maxUsers,
          maxStorage: values.maxStorage,
          currentUsers: 0,
          currentStorage: 0,
          expireDate: values.expireDate,
          contactPerson: values.contactPerson,
          contactPhone: values.contactPhone,
          contactEmail: values.contactEmail,
          createdAt: new Date().toLocaleDateString('zh-CN'),
        };
        setTenants([newTenant, ...tenants]);
        message.success('租户创建成功');
      }
      setModalVisible(false);
    });
  };

  const getStatusTag = (status: TenantStatus) => {
    const config = {
      active: { color: 'success', text: '正常' },
      suspended: { color: 'warning', text: '暂停' },
      expired: { color: 'error', text: '过期' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const getPlanTag = (plan: TenantPlan) => {
    const config = {
      free: { color: 'default', text: '免费版', icon: null },
      basic: { color: 'blue', text: '基础版', icon: null },
      professional: { color: 'purple', text: '专业版', icon: <CrownOutlined /> },
      enterprise: { color: 'gold', text: '企业版', icon: <CrownOutlined /> },
    };
    const { color, text, icon } = config[plan];
    return (
      <Tag color={color} icon={icon}>
        {text}
      </Tag>
    );
  };

  const filteredTenants = tenants.filter((tenant) => {
    const matchSearch =
      !searchText ||
      tenant.name.toLowerCase().includes(searchText.toLowerCase()) ||
      tenant.code.toLowerCase().includes(searchText.toLowerCase());
    const matchStatus = statusFilter === 'all' || tenant.status === statusFilter;
    const matchPlan = planFilter === 'all' || tenant.plan === planFilter;
    return matchSearch && matchStatus && matchPlan;
  });

  const totalTenants = tenants.length;
  const activeTenants = tenants.filter((t) => t.status === 'active').length;
  const totalUsers = tenants.reduce((sum, t) => sum + t.currentUsers, 0);
  const totalStorage = tenants.reduce((sum, t) => sum + t.currentStorage, 0);

  const columns = [
    { title: '租户名称', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: '编码', dataIndex: 'code', key: 'code', width: 100 },
    {
      title: '套餐',
      dataIndex: 'plan',
      key: 'plan',
      width: 100,
      render: (plan: TenantPlan) => getPlanTag(plan),
    },
    {
      title: '用户数',
      key: 'users',
      width: 150,
      render: (_: unknown, record: Tenant) => {
        const percent = Math.round((record.currentUsers / record.maxUsers) * 100);
        return (
          <div>
            <Text type="secondary">{record.currentUsers} / {record.maxUsers}</Text>
            <Progress
              percent={percent}
              size="small"
              status={percent >= 90 ? 'exception' : percent >= 70 ? 'active' : 'normal'}
              showInfo={false}
            />
          </div>
        );
      },
    },
    {
      title: '存储空间 (GB)',
      key: 'storage',
      width: 150,
      render: (_: unknown, record: Tenant) => {
        const percent = Math.round((record.currentStorage / record.maxStorage) * 100);
        return (
          <div>
            <Text type="secondary">{record.currentStorage} / {record.maxStorage}</Text>
            <Progress
              percent={percent}
              size="small"
              status={percent >= 90 ? 'exception' : percent >= 70 ? 'active' : 'normal'}
              showInfo={false}
            />
          </div>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: TenantStatus) => getStatusTag(status),
    },
    { title: '到期日期', dataIndex: 'expireDate', key: 'expireDate', width: 120 },
    { title: '联系人', dataIndex: 'contactPerson', key: 'contactPerson', width: 100 },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: Tenant) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="租户名称"
                rules={[{ required: true, message: '请输入租户名称' }]}
              >
                <Input placeholder="如：科技发展有限公司" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="code"
                label="租户编码"
                rules={[{ required: true, message: '请输入租户编码' }]}
              >
                <Input placeholder="如：TECH001" disabled={!!editingTenant} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="status" label="状态" rules={[{ required: true }]}>
                <Select options={STATUS_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="plan" label="套餐" rules={[{ required: true }]}>
                <Select options={PLAN_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="expireDate"
                label="到期日期"
                rules={[{ required: true, message: '请选择到期日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="contactPerson"
                label="联系人"
                rules={[{ required: true, message: '请输入联系人' }]}
              >
                <Input placeholder="如：张总" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="contactPhone"
                label="联系电话"
                rules={[{ required: true, message: '请输入联系电话' }]}
              >
                <Input placeholder="如：13800138000" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="contactEmail"
                label="联系邮箱"
                rules={[{ required: true, type: 'email', message: '邮箱格式不正确' }]}
              >
                <Input placeholder="如：zhang@tech.com" />
              </Form.Item>
            </Col>
          </Row>
        </>
      ),
    },
    {
      key: 'quota',
      label: '配额设置',
      children: (
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="maxUsers"
              label="最大用户数"
              rules={[{ required: true, message: '请输入最大用户数' }]}
            >
              <InputNumber min={1} max={1000} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="maxStorage"
              label="最大存储空间 (GB)"
              rules={[{ required: true, message: '请输入最大存储空间' }]}
            >
              <InputNumber min={1} max={10240} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
      ),
    },
    {
      key: 'features',
      label: '功能配置',
      children: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Form.Item name="enableNL2SQL" label="启用 NL2SQL" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="enableAICleaning" label="启用 AI 清洗" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="enableDataFusion" label="启用数据融合" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="enableAdvancedReport" label="启用高级报表" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <TeamOutlined /> 租户管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="租户管理说明"
          description="管理平台租户信息，包括租户基本信息、配额设置和功能配置。支持按状态和套餐筛选租户。"
          type="info"
          showIcon
        />

        {/* 统计概览 */}
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="总租户数"
                value={totalTenants}
                suffix="个"
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="活跃租户"
                value={activeTenants}
                suffix="个"
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="总用户数"
                value={totalUsers}
                suffix="人"
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="总存储使用"
                value={totalStorage}
                suffix="GB"
                prefix={<DatabaseOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 租户列表 */}
        <Card
          size="small"
          title="租户列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建租户
            </Button>
          }
        >
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="搜索租户名称/编码..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 250 }}
              prefix={<SearchOutlined />}
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="active">正常</Select.Option>
              <Select.Option value="suspended">暂停</Select.Option>
              <Select.Option value="expired">过期</Select.Option>
            </Select>
            <Select
              value={planFilter}
              onChange={setPlanFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部套餐</Select.Option>
              <Select.Option value="free">免费版</Select.Option>
              <Select.Option value="basic">基础版</Select.Option>
              <Select.Option value="professional">专业版</Select.Option>
              <Select.Option value="enterprise">企业版</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Space>
          <Table
            columns={columns}
            dataSource={filteredTenants.map((t) => ({ ...t, key: t.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1100 }}
          />
        </Card>
      </Space>

      {/* 编辑弹窗 */}
      <Modal
        title={editingTenant ? '编辑租户' : '新建租户'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Tabs items={tabItems} />
        </Form>
      </Modal>
    </div>
  );
};

export default Tenants;
