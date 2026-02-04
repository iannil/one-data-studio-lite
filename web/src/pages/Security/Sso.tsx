import React, { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Tag,
  Form,
  Input,
  Select,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Switch,
  Tabs,
  Steps,
} from 'antd';
import {
  KeyOutlined,
  PlusOutlined,
  EditOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { SSO_CONFIG } from '../../config/constants';

const { Title } = Typography;
const { TextArea } = Input;

type SsoType = 'oauth2' | 'ldap' | 'saml' | 'cas';
type SsoStatus = 'active' | 'inactive' | 'error';

interface SsoConfig {
  id: string;
  name: string;
  type: SsoType;
  status: SsoStatus;
  displayName: string;
  clientId?: string;
  issuer?: string;
  syncAttributes: boolean;
  autoProvision: boolean;
  defaultRole?: string;
  lastSync?: string;
  createdAt: string;
}

interface LoginHistory {
  id: string;
  userId: string;
  username: string;
  method: 'sso' | 'password' | 'ldap';
  provider?: string;
  loginTime: string;
  ip: string;
  status: 'success' | 'failed';
}

const DEMO_CONFIGS: SsoConfig[] = [
  {
    id: '1',
    name: '企业微信 SSO',
    type: 'oauth2',
    status: 'active',
    displayName: 'WeCom',
    clientId: SSO_CONFIG.WEWORK_CLIENT_ID || 'wwxxxxx',
    issuer: SSO_CONFIG.ISSUERS.WEWORK,
    syncAttributes: true,
    autoProvision: true,
    defaultRole: 'employee',
    lastSync: '2026-01-31 10:00:00',
    createdAt: '2026-01-20 10:00:00',
  },
  {
    id: '2',
    name: 'LDAP 认证',
    type: 'ldap',
    status: 'active',
    displayName: 'Company AD',
    syncAttributes: true,
    autoProvision: false,
    createdAt: '2026-01-15 09:00:00',
  },
  {
    id: '3',
    name: '钉钉集成',
    type: 'oauth2',
    status: 'inactive',
    displayName: 'DingTalk',
    clientId: SSO_CONFIG.DINGTALK_CLIENT_ID || 'dingxxxxx',
    issuer: SSO_CONFIG.ISSUERS.DINGTALK,
    syncAttributes: false,
    autoProvision: false,
    createdAt: '2026-01-10 14:00:00',
  },
];

const DEMO_HISTORY: LoginHistory[] = [
  {
    id: '1',
    userId: 'u001',
    username: 'zhangsan',
    method: 'sso',
    provider: '企业微信 SSO',
    loginTime: '2026-01-31 14:30:25',
    ip: '192.168.1.100',
    status: 'success',
  },
  {
    id: '2',
    userId: 'u002',
    username: 'lisi',
    method: 'ldap',
    provider: 'LDAP 认证',
    loginTime: '2026-01-31 14:25:10',
    ip: '192.168.1.101',
    status: 'success',
  },
  {
    id: '3',
    userId: 'unknown',
    username: 'test',
    method: 'password',
    loginTime: '2026-01-31 14:20:05',
    ip: '192.168.1.102',
    status: 'failed',
  },
];

const SSO_TYPE_OPTIONS = [
  { label: 'OAuth 2.0', value: 'oauth2' },
  { label: 'LDAP / AD', value: 'ldap' },
  { label: 'SAML 2.0', value: 'saml' },
  { label: 'CAS', value: 'cas' },
];

const ROLE_OPTIONS = [
  { label: '管理员', value: 'admin' },
  { label: '普通用户', value: 'user' },
  { label: '访客', value: 'guest' },
  { label: '开发者', value: 'developer' },
];

const Sso: React.FC = () => {
  const [configs, setConfigs] = useState<SsoConfig[]>(DEMO_CONFIGS);
  const [histories] = useState<LoginHistory[]>(DEMO_HISTORY);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SsoConfig | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingConfig(null);
    setCurrentStep(0);
    form.resetFields();
    form.setFieldsValue({
      type: 'oauth2',
      status: 'inactive',
      syncAttributes: true,
      autoProvision: false,
    });
    setModalVisible(true);
  };

  const handleEdit = (config: SsoConfig) => {
    setEditingConfig(config);
    setCurrentStep(0);
    form.setFieldsValue(config);
    setModalVisible(true);
  };

  const handleDelete = (id: string) => {
    setConfigs(configs.filter((c) => c.id !== id));
    message.success('删除成功');
  };

  const handleToggleStatus = (id: string) => {
    setConfigs((prev) =>
      prev.map((c) =>
        c.id === id
          ? { ...c, status: c.status === 'active' ? ('inactive' as const) : ('active' as const) }
          : c
      )
    );
    message.success('状态已更新');
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingConfig) {
        setConfigs((prev) =>
          prev.map((c) =>
            c.id === editingConfig.id ? { ...c, ...values } : c
          )
        );
        message.success('更新成功');
      } else {
        const newConfig: SsoConfig = {
          id: Date.now().toString(),
          name: values.name,
          type: values.type,
          status: values.status || 'inactive',
          displayName: values.displayName,
          clientId: values.clientId,
          issuer: values.issuer,
          syncAttributes: values.syncAttributes,
          autoProvision: values.autoProvision,
          defaultRole: values.defaultRole,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setConfigs([newConfig, ...configs]);
        message.success('创建成功');
      }
      setModalVisible(false);
      setCurrentStep(0);
    });
  };

  const getTypeTag = (type: SsoType) => {
    const config: Record<SsoType, { color: string; text: string }> = {
      oauth2: { color: 'blue', text: 'OAuth 2.0' },
      ldap: { color: 'green', text: 'LDAP' },
      saml: { color: 'purple', text: 'SAML' },
      cas: { color: 'orange', text: 'CAS' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    { title: '配置名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: SsoType) => getTypeTag(type),
    },
    {
      title: '显示名称',
      dataIndex: 'displayName',
      key: 'displayName',
      width: 150,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: SsoStatus, record: SsoConfig) => (
        <Switch
          size="small"
          checked={status === 'active'}
          onChange={() => handleToggleStatus(record.id)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '属性同步',
      dataIndex: 'syncAttributes',
      key: 'syncAttributes',
      width: 100,
      render: (sync: boolean) => (
        <Tag color={sync ? 'success' : 'default'}>{sync ? '是' : '否'}</Tag>
      ),
    },
    {
      title: '自动开通',
      dataIndex: 'autoProvision',
      key: 'autoProvision',
      width: 100,
      render: (auto: boolean) => (
        <Tag color={auto ? 'success' : 'default'}>{auto ? '是' : '否'}</Tag>
      ),
    },
    { title: '最后同步', dataIndex: 'lastSync', key: 'lastSync', width: 160, render: (t?: string) => t || '-' },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: SsoConfig) => (
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

  const historyColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    {
      title: '登录方式',
      dataIndex: 'method',
      key: 'method',
      render: (method: string) => <Tag>{method === 'sso' ? 'SSO' : '密码'}</Tag>,
    },
    { title: '认证源', dataIndex: 'provider', key: 'provider', render: (p?: string) => p || '-' },
    { title: '登录时间', dataIndex: 'loginTime', key: 'loginTime' },
    { title: 'IP 地址', dataIndex: 'ip', key: 'ip' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'success' ? 'success' : 'error'}>
          {status === 'success' ? '成功' : '失败'}
        </Tag>
      ),
    },
  ];

  const steps = [
    {
      title: '基本信息',
      content: (
        <>
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="如：企业微信 SSO" />
          </Form.Item>
          <Form.Item
            name="displayName"
            label="显示名称"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="登录页面显示的名称" />
          </Form.Item>
          <Form.Item
            name="type"
            label="认证类型"
            rules={[{ required: true }]}
          >
            <Select options={SSO_TYPE_OPTIONS} placeholder="选择认证类型" />
          </Form.Item>
        </>
      ),
    },
    {
      title: '连接配置',
      content: (
        <>
          <Form.Item name="clientId" label="Client ID / 应用 ID">
            <Input placeholder="应用 ID" />
          </Form.Item>
          <Form.Item name="clientSecret" label="Client Secret">
            <Input.Password placeholder="应用密钥" />
          </Form.Item>
          <Form.Item name="issuer" label="Issuer / 登录地址">
            <Input placeholder="如：https://work.weixin.qq.com" />
          </Form.Item>
          <Form.Item name="redirectUri" label="回调地址">
            <Input placeholder="如：https://your-domain.com/auth/callback" />
          </Form.Item>
        </>
      ),
    },
    {
      title: '用户映射',
      content: (
        <>
          <Form.Item name="syncAttributes" label="属性同步" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="autoProvision" label="自动开通账户" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item name="defaultRole" label="默认角色">
            <Select options={ROLE_OPTIONS} placeholder="选择默认角色" allowClear />
          </Form.Item>
          <Form.Item name="attributeMapping" label="属性映射">
            <TextArea
              rows={4}
              placeholder='{"username": "name", "email": "email", "department": "department"}'
            />
          </Form.Item>
        </>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'configs',
      label: `认证配置 (${configs.length})`,
      children: (
        <Card
          size="small"
          title="SSO 认证配置列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建配置
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={configs.map((c) => ({ ...c, key: c.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1100 }}
          />
        </Card>
      ),
    },
    {
      key: 'history',
      label: '登录历史',
      children: (
        <Card size="small" title="SSO 登录历史记录">
          <Table
            columns={historyColumns}
            dataSource={histories.map((h) => ({ ...h, key: h.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <KeyOutlined /> 统一身份认证 (SSO)
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="SSO 配置说明"
          description="支持 OAuth 2.0、LDAP/AD、SAML、CAS 等多种认证方式，配置后用户可使用企业账号直接登录系统。"
          type="info"
          showIcon
          icon={<CloudServerOutlined />}
        />
        <Tabs items={tabItems} />
      </Space>

      <Modal
        title={editingConfig ? '编辑 SSO 配置' : '新建 SSO 配置'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setCurrentStep(0);
        }}
        onOk={handleModalOk}
        width={700}
        destroyOnClose
      >
        <Steps
          current={currentStep}
          size="small"
          style={{ marginBottom: 24 }}
          items={[
            { title: "基本信息" },
            { title: "连接配置" },
            { title: "用户映射" },
          ]}
        />

        <Form form={form} layout="vertical" preserve={false}>
          {steps[currentStep].content}

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            {currentStep > 0 && (
              <Button onClick={() => setCurrentStep(currentStep - 1)}>
                上一步
              </Button>
            )}{' '}
            {currentStep < steps.length - 1 ? (
              <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
                下一步
              </Button>
            ) : (
              <Button type="primary" onClick={handleModalOk}>
                完成
              </Button>
            )}
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default Sso;
