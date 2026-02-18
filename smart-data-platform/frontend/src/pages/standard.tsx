'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tabs,
  Descriptions,
  Badge,
  Spin,
  Progress,
  Alert,
  Tooltip,
  Collapse,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BulbOutlined,
  SafetyOutlined,
  FileTextOutlined,
  ReloadOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { standardsApi, sourcesApi, metadataApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

interface DataStandard {
  id: string;
  name: string;
  code: string;
  description?: string;
  standard_type: string;
  status: string;
  rules: Record<string, unknown>;
  applicable_domains?: string[];
  applicable_data_types?: string[];
  tags?: string[];
  department?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

interface ComplianceResult {
  standard_id: string;
  standard_name?: string;
  compliance_rate: number;
  is_compliant: boolean;
  total_records: number;
  compliant_records: number;
  violations: Array<{
    rule: string;
    count: number;
    samples: string[];
  }>;
  checked_at: string;
}

interface Suggestion {
  name: string;
  code: string;
  standard_type: string;
  rules: Record<string, unknown>;
  description: string;
  confidence: number;
}

const standardTypes = [
  { value: 'field_format', label: '字段格式' },
  { value: 'naming_convention', label: '命名规范' },
  { value: 'encoding_rule', label: '编码规则' },
  { value: 'value_range', label: '值域规范' },
  { value: 'reference_data', label: '参照数据' },
];

const statusOptions = [
  { value: 'draft', label: '草稿', color: 'default' },
  { value: 'pending_review', label: '待审核', color: 'processing' },
  { value: 'approved', label: '已批准', color: 'success' },
  { value: 'deprecated', label: '已废弃', color: 'error' },
];

export default function StandardPage() {
  const [standards, setStandards] = useState<DataStandard[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedStandard, setSelectedStandard] = useState<DataStandard | null>(null);
  const [suggestModalOpen, setSuggestModalOpen] = useState(false);
  const [complianceModalOpen, setComplianceModalOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [complianceResult, setComplianceResult] = useState<ComplianceResult | null>(null);
  const [complianceLoading, setComplianceLoading] = useState(false);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [complianceHistory, setComplianceHistory] = useState<ComplianceResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [dataSources, setDataSources] = useState<Array<{ id: string; name: string }>>([]);
  const [tables, setTables] = useState<Array<{ id: string; name: string }>>([]);
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();

  const [createForm] = Form.useForm();
  const [suggestForm] = Form.useForm();
  const [complianceForm] = Form.useForm();

  const fetchStandards = async () => {
    setLoading(true);
    try {
      const response = await standardsApi.list({
        standard_type: filterType,
        status: filterStatus,
      });
      setStandards(response.data.items);
    } catch (error) {
      message.error('获取数据标准列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchDataSources = async () => {
    try {
      const response = await sourcesApi.list();
      setDataSources(response.data);
    } catch (error) {
      message.error('获取数据源列表失败');
    }
  };

  const fetchTables = async (sourceId: string) => {
    try {
      const response = await metadataApi.listTables(sourceId);
      setTables(response.data.map((t: { id: string; table_name: string }) => ({ id: t.id, name: t.table_name })));
    } catch (error) {
      message.error('获取表列表失败');
    }
  };

  useEffect(() => {
    fetchStandards();
    fetchDataSources();
  }, [filterType, filterStatus]);

  const handleCreate = async (values: Record<string, unknown>) => {
    try {
      const rulesJson = typeof values.rules === 'string' ? JSON.parse(values.rules as string) : values.rules;
      await standardsApi.create({
        name: values.name as string,
        code: values.code as string,
        description: values.description as string | undefined,
        standard_type: values.standard_type as string,
        rules: rulesJson,
        applicable_domains: values.applicable_domains as string[] | undefined,
        applicable_data_types: values.applicable_data_types as string[] | undefined,
        tags: values.tags as string[] | undefined,
        department: values.department as string | undefined,
      });
      message.success('数据标准创建成功');
      setCreateModalOpen(false);
      createForm.resetFields();
      fetchStandards();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '创建失败');
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await standardsApi.approve(id);
      message.success('标准已批准');
      fetchStandards();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '批准失败');
    }
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此数据标准吗？只有草稿状态的标准可以删除。',
      onOk: async () => {
        try {
          await standardsApi.delete(id);
          message.success('删除成功');
          fetchStandards();
        } catch (error: unknown) {
          const err = error as { response?: { data?: { detail?: string } } };
          message.error(err.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const handleSuggest = async (values: { source_id: string; table_name: string }) => {
    setSuggestLoading(true);
    try {
      const response = await standardsApi.suggest({
        source_id: values.source_id,
        table_name: values.table_name,
      });
      setSuggestions(response.data.suggestions || []);
      message.success(`AI 生成了 ${response.data.suggestions?.length || 0} 个建议`);
    } catch (error) {
      message.error('获取 AI 建议失败');
    } finally {
      setSuggestLoading(false);
    }
  };

  const handleCreateFromSuggestion = async (suggestion: Suggestion) => {
    try {
      await standardsApi.createFromSuggestion({ ...suggestion });
      message.success('从建议创建标准成功');
      setSuggestModalOpen(false);
      fetchStandards();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '创建失败');
    }
  };

  const handleCheckCompliance = async (values: {
    standard_id: string;
    source_id: string;
    table_name: string;
    column_name?: string;
  }) => {
    setComplianceLoading(true);
    try {
      const response = await standardsApi.checkCompliance(values);
      setComplianceResult(response.data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '合规性检查失败');
    } finally {
      setComplianceLoading(false);
    }
  };

  const handleViewHistory = async (standardId?: string) => {
    setHistoryLoading(true);
    setHistoryModalOpen(true);
    try {
      const response = await standardsApi.getComplianceHistory({
        standard_id: standardId,
        limit: 50,
      });
      setComplianceHistory(response.data.items);
    } catch (error) {
      message.error('获取历史记录失败');
    } finally {
      setHistoryLoading(false);
    }
  };

  const getStatusInfo = (status: string) => {
    return statusOptions.find((s) => s.value === status) || { label: status, color: 'default' };
  };

  const getTypeLabel = (type: string) => {
    return standardTypes.find((t) => t.value === type)?.label || type;
  };

  const columns: ColumnsType<DataStandard> = [
    {
      title: '标准名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <FileTextOutlined />
          <a onClick={() => {
            setSelectedStandard(record);
            setDetailModalOpen(true);
          }}>{name}</a>
        </Space>
      ),
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      render: (code) => <Tag>{code}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'standard_type',
      key: 'standard_type',
      render: (type) => <Tag color="blue">{getTypeLabel(type)}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const info = getStatusInfo(status);
        return <Badge status={info.color as 'default' | 'processing' | 'success' | 'error'} text={info.label} />;
      },
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (v) => `v${v}`,
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[] | undefined) => tags?.slice(0, 2).map((t) => <Tag key={t}>{t}</Tag>),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'draft' && (
            <>
              <Tooltip title="编辑">
                <Button size="small" icon={<EditOutlined />} />
              </Tooltip>
              <Tooltip title="删除">
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
              </Tooltip>
            </>
          )}
          {(record.status === 'draft' || record.status === 'pending_review') && (
            <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => handleApprove(record.id)}>
              批准
            </Button>
          )}
          <Button size="small" icon={<SafetyOutlined />} onClick={() => {
            complianceForm.setFieldValue('standard_id', record.id);
            setComplianceModalOpen(true);
          }}>
            检查
          </Button>
        </Space>
      ),
    },
  ];

  const stats = {
    total: standards.length,
    approved: standards.filter((s) => s.status === 'approved').length,
    draft: standards.filter((s) => s.status === 'draft').length,
    pending: standards.filter((s) => s.status === 'pending_review').length,
  };

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Row gutter={24}>
            <Col span={6}>
              <Statistic title="标准总数" value={stats.total} prefix={<FileTextOutlined />} />
            </Col>
            <Col span={6}>
              <Statistic title="已批准" value={stats.approved} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
            </Col>
            <Col span={6}>
              <Statistic title="草稿" value={stats.draft} prefix={<EditOutlined />} />
            </Col>
            <Col span={6}>
              <Statistic title="待审核" value={stats.pending} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#faad14' }} />
            </Col>
          </Row>
        </Card>

        <Card
          title={<Title level={4}>数据标准管理</Title>}
          extra={
            <Space>
              <Select
                placeholder="类型筛选"
                allowClear
                style={{ width: 150 }}
                options={standardTypes}
                value={filterType}
                onChange={setFilterType}
              />
              <Select
                placeholder="状态筛选"
                allowClear
                style={{ width: 120 }}
                options={statusOptions}
                value={filterStatus}
                onChange={setFilterStatus}
              />
              <Button icon={<BulbOutlined />} onClick={() => {
                setSuggestions([]);
                suggestForm.resetFields();
                setSuggestModalOpen(true);
              }}>
                AI 建议
              </Button>
              <Button icon={<HistoryOutlined />} onClick={() => handleViewHistory()}>
                检查历史
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
                新建标准
              </Button>
            </Space>
          }
        >
          <Table columns={columns} dataSource={standards} rowKey="id" loading={loading} />
        </Card>
      </Space>

      {/* Create Standard Modal */}
      <Modal
        title="新建数据标准"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        footer={null}
        width={700}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="标准名称" rules={[{ required: true, message: '请输入标准名称' }]}>
                <Input placeholder="例如：手机号格式标准" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="code" label="标准代码" rules={[{ required: true, message: '请输入标准代码' }]}>
                <Input placeholder="例如：STD_PHONE_FORMAT" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="standard_type" label="标准类型" rules={[{ required: true }]}>
                <Select options={standardTypes} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="department" label="所属部门">
                <Input placeholder="例如：数据治理部" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="标准的用途和说明" />
          </Form.Item>
          <Form.Item
            name="rules"
            label="规则定义 (JSON)"
            rules={[{ required: true, message: '请输入规则定义' }]}
          >
            <TextArea
              rows={4}
              placeholder='{"pattern": "^1[3-9]\\d{9}$", "message": "手机号格式不正确"}'
            />
          </Form.Item>
          <Form.Item name="applicable_domains" label="适用领域">
            <Select mode="tags" placeholder="输入后按回车添加" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入后按回车添加" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">创建</Button>
              <Button onClick={() => setCreateModalOpen(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="标准详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={800}
      >
        {selectedStandard && (
          <Tabs items={[
            {
              key: 'info',
              label: '基本信息',
              children: (
                <Descriptions column={2} bordered>
                  <Descriptions.Item label="名称" span={2}>{selectedStandard.name}</Descriptions.Item>
                  <Descriptions.Item label="代码">{selectedStandard.code}</Descriptions.Item>
                  <Descriptions.Item label="版本">v{selectedStandard.version}</Descriptions.Item>
                  <Descriptions.Item label="类型">{getTypeLabel(selectedStandard.standard_type)}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Badge status={getStatusInfo(selectedStandard.status).color as 'default' | 'processing' | 'success' | 'error'} text={getStatusInfo(selectedStandard.status).label} />
                  </Descriptions.Item>
                  <Descriptions.Item label="部门">{selectedStandard.department || '-'}</Descriptions.Item>
                  <Descriptions.Item label="创建时间">{new Date(selectedStandard.created_at).toLocaleString()}</Descriptions.Item>
                  <Descriptions.Item label="描述" span={2}>{selectedStandard.description || '-'}</Descriptions.Item>
                  <Descriptions.Item label="适用领域" span={2}>
                    {selectedStandard.applicable_domains?.map((d) => <Tag key={d}>{d}</Tag>) || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="标签" span={2}>
                    {selectedStandard.tags?.map((t) => <Tag key={t}>{t}</Tag>) || '-'}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: 'rules',
              label: '规则定义',
              children: (
                <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto' }}>
                  {JSON.stringify(selectedStandard.rules, null, 2)}
                </pre>
              ),
            },
          ]} />
        )}
      </Modal>

      {/* AI Suggest Modal */}
      <Modal
        title="AI 标准建议"
        open={suggestModalOpen}
        onCancel={() => setSuggestModalOpen(false)}
        footer={null}
        width={900}
      >
        <Form form={suggestForm} layout="inline" onFinish={handleSuggest} style={{ marginBottom: 16 }}>
          <Form.Item name="source_id" label="数据源" rules={[{ required: true }]}>
            <Select
              style={{ width: 200 }}
              options={dataSources.map((s) => ({ value: s.id, label: s.name }))}
              onChange={(v) => fetchTables(v)}
            />
          </Form.Item>
          <Form.Item name="table_name" label="表名" rules={[{ required: true }]}>
            <Select
              style={{ width: 200 }}
              options={tables.map((t) => ({ value: t.name, label: t.name }))}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={suggestLoading} icon={<BulbOutlined />}>
              生成建议
            </Button>
          </Form.Item>
        </Form>

        {suggestLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>AI 正在分析数据...</div>
          </div>
        ) : suggestions.length > 0 ? (
          <Collapse>
            {suggestions.map((s, i) => (
              <Panel
                key={i}
                header={
                  <Space>
                    <span>{s.name}</span>
                    <Tag color="blue">{getTypeLabel(s.standard_type)}</Tag>
                    <Tag color={s.confidence > 0.8 ? 'green' : s.confidence > 0.5 ? 'orange' : 'red'}>
                      置信度: {(s.confidence * 100).toFixed(0)}%
                    </Tag>
                  </Space>
                }
                extra={
                  <Button type="link" onClick={(e) => { e.stopPropagation(); handleCreateFromSuggestion(s); }}>
                    采纳建议
                  </Button>
                }
              >
                <Paragraph>{s.description}</Paragraph>
                <Text strong>推荐代码: </Text><Tag>{s.code}</Tag>
                <div style={{ marginTop: 8 }}>
                  <Text strong>规则: </Text>
                  <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4 }}>
                    {JSON.stringify(s.rules, null, 2)}
                  </pre>
                </div>
              </Panel>
            ))}
          </Collapse>
        ) : (
          <Alert message="选择数据源和表后点击生成建议" type="info" />
        )}
      </Modal>

      {/* Compliance Check Modal */}
      <Modal
        title="合规性检查"
        open={complianceModalOpen}
        onCancel={() => {
          setComplianceModalOpen(false);
          setComplianceResult(null);
        }}
        footer={null}
        width={800}
      >
        <Form form={complianceForm} layout="vertical" onFinish={handleCheckCompliance}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="standard_id" label="数据标准" rules={[{ required: true }]}>
                <Select
                  options={standards.filter((s) => s.status === 'approved').map((s) => ({
                    value: s.id,
                    label: `${s.name} (${s.code})`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source_id" label="数据源" rules={[{ required: true }]}>
                <Select
                  options={dataSources.map((s) => ({ value: s.id, label: s.name }))}
                  onChange={(v) => fetchTables(v)}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="table_name" label="表名" rules={[{ required: true }]}>
                <Select options={tables.map((t) => ({ value: t.name, label: t.name }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="column_name" label="列名 (可选)">
                <Input placeholder="留空检查整个表" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={complianceLoading} icon={<SafetyOutlined />}>
              开始检查
            </Button>
          </Form.Item>
        </Form>

        {complianceLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在检查合规性...</div>
          </div>
        ) : complianceResult && (
          <div style={{ marginTop: 24 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="合规率"
                    value={complianceResult.compliance_rate}
                    suffix="%"
                    valueStyle={{ color: complianceResult.is_compliant ? '#52c41a' : '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic title="总记录数" value={complianceResult.total_records} />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="合规记录数"
                    value={complianceResult.compliant_records}
                    suffix={`/ ${complianceResult.total_records}`}
                  />
                </Card>
              </Col>
            </Row>

            <div style={{ marginTop: 16 }}>
              <Progress
                percent={complianceResult.compliance_rate}
                status={complianceResult.is_compliant ? 'success' : 'exception'}
              />
            </div>

            {complianceResult.violations?.length > 0 && (
              <Card title="违规详情" size="small" style={{ marginTop: 16 }}>
                {complianceResult.violations.map((v, i) => (
                  <div key={i} style={{ marginBottom: 12 }}>
                    <Text strong>{v.rule}: </Text>
                    <Tag color="red">{v.count} 条违规</Tag>
                    {v.samples.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        <Text type="secondary">示例: </Text>
                        {v.samples.slice(0, 3).map((s, j) => (
                          <Tag key={j} color="orange">{s}</Tag>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}
      </Modal>

      {/* History Modal */}
      <Modal
        title="合规检查历史"
        open={historyModalOpen}
        onCancel={() => setHistoryModalOpen(false)}
        footer={null}
        width={900}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Table
            dataSource={complianceHistory}
            rowKey="checked_at"
            columns={[
              {
                title: '标准',
                dataIndex: 'standard_name',
                key: 'standard_name',
              },
              {
                title: '合规率',
                dataIndex: 'compliance_rate',
                key: 'compliance_rate',
                render: (rate, record) => (
                  <Progress
                    percent={rate}
                    size="small"
                    status={record.is_compliant ? 'success' : 'exception'}
                    style={{ width: 120 }}
                  />
                ),
              },
              {
                title: '总记录',
                dataIndex: 'total_records',
                key: 'total_records',
              },
              {
                title: '合规记录',
                dataIndex: 'compliant_records',
                key: 'compliant_records',
              },
              {
                title: '检查时间',
                dataIndex: 'checked_at',
                key: 'checked_at',
                render: (t) => new Date(t).toLocaleString(),
              },
            ]}
          />
        )}
      </Modal>
    </AuthGuard>
  );
}
