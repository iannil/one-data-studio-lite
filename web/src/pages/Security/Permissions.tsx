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
  Tabs,
  Tree,
  Switch,
} from 'antd';
import {
  SafetyOutlined,
  PlusOutlined,
  EditOutlined,
  DatabaseOutlined,
  LockOutlined,
} from '@ant-design/icons';

const { Title } = Typography;
const { TextArea } = Input;

type PermissionType = 'row_level' | 'column_level' | 'table_level';
type PermissionScope = 'all' | 'database' | 'table' | 'column';

interface PermissionRule {
  id: string;
  name: string;
  description?: string;
  type: PermissionType;
  scope: PermissionScope;
  resource: string;
  filterCondition?: string;
  users: string[];
  roles: string[];
  enabled: boolean;
  createdAt: string;
}

interface PermissionTemplate {
  id: string;
  name: string;
  permissions: string[];
  isDefault: boolean;
}

const DEMO_RULES: PermissionRule[] = [
  {
    id: '1',
    name: '销售数据部门隔离',
    description: '各部门只能查看自己部门的数据',
    type: 'row_level',
    scope: 'table',
    resource: 'sales.orders',
    filterCondition: 'department_id = :user_department',
    users: [],
    roles: ['sales_staff', 'sales_manager'],
    enabled: true,
    createdAt: '2026-01-20 10:00:00',
  },
  {
    id: '2',
    name: '敏感字段脱敏',
    description: '手机号和身份证号脱敏',
    type: 'column_level',
    scope: 'column',
    resource: 'user_info.phone, user_info.id_card',
    users: [],
    roles: ['guest', 'external_user'],
    enabled: true,
    createdAt: '2026-01-15 09:00:00',
  },
  {
    id: '3',
    name: '财务数据表级控制',
    description: '只有财务角色可以访问财务相关表',
    type: 'table_level',
    scope: 'database',
    resource: 'finance_db',
    users: ['cfo'],
    roles: ['finance_team'],
    enabled: true,
    createdAt: '2026-01-10 14:00:00',
  },
];

const DEMO_TEMPLATES: PermissionTemplate[] = [
  { id: '1', name: '只读模板', permissions: ['SELECT'], isDefault: true },
  { id: '2', name: '读写模板', permissions: ['SELECT', 'INSERT', 'UPDATE'], isDefault: false },
  { id: '3', name: '完全控制模板', permissions: ['SELECT', 'INSERT', 'UPDATE', 'DELETE'], isDefault: false },
];

const PERMISSION_TYPE_OPTIONS = [
  { label: '行级权限', value: 'row_level' },
  { label: '列级权限', value: 'column_level' },
  { label: '表级权限', value: 'table_level' },
];

const SCOPE_OPTIONS = [
  { label: '全部资源', value: 'all' },
  { label: '数据库', value: 'database' },
  { label: '数据表', value: 'table' },
  { label: '字段', value: 'column' },
];

const ROLE_OPTIONS = [
  { label: '管理员', value: 'admin' },
  { label: '数据分析师', value: 'analyst' },
  { label: '开发人员', value: 'developer' },
  { label: '访客', value: 'guest' },
];

const Permissions: React.FC = () => {
  const [rules, setRules] = useState<PermissionRule[]>(DEMO_RULES);
  const [templates] = useState<PermissionTemplate[]>(DEMO_TEMPLATES);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<PermissionRule | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({
      type: 'row_level',
      scope: 'table',
      enabled: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (rule: PermissionRule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setModalVisible(true);
  };

  const handleDelete = (id: string) => {
    setRules(rules.filter((r) => r.id !== id));
    message.success('删除成功');
  };

  const handleToggleEnabled = (id: string) => {
    setRules((prev) =>
      prev.map((r) =>
        r.id === id ? { ...r, enabled: !r.enabled } : r
      )
    );
    message.success('状态已更新');
  };

  const handleModalOk = () => {
    form.validateFields().then((values) => {
      if (editingRule) {
        setRules((prev) =>
          prev.map((r) =>
            r.id === editingRule.id ? { ...r, ...values } : r
          )
        );
        message.success('更新成功');
      } else {
        const newRule: PermissionRule = {
          id: Date.now().toString(),
          name: values.name,
          description: values.description,
          type: values.type,
          scope: values.scope,
          resource: values.resource,
          filterCondition: values.filterCondition,
          users: values.users || [],
          roles: values.roles || [],
          enabled: values.enabled,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setRules([newRule, ...rules]);
        message.success('创建成功');
      }
      setModalVisible(false);
    });
  };

  const getTypeTag = (type: PermissionType) => {
    const config = {
      row_level: { color: 'blue', text: '行级' },
      column_level: { color: 'green', text: '列级' },
      table_level: { color: 'purple', text: '表级' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const getScopeTag = (scope: PermissionScope) => {
    const config = {
      all: { color: 'red', text: '全部' },
      database: { color: 'orange', text: '数据库' },
      table: { color: 'blue', text: '数据表' },
      column: { color: 'green', text: '字段' },
    };
    const { color, text } = config[scope];
    return <Tag color={color}>{text}</Tag>;
  };

  const ruleColumns = [
    { title: '规则名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '权限类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: PermissionType) => getTypeTag(type),
    },
    {
      title: '作用范围',
      dataIndex: 'scope',
      key: 'scope',
      width: 100,
      render: (scope: PermissionScope) => getScopeTag(scope),
    },
    {
      title: '资源对象',
      dataIndex: 'resource',
      key: 'resource',
      ellipsis: true,
    },
    {
      title: '过滤条件',
      dataIndex: 'filterCondition',
      key: 'filterCondition',
      ellipsis: true,
      render: (condition?: string) => condition || '-',
    },
    {
      title: '绑定角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[]) =>
        roles.map((r) => <Tag key={r} color="geekblue">{r}</Tag>),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record: PermissionRule) => (
        <Switch
          size="small"
          checked={enabled}
          onChange={() => handleToggleEnabled(record.id)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: PermissionRule) => (
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

  const templateColumns = [
    { title: '模板名称', dataIndex: 'name', key: 'name' },
    {
      title: '权限列表',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: string[]) =>
        permissions.map((p) => <Tag key={p}>{p}</Tag>),
    },
    {
      title: '默认模板',
      dataIndex: 'isDefault',
      key: 'isDefault',
      render: (isDefault: boolean) =>
        isDefault ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
  ];

  const treeData = [
    {
      title: 'databases',
      key: 'databases',
      icon: <DatabaseOutlined />,
      children: [
        {
          title: 'user_db',
          key: 'user_db',
          children: [
            { title: 'user_info', key: 'user_info' },
            { title: 'user_profile', key: 'user_profile' },
          ],
        },
        {
          title: 'sales_db',
          key: 'sales_db',
          children: [
            { title: 'orders', key: 'orders' },
            { title: 'products', key: 'products' },
          ],
        },
      ],
    },
  ];

  const tabItems = [
    {
      key: 'rules',
      label: `权限规则 (${rules.length})`,
      children: (
        <Card
          size="small"
          title="数据权限规则列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建规则
            </Button>
          }
        >
          <Table
            columns={ruleColumns}
            dataSource={rules.map((r) => ({ ...r, key: r.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1200 }}
          />
        </Card>
      ),
    },
    {
      key: 'templates',
      label: '权限模板',
      children: (
        <Card
          size="small"
          title="权限模板管理"
          extra={
            <Button icon={<PlusOutlined />} onClick={() => {}}>
              新建模板
            </Button>
          }
        >
          <Table
            columns={templateColumns}
            dataSource={templates.map((t) => ({ ...t, key: t.id }))}
            pagination={false}
            size="small"
          />
        </Card>
      ),
    },
    {
      key: 'preview',
      label: '权限预览',
      children: (
        <Card size="small" title="资源权限树">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Alert
              message="权限预览"
              description="查看各数据资源的权限分配情况"
              type="info"
              showIcon
            />
            <Tree
              showIcon
              defaultExpandAll
              treeData={treeData}
              titleRender={(nodeData: { title: string }) => {
                // Use a hash of the node title to determine "locked" state consistently
                const hash = nodeData.title.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0);
                const isLocked = hash % 2 === 0;
                return (
                  <Space>
                    <span>{nodeData.title}</span>
                    {isLocked && <LockOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />}
                  </Space>
                );
              }}
            />
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SafetyOutlined /> 数据权限管控
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="权限管控说明"
          description="支持行级、列级、表级三种数据权限控制方式，可基于用户或角色配置访问权限。"
          type="info"
          showIcon
        />
        <Tabs items={tabItems} />
      </Space>

      <Modal
        title={editingRule ? '编辑权限规则' : '新建权限规则'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="如：销售数据部门隔离" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="规则描述（可选）" />
          </Form.Item>

          <Form.Item
            name="type"
            label="权限类型"
            rules={[{ required: true }]}
          >
            <Select options={PERMISSION_TYPE_OPTIONS} placeholder="选择权限类型" />
          </Form.Item>

          <Form.Item
            name="scope"
            label="作用范围"
            rules={[{ required: true }]}
          >
            <Select options={SCOPE_OPTIONS} placeholder="选择作用范围" />
          </Form.Item>

          <Form.Item
            name="resource"
            label="资源对象"
            rules={[{ required: true, message: '请输入资源对象' }]}
          >
            <Input placeholder="如：database.table 或 table.column1,column2" />
          </Form.Item>

          <Form.Item name="filterCondition" label="过滤条件">
            <Input placeholder="如：department_id = :user_department" />
          </Form.Item>

          <Form.Item
            name="roles"
            label="绑定角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select mode="tags" options={ROLE_OPTIONS} placeholder="选择或输入角色" />
          </Form.Item>

          <Form.Item name="enabled" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Permissions;
