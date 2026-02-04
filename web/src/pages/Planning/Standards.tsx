import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Form,
  Input,
  Select,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Tabs,
  Switch,
  Descriptions,
} from 'antd';
import {
  FileProtectOutlined,
  PlusOutlined,
  EditOutlined,
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  CopyOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type StandardCategory = 'naming' | 'format' | 'value' | 'security';
type StandardStatus = 'draft' | 'active' | 'deprecated';

interface DataStandard {
  id: string;
  code: string;
  name: string;
  category: StandardCategory;
  description: string;
  ruleType: string;
  ruleValue: string;
  applicableTo: string[];
  status: StandardStatus;
  version: string;
  createdBy: string;
  createdAt: string;
}

interface ValidationRule {
  id: string;
  name: string;
  field: string;
  ruleType: string;
  ruleExpression: string;
  errorMessage: string;
  enabled: boolean;
}

interface StandardTemplate {
  id: string;
  name: string;
  category: StandardCategory;
  description: string;
  standards: string[];
  isDefault: boolean;
}

const DEMO_STANDARDS: DataStandard[] = [
  {
    id: '1',
    code: 'DS-NAMING-001',
    name: '表命名规范',
    category: 'naming',
    description: '数据库表命名必须使用小写字母和下划线，以业务模块为前缀',
    ruleType: 'regex',
    ruleValue: '^[a-z][a-z0-9_]*$',
    applicableTo: ['MySQL', 'PostgreSQL'],
    status: 'active',
    version: '1.0',
    createdBy: 'admin',
    createdAt: '2025-01-15',
  },
  {
    id: '2',
    code: 'DS-FMT-001',
    name: '日期格式标准',
    category: 'format',
    description: '日期字段统一使用 YYYY-MM-DD HH:mm:ss 格式存储',
    ruleType: 'pattern',
    ruleValue: '^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}$',
    applicableTo: ['All'],
    status: 'active',
    version: '1.2',
    createdBy: 'admin',
    createdAt: '2025-02-10',
  },
  {
    id: '3',
    code: 'DS-VAL-001',
    name: '手机号校验规则',
    category: 'value',
    description: '中国大陆手机号格式校验，支持13/14/15/16/17/18/19开头',
    ruleType: 'regex',
    ruleValue: '^1[3-9]\\d{9}$',
    applicableTo: ['All'],
    status: 'active',
    version: '1.0',
    createdBy: 'data_admin',
    createdAt: '2025-03-20',
  },
  {
    id: '4',
    code: 'DS-SEC-001',
    name: '敏感字段加密标准',
    category: 'security',
    description: '身份证、银行卡号等敏感字段必须使用AES-256加密存储',
    ruleType: 'encryption',
    ruleValue: 'AES-256',
    applicableTo: ['MySQL', 'PostgreSQL', 'MongoDB'],
    status: 'active',
    version: '2.0',
    createdBy: 'security_admin',
    createdAt: '2025-04-05',
  },
  {
    id: '5',
    code: 'DS-NAMING-002',
    name: '字段命名规范',
    category: 'naming',
    description: '字段名使用驼峰命名法，避免使用保留字',
    ruleType: 'pattern',
    ruleValue: '^[a-z][a-zA-Z0-9]*$',
    applicableTo: ['Java', 'Go'],
    status: 'draft',
    version: '0.1',
    createdBy: 'dev_admin',
    createdAt: '2025-12-20',
  },
  {
    id: '6',
    code: 'DS-VAL-002',
    name: '邮箱格式校验',
    category: 'value',
    description: '标准邮箱格式校验规则',
    ruleType: 'regex',
    ruleValue: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
    applicableTo: ['All'],
    status: 'deprecated',
    version: '1.0',
    createdBy: 'admin',
    createdAt: '2025-05-10',
  },
];

const DEMO_VALIDATION_RULES: ValidationRule[] = [
  {
    id: '1',
    name: '用户名唯一性校验',
    field: 'username',
    ruleType: 'unique',
    ruleExpression: 'unique_in_table(user_info, username)',
    errorMessage: '用户名已存在',
    enabled: true,
  },
  {
    id: '2',
    name: '年龄范围校验',
    field: 'age',
    ruleType: 'range',
    ruleExpression: 'BETWEEN 0 AND 150',
    errorMessage: '年龄必须在0-150之间',
    enabled: true,
  },
  {
    id: '3',
    name: '非空校验',
    field: 'required_fields',
    ruleType: 'not_null',
    ruleExpression: 'NOT NULL',
    errorMessage: '该字段不能为空',
    enabled: true,
  },
  {
    id: '4',
    name: '金额精度校验',
    field: 'amount',
    ruleType: 'precision',
    ruleExpression: 'DECIMAL(18,2)',
    errorMessage: '金额最多保留两位小数',
    enabled: true,
  },
];

const DEMO_TEMPLATES: StandardTemplate[] = [
  {
    id: '1',
    name: '金融行业标准模板',
    category: 'security',
    description: '适用于金融行业的数据标准集合，包含命名、格式、安全等规范',
    standards: ['DS-NAMING-001', 'DS-FMT-001', 'DS-SEC-001'],
    isDefault: true,
  },
  {
    id: '2',
    name: '电商行业标准模板',
    category: 'value',
    description: '适用于电商业务的数据标准，包含订单、商品等字段规范',
    standards: ['DS-NAMING-001', 'DS-VAL-001'],
    isDefault: false,
  },
];

const CATEGORY_OPTIONS = [
  { label: '命名规范', value: 'naming' },
  { label: '格式规范', value: 'format' },
  { label: '取值规范', value: 'value' },
  { label: '安全规范', value: 'security' },
];

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '生效中', value: 'active' },
  { label: '已废弃', value: 'deprecated' },
];

const RULE_TYPE_OPTIONS = [
  { label: '正则表达式', value: 'regex' },
  { label: '格式匹配', value: 'pattern' },
  { label: '范围校验', value: 'range' },
  { label: '枚举值', value: 'enum' },
  { label: '自定义脚本', value: 'script' },
];

const Standards: React.FC = () => {
  const [standards, setStandards] = useState<DataStandard[]>(DEMO_STANDARDS);
  const [validationRules, setValidationRules] = useState<ValidationRule[]>(DEMO_VALIDATION_RULES);
  const [templates] = useState<StandardTemplate[]>(DEMO_TEMPLATES);
  const [standardModalVisible, setStandardModalVisible] = useState(false);
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [editingStandard, setEditingStandard] = useState<DataStandard | null>(null);
  const [editingRule, setEditingRule] = useState<ValidationRule | null>(null);
  const [viewingStandard, setViewingStandard] = useState<DataStandard | null>(null);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<StandardCategory | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<StandardStatus | 'all'>('all');
  const [standardForm] = Form.useForm();
  const [ruleForm] = Form.useForm();

  const handleCreateStandard = () => {
    setEditingStandard(null);
    standardForm.resetFields();
    standardForm.setFieldsValue({
      status: 'draft',
      version: '1.0',
      applicableTo: ['All'],
    });
    setStandardModalVisible(true);
  };

  const handleEditStandard = (standard: DataStandard) => {
    setEditingStandard(standard);
    standardForm.setFieldsValue(standard);
    setStandardModalVisible(true);
  };

  const handleViewStandard = (standard: DataStandard) => {
    setViewingStandard(standard);
    setViewModalVisible(true);
  };

  const handleDeleteStandard = (id: string) => {
    setStandards(standards.filter((s) => s.id !== id));
    message.success('标准删除成功');
  };

  const handleStandardModalOk = () => {
    standardForm.validateFields().then((values) => {
      if (editingStandard) {
        setStandards((prev) =>
          prev.map((s) =>
            s.id === editingStandard.id ? { ...s, ...values } : s
          )
        );
        message.success('标准更新成功');
      } else {
        const newStandard: DataStandard = {
          id: Date.now().toString(),
          code: values.code,
          name: values.name,
          category: values.category,
          description: values.description,
          ruleType: values.ruleType,
          ruleValue: values.ruleValue,
          applicableTo: values.applicableTo,
          status: values.status,
          version: values.version,
          createdBy: 'admin',
          createdAt: new Date().toLocaleDateString('zh-CN'),
        };
        setStandards([newStandard, ...standards]);
        message.success('标准创建成功');
      }
      setStandardModalVisible(false);
    });
  };

  const handleCopyStandard = (standard: DataStandard) => {
    const newStandard: DataStandard = {
      ...standard,
      id: Date.now().toString(),
      code: `${standard.code}-COPY`,
      name: `${standard.name} (副本)`,
      status: 'draft' as const,
      createdAt: new Date().toLocaleDateString('zh-CN'),
    };
    setStandards([newStandard, ...standards]);
    message.success('标准复制成功');
  };

  const handleCreateRule = () => {
    setEditingRule(null);
    ruleForm.resetFields();
    ruleForm.setFieldsValue({ enabled: true });
    setRuleModalVisible(true);
  };

  const handleEditRule = (rule: ValidationRule) => {
    setEditingRule(rule);
    ruleForm.setFieldsValue(rule);
    setRuleModalVisible(true);
  };

  const handleDeleteRule = (id: string) => {
    setValidationRules(validationRules.filter((r) => r.id !== id));
    message.success('规则删除成功');
  };

  const handleRuleModalOk = () => {
    ruleForm.validateFields().then((values) => {
      if (editingRule) {
        setValidationRules((prev) =>
          prev.map((r) =>
            r.id === editingRule.id ? { ...r, ...values } : r
          )
        );
        message.success('规则更新成功');
      } else {
        const newRule: ValidationRule = {
          id: Date.now().toString(),
          name: values.name,
          field: values.field,
          ruleType: values.ruleType,
          ruleExpression: values.ruleExpression,
          errorMessage: values.errorMessage,
          enabled: values.enabled,
        };
        setValidationRules([newRule, ...validationRules]);
        message.success('规则创建成功');
      }
      setRuleModalVisible(false);
    });
  };

  const handleToggleRule = (id: string) => {
    setValidationRules((prev) =>
      prev.map((r) =>
        r.id === id ? { ...r, enabled: !r.enabled } : r
      )
    );
    message.success('规则状态已更新');
  };

  const getCategoryTag = (category: StandardCategory) => {
    const config = {
      naming: { color: 'blue', text: '命名规范' },
      format: { color: 'green', text: '格式规范' },
      value: { color: 'orange', text: '取值规范' },
      security: { color: 'red', text: '安全规范' },
    };
    const { color, text } = config[category];
    return <Tag color={color}>{text}</Tag>;
  };

  const getStatusTag = (status: StandardStatus) => {
    const config = {
      draft: { color: 'default', text: '草稿' },
      active: { color: 'success', text: '生效中' },
      deprecated: { color: 'error', text: '已废弃' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const filteredStandards = standards.filter((standard) => {
    const matchSearch =
      !searchText ||
      standard.name.toLowerCase().includes(searchText.toLowerCase()) ||
      standard.code.toLowerCase().includes(searchText.toLowerCase());
    const matchCategory = categoryFilter === 'all' || standard.category === categoryFilter;
    const matchStatus = statusFilter === 'all' || standard.status === statusFilter;
    return matchSearch && matchCategory && matchStatus;
  });

  const standardColumns = [
    { title: '编码', dataIndex: 'code', key: 'code', width: 140 },
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category: StandardCategory) => getCategoryTag(category),
    },
    { title: '规则类型', dataIndex: 'ruleType', key: 'ruleType', width: 100 },
    { title: '版本', dataIndex: 'version', key: 'version', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: StandardStatus) => getStatusTag(status),
    },
    { title: '创建者', dataIndex: 'createdBy', key: 'createdBy', width: 100 },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 110 },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right' as const,
      render: (_: unknown, record: DataStandard) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewStandard(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopyStandard(record)}
          >
            复制
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditStandard(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDeleteStandard(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const ruleColumns = [
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { title: '目标字段', dataIndex: 'field', key: 'field' },
    { title: '规则类型', dataIndex: 'ruleType', key: 'ruleType', width: 100 },
    { title: '规则表达式', dataIndex: 'ruleExpression', key: 'ruleExpression', ellipsis: true },
    { title: '错误提示', dataIndex: 'errorMessage', key: 'errorMessage', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record: ValidationRule) => (
        <Switch
          size="small"
          checked={enabled}
          onChange={() => handleToggleRule(record.id)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: ValidationRule) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditRule(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDeleteRule(record.id)}
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
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: StandardCategory) => getCategoryTag(category),
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '包含标准',
      dataIndex: 'standards',
      key: 'standards',
      render: (standards: string[]) => standards.map((s) => <Tag key={s}>{s}</Tag>),
    },
    {
      title: '默认模板',
      dataIndex: 'isDefault',
      key: 'isDefault',
      render: (isDefault: boolean) => isDefault ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
  ];

  const tabItems = [
    {
      key: 'standards',
      label: `标准列表 (${standards.length})`,
      children: (
        <Card
          size="small"
          title="数据标准列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateStandard}>
              新建标准
            </Button>
          }
        >
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="搜索标准名称/编码..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 250 }}
              prefix={<SearchOutlined />}
            />
            <Select
              value={categoryFilter}
              onChange={setCategoryFilter}
              style={{ width: 130 }}
            >
              <Select.Option value="all">全部分类</Select.Option>
              <Select.Option value="naming">命名规范</Select.Option>
              <Select.Option value="format">格式规范</Select.Option>
              <Select.Option value="value">取值规范</Select.Option>
              <Select.Option value="security">安全规范</Select.Option>
            </Select>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="draft">草稿</Select.Option>
              <Select.Option value="active">生效中</Select.Option>
              <Select.Option value="deprecated">已废弃</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Space>
          <Table
            columns={standardColumns}
            dataSource={filteredStandards.map((s) => ({ ...s, key: s.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1200 }}
          />
        </Card>
      ),
    },
    {
      key: 'validation',
      label: `校验规则 (${validationRules.length})`,
      children: (
        <Card
          size="small"
          title="数据校验规则"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateRule}>
              新建规则
            </Button>
          }
        >
          <Alert
            message="校验规则说明"
            description="配置数据字段的校验规则，在数据写入时自动进行校验，确保数据质量。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            columns={ruleColumns}
            dataSource={validationRules.map((r) => ({ ...r, key: r.id }))}
            pagination={false}
            size="small"
            scroll={{ x: 900 }}
          />
        </Card>
      ),
    },
    {
      key: 'templates',
      label: '标准模板',
      children: (
        <Card
          size="small"
          title="标准模板管理"
          extra={
            <Button icon={<PlusOutlined />} onClick={() => setStandardModalVisible(true)}>
              新建模板
            </Button>
          }
        >
          <Alert
            message="模板说明"
            description="将多个数据标准组合成模板，便于快速应用到新项目或数据源。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            columns={templateColumns}
            dataSource={templates.map((t) => ({ ...t, key: t.id }))}
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <FileProtectOutlined /> 数据标准管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="数据标准管理说明"
          description="定义和管理数据标准规范，包括命名规范、格式规范、取值规范和安全规范。支持配置校验规则和应用标准模板。"
          type="info"
          showIcon
        />
        <Tabs items={tabItems} />
      </Space>

      {/* 标准编辑弹窗 */}
      <Modal
        title={editingStandard ? '编辑数据标准' : '新建数据标准'}
        open={standardModalVisible}
        onCancel={() => setStandardModalVisible(false)}
        onOk={handleStandardModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={standardForm} layout="vertical" preserve={false}>
          <Form.Item
            name="code"
            label="标准编码"
            rules={[{ required: true, message: '请输入标准编码' }]}
          >
            <Input placeholder="如：DS-NAMING-001" disabled={!!editingStandard} />
          </Form.Item>
          <Form.Item
            name="name"
            label="标准名称"
            rules={[{ required: true, message: '请输入标准名称' }]}
          >
            <Input placeholder="如：表命名规范" />
          </Form.Item>
          <Form.Item
            name="category"
            label="标准分类"
            rules={[{ required: true, message: '请选择标准分类' }]}
          >
            <Select options={CATEGORY_OPTIONS} placeholder="选择分类" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="标准描述" />
          </Form.Item>
          <Form.Item
            name="ruleType"
            label="规则类型"
            rules={[{ required: true, message: '请选择规则类型' }]}
          >
            <Select options={RULE_TYPE_OPTIONS} placeholder="选择规则类型" />
          </Form.Item>
          <Form.Item
            name="ruleValue"
            label="规则值/表达式"
            rules={[{ required: true, message: '请输入规则值' }]}
          >
            <TextArea rows={2} placeholder="如：^[a-z][a-z0-9_]*$" />
          </Form.Item>
          <Form.Item
            name="applicableTo"
            label="适用范围"
            rules={[{ required: true, message: '请选择适用范围' }]}
          >
            <Select mode="tags" placeholder="选择或输入适用系统" />
          </Form.Item>
          <Form.Item
            name="version"
            label="版本号"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="如：1.0" />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? '编辑校验规则' : '新建校验规则'}
        open={ruleModalVisible}
        onCancel={() => setRuleModalVisible(false)}
        onOk={handleRuleModalOk}
        destroyOnClose
      >
        <Form form={ruleForm} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="如：用户名唯一性校验" />
          </Form.Item>
          <Form.Item
            name="field"
            label="目标字段"
            rules={[{ required: true, message: '请输入目标字段' }]}
          >
            <Input placeholder="如：username" />
          </Form.Item>
          <Form.Item
            name="ruleType"
            label="规则类型"
            rules={[{ required: true, message: '请选择规则类型' }]}
          >
            <Select options={RULE_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="ruleExpression"
            label="规则表达式"
            rules={[{ required: true, message: '请输入规则表达式' }]}
          >
            <TextArea rows={2} placeholder="如：BETWEEN 0 AND 150" />
          </Form.Item>
          <Form.Item
            name="errorMessage"
            label="错误提示"
            rules={[{ required: true, message: '请输入错误提示' }]}
          >
            <Input placeholder="如：年龄必须在0-150之间" />
          </Form.Item>
          <Form.Item name="enabled" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 标准详情弹窗 */}
      <Modal
        title="数据标准详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {viewingStandard && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="标准编码" span={2}>
              {viewingStandard.code}
            </Descriptions.Item>
            <Descriptions.Item label="标准名称" span={2}>
              {viewingStandard.name}
            </Descriptions.Item>
            <Descriptions.Item label="分类">
              {getCategoryTag(viewingStandard.category)}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {getStatusTag(viewingStandard.status)}
            </Descriptions.Item>
            <Descriptions.Item label="规则类型">
              {viewingStandard.ruleType}
            </Descriptions.Item>
            <Descriptions.Item label="版本">
              {viewingStandard.version}
            </Descriptions.Item>
            <Descriptions.Item label="规则值" span={2}>
              <Text code copyable>
                {viewingStandard.ruleValue}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="适用范围" span={2}>
              {viewingStandard.applicableTo.map((s) => (
                <Tag key={s}>{s}</Tag>
              ))}
            </Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>
              {viewingStandard.description}
            </Descriptions.Item>
            <Descriptions.Item label="创建者">
              {viewingStandard.createdBy}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {viewingStandard.createdAt}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Standards;
