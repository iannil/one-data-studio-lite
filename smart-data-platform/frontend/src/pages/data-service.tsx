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
  Spin,
  Empty,
  Alert,
  InputNumber,
  List,
  Progress,
  Switch,
  Checkbox,
  Divider,
  Collapse,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  LineChartOutlined,
  FireOutlined,
  FileExcelOutlined,
  CloudDownloadOutlined,
  TableOutlined,
  FilterOutlined,
  SortAscendingOutlined,
  ReloadOutlined,
  ApiOutlined,
  SettingOutlined,
  CopyOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { dataServiceApi, assetsApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface DataAsset {
  id: string;
  name: string;
  domain?: string;
  category?: string;
  description?: string;
  asset_type: string;
}

interface QueryResult {
  asset_id: string;
  asset_name: string;
  data: Record<string, unknown>[];
  row_count: number;
  columns: string[];
  total_rows: number | null;
  limit: number;
  offset: number;
}

interface AccessStatistics {
  period_days: number;
  total_accesses: number;
  unique_users: number;
  unique_assets: number;
  access_by_type: Record<string, number>;
  daily_trend: Array<{ date: string; count: number }>;
  avg_daily_accesses: number;
}

interface TopAsset {
  asset_id: string;
  name: string;
  domain: string | null;
  category: string | null;
  access_count: number;
}

interface QueryFilter {
  column: string;
  operator: string;
  value: unknown;
}

interface ApiConfig {
  id?: string;
  asset_id: string;
  is_enabled: boolean;
  endpoint_slug?: string;
  rate_limit_requests: number;
  rate_limit_window_seconds: number;
  allow_query: boolean;
  allow_export: boolean;
  allowed_export_formats: string[];
  exposed_columns?: string[];
  hidden_columns: string[];
  default_limit: number;
  max_limit: number;
  require_auth: boolean;
  allowed_roles?: string[];
  enable_desensitization: boolean;
  desensitization_rules?: Record<string, unknown>;
  api_endpoint?: string;
  api_documentation?: Record<string, unknown>;
}

interface ApiDocs {
  asset_id: string;
  asset_name: string;
  api_endpoint: string;
  description?: string;
  is_enabled: boolean;
  require_auth: boolean;
  rate_limit: { requests: number; window_seconds: number };
  available_operations: string[];
  allowed_formats: string[];
  limits: { default_limit: number; max_limit: number };
  request_examples: Record<string, string>;
  response_example: Record<string, unknown>;
}

const filterOperators = [
  { value: 'eq', label: '等于 (=)' },
  { value: 'ne', label: '不等于 (!=)' },
  { value: 'gt', label: '大于 (>)' },
  { value: 'gte', label: '大于等于 (>=)' },
  { value: 'lt', label: '小于 (<)' },
  { value: 'lte', label: '小于等于 (<=)' },
  { value: 'in', label: '包含于 (IN)' },
  { value: 'contains', label: '包含 (LIKE)' },
];

const exportFormats = [
  { value: 'csv', label: 'CSV', icon: <TableOutlined /> },
  { value: 'json', label: 'JSON', icon: <FileExcelOutlined /> },
  { value: 'excel', label: 'Excel', icon: <FileExcelOutlined /> },
  { value: 'parquet', label: 'Parquet', icon: <CloudDownloadOutlined /> },
];

export default function DataServicePage() {
  const [assets, setAssets] = useState<DataAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [queryModalOpen, setQueryModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<DataAsset | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [statistics, setStatistics] = useState<AccessStatistics | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [topAssets, setTopAssets] = useState<TopAsset[]>([]);
  const [topAssetsLoading, setTopAssetsLoading] = useState(false);
  const [filters, setFilters] = useState<QueryFilter[]>([]);
  const [activeTab, setActiveTab] = useState('query');

  // API Config state
  const [apiConfigModalOpen, setApiConfigModalOpen] = useState(false);
  const [apiConfig, setApiConfig] = useState<ApiConfig | null>(null);
  const [apiDocs, setApiDocs] = useState<ApiDocs | null>(null);
  const [apiConfigLoading, setApiConfigLoading] = useState(false);
  const [apiConfigSaving, setApiConfigSaving] = useState(false);

  const [queryForm] = Form.useForm();
  const [exportForm] = Form.useForm();
  const [apiConfigForm] = Form.useForm();

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const response = await assetsApi.list();
      setAssets(response.data);
    } catch (error) {
      message.error('获取数据资产列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    setStatsLoading(true);
    try {
      const response = await dataServiceApi.getStatistics({ days: 30 });
      setStatistics(response.data);
    } catch (error) {
      message.error('获取访问统计失败');
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchTopAssets = async () => {
    setTopAssetsLoading(true);
    try {
      const response = await dataServiceApi.getTopAssets({ limit: 10, days: 30 });
      setTopAssets(response.data);
    } catch (error) {
      message.error('获取热门资产失败');
    } finally {
      setTopAssetsLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
    fetchStatistics();
    fetchTopAssets();
  }, []);

  const handleQuery = async () => {
    if (!selectedAsset) return;

    setQueryLoading(true);
    try {
      const values = queryForm.getFieldsValue();
      const response = await dataServiceApi.query({
        asset_id: selectedAsset.id,
        query_params: {
          filters: filters.length > 0 ? filters : undefined,
          sort_by: values.sort_by,
          sort_order: values.sort_order,
          columns: values.columns?.length > 0 ? values.columns : undefined,
        },
        limit: values.limit || 100,
        offset: values.offset || 0,
      });
      setQueryResult(response.data);
      message.success(`查询成功，返回 ${response.data.row_count} 条记录`);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '查询失败');
    } finally {
      setQueryLoading(false);
    }
  };

  const handleExport = async () => {
    if (!selectedAsset) return;

    setExportLoading(true);
    try {
      const values = exportForm.getFieldsValue();
      const response = await dataServiceApi.export({
        asset_id: selectedAsset.id,
        format: values.format || 'csv',
        query_params: filters.length > 0 ? { filters } : undefined,
        limit: values.limit,
      });

      const blob = new Blob([response.data], { type: response.headers['content-type'] });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') || `export.${values.format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      message.success('导出成功');
      setExportModalOpen(false);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '导出失败');
    } finally {
      setExportLoading(false);
    }
  };

  const addFilter = () => {
    setFilters([...filters, { column: '', operator: 'eq', value: '' }]);
  };

  const updateFilter = (index: number, field: keyof QueryFilter, value: unknown) => {
    const newFilters = filters.map((f, i) =>
      i === index ? { ...f, [field]: value } : f
    );
    setFilters(newFilters);
  };

  const removeFilter = (index: number) => {
    setFilters(filters.filter((_, i) => i !== index));
  };

  const openQueryModal = (asset: DataAsset) => {
    setSelectedAsset(asset);
    setQueryResult(null);
    setFilters([]);
    queryForm.resetFields();
    setQueryModalOpen(true);
  };

  const openExportModal = (asset: DataAsset) => {
    setSelectedAsset(asset);
    setFilters([]);
    exportForm.resetFields();
    setExportModalOpen(true);
  };

  const openApiConfigModal = async (asset: DataAsset) => {
    setSelectedAsset(asset);
    setApiConfigLoading(true);
    setApiConfigModalOpen(true);

    try {
      const [configResponse, docsResponse] = await Promise.all([
        assetsApi.getApiConfig(asset.id).catch(() => null),
        assetsApi.getApiDocs(asset.id).catch(() => null),
      ]);

      if (configResponse?.data) {
        setApiConfig(configResponse.data);
        apiConfigForm.setFieldsValue(configResponse.data);
      } else {
        const defaultConfig: ApiConfig = {
          asset_id: asset.id,
          is_enabled: true,
          rate_limit_requests: 100,
          rate_limit_window_seconds: 60,
          allow_query: true,
          allow_export: true,
          allowed_export_formats: ['csv', 'json'],
          hidden_columns: [],
          default_limit: 100,
          max_limit: 10000,
          require_auth: true,
          enable_desensitization: true,
        };
        setApiConfig(defaultConfig);
        apiConfigForm.setFieldsValue(defaultConfig);
      }

      if (docsResponse?.data) {
        setApiDocs(docsResponse.data);
      }
    } catch (error) {
      message.error('获取 API 配置失败');
    } finally {
      setApiConfigLoading(false);
    }
  };

  const handleSaveApiConfig = async () => {
    if (!selectedAsset) return;

    setApiConfigSaving(true);
    try {
      const values = apiConfigForm.getFieldsValue();
      await assetsApi.updateApiConfig(selectedAsset.id, values);
      message.success('API 配置保存成功');

      const docsResponse = await assetsApi.getApiDocs(selectedAsset.id);
      if (docsResponse?.data) {
        setApiDocs(docsResponse.data);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '保存 API 配置失败');
    } finally {
      setApiConfigSaving(false);
    }
  };

  const handleDeleteApiConfig = async () => {
    if (!selectedAsset) return;

    try {
      await assetsApi.deleteApiConfig(selectedAsset.id);
      message.success('API 配置已删除');
      setApiConfigModalOpen(false);
      setApiConfig(null);
      setApiDocs(null);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '删除 API 配置失败');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  const assetColumns: ColumnsType<DataAsset> = [
    {
      title: '资产名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <TableOutlined />
          <a onClick={() => openQueryModal(record)}>{name}</a>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'asset_type',
      key: 'asset_type',
      render: (type) => <Tag>{type}</Tag>,
    },
    {
      title: '领域',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'API',
      key: 'api',
      width: 100,
      render: (_, record) => (
        <Button
          size="small"
          type="link"
          icon={<ApiOutlined />}
          onClick={() => openApiConfigModal(record)}
        >
          配置
        </Button>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<SearchOutlined />} onClick={() => openQueryModal(record)}>
            查询
          </Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={() => openExportModal(record)}>
            导出
          </Button>
        </Space>
      ),
    },
  ];

  const queryResultColumns: ColumnsType<Record<string, unknown>> = queryResult?.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
    width: 150,
    render: (value) => {
      if (value === null || value === undefined) return <Text type="secondary">NULL</Text>;
      if (typeof value === 'object') return JSON.stringify(value);
      return String(value);
    },
  })) || [];

  return (
    <AuthGuard>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'query',
            label: (
              <Space>
                <SearchOutlined />
                数据查询
              </Space>
            ),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Card
                  title={<Title level={4}>数据资产查询</Title>}
                  extra={
                    <Button icon={<ReloadOutlined />} onClick={fetchAssets}>
                      刷新
                    </Button>
                  }
                >
                  <Table
                    columns={assetColumns}
                    dataSource={assets}
                    rowKey="id"
                    loading={loading}
                  />
                </Card>
              </Space>
            ),
          },
          {
            key: 'statistics',
            label: (
              <Space>
                <LineChartOutlined />
                访问统计
              </Space>
            ),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                {statsLoading ? (
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin size="large" />
                  </div>
                ) : statistics ? (
                  <>
                    <Card>
                      <Row gutter={24}>
                        <Col span={6}>
                          <Statistic
                            title="总访问次数"
                            value={statistics.total_accesses}
                            prefix={<LineChartOutlined />}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="独立用户数"
                            value={statistics.unique_users}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="访问资产数"
                            value={statistics.unique_assets}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="日均访问量"
                            value={statistics.avg_daily_accesses.toFixed(1)}
                          />
                        </Col>
                      </Row>
                    </Card>

                    <Row gutter={16}>
                      <Col span={12}>
                        <Card title="访问类型分布">
                          {Object.entries(statistics.access_by_type).length > 0 ? (
                            <List
                              dataSource={Object.entries(statistics.access_by_type)}
                              renderItem={([type, count]) => (
                                <List.Item>
                                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                    <Tag color="blue">{type}</Tag>
                                    <Text>{count} 次</Text>
                                  </Space>
                                </List.Item>
                              )}
                            />
                          ) : (
                            <Empty description="暂无数据" />
                          )}
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card title="近期访问趋势">
                          {statistics.daily_trend.length > 0 ? (
                            <List
                              dataSource={statistics.daily_trend.slice(-7)}
                              renderItem={(item) => (
                                <List.Item>
                                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                    <Text>{item.date}</Text>
                                    <Progress
                                      percent={Math.round((item.count / Math.max(...statistics.daily_trend.map((d) => d.count), 1)) * 100)}
                                      size="small"
                                      format={() => `${item.count}`}
                                      style={{ width: 150 }}
                                    />
                                  </Space>
                                </List.Item>
                              )}
                            />
                          ) : (
                            <Empty description="暂无数据" />
                          )}
                        </Card>
                      </Col>
                    </Row>
                  </>
                ) : (
                  <Empty description="加载统计数据失败" />
                )}
              </Space>
            ),
          },
          {
            key: 'top',
            label: (
              <Space>
                <FireOutlined />
                热门资产
              </Space>
            ),
            children: (
              <Card
                title={<Title level={4}>热门数据资产 (近30天)</Title>}
                extra={
                  <Button icon={<ReloadOutlined />} onClick={fetchTopAssets}>
                    刷新
                  </Button>
                }
              >
                {topAssetsLoading ? (
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin size="large" />
                  </div>
                ) : topAssets.length > 0 ? (
                  <List
                    dataSource={topAssets}
                    renderItem={(item, index) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={
                            <div style={{
                              width: 32,
                              height: 32,
                              borderRadius: '50%',
                              background: index < 3 ? '#faad14' : '#d9d9d9',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 'bold',
                              color: index < 3 ? '#fff' : '#666',
                            }}>
                              {index + 1}
                            </div>
                          }
                          title={
                            <Space>
                              <a onClick={() => {
                                const asset = assets.find((a) => a.id === item.asset_id);
                                if (asset) openQueryModal(asset);
                              }}>
                                {item.name}
                              </a>
                              {item.domain && <Tag>{item.domain}</Tag>}
                              {item.category && <Tag color="blue">{item.category}</Tag>}
                            </Space>
                          }
                          description={`访问次数: ${item.access_count}`}
                        />
                        <Progress
                          percent={Math.round((item.access_count / Math.max(topAssets[0]?.access_count || 1, 1)) * 100)}
                          size="small"
                          style={{ width: 200 }}
                          format={() => `${item.access_count} 次`}
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty description="暂无访问数据" />
                )}
              </Card>
            ),
          },
        ]}
      />

      {/* Query Modal */}
      <Modal
        title={
          <Space>
            <SearchOutlined />
            查询: {selectedAsset?.name}
          </Space>
        }
        open={queryModalOpen}
        onCancel={() => setQueryModalOpen(false)}
        footer={null}
        width={1200}
      >
        <Form form={queryForm} layout="vertical">
          <Card size="small" title="查询参数" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="limit" label="返回行数" initialValue={100}>
                  <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="offset" label="跳过行数" initialValue={0}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="sort_order" label="排序方向" initialValue="asc">
                  <Select
                    options={[
                      { value: 'asc', label: '升序' },
                      { value: 'desc', label: '降序' },
                    ]}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="sort_by" label="排序字段">
                  <Input placeholder="输入列名" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="columns" label="选择列 (留空返回全部)">
                  <Select mode="tags" placeholder="输入列名后按回车" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card
            size="small"
            title={
              <Space>
                <FilterOutlined />
                筛选条件
              </Space>
            }
            extra={
              <Button size="small" onClick={addFilter}>
                添加条件
              </Button>
            }
            style={{ marginBottom: 16 }}
          >
            {filters.length === 0 ? (
              <Alert message="无筛选条件，将返回全部数据" type="info" />
            ) : (
              filters.map((filter, index) => (
                <Row key={index} gutter={8} style={{ marginBottom: 8 }}>
                  <Col span={8}>
                    <Input
                      placeholder="列名"
                      value={filter.column}
                      onChange={(e) => updateFilter(index, 'column', e.target.value)}
                    />
                  </Col>
                  <Col span={6}>
                    <Select
                      style={{ width: '100%' }}
                      value={filter.operator}
                      onChange={(v) => updateFilter(index, 'operator', v)}
                      options={filterOperators}
                    />
                  </Col>
                  <Col span={8}>
                    <Input
                      placeholder="值"
                      value={String(filter.value)}
                      onChange={(e) => updateFilter(index, 'value', e.target.value)}
                    />
                  </Col>
                  <Col span={2}>
                    <Button danger onClick={() => removeFilter(index)}>
                      删除
                    </Button>
                  </Col>
                </Row>
              ))
            )}
          </Card>

          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleQuery} loading={queryLoading}>
              执行查询
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => {
              setQueryModalOpen(false);
              if (selectedAsset) openExportModal(selectedAsset);
            }}>
              导出数据
            </Button>
          </Space>
        </Form>

        {queryLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : queryResult && (
          <div>
            <Alert
              message={`查询结果: ${queryResult.row_count} 条记录${queryResult.total_rows ? ` (共 ${queryResult.total_rows} 条)` : ''}`}
              type="success"
              style={{ marginBottom: 16 }}
            />
            <Table
              dataSource={queryResult.data}
              columns={queryResultColumns}
              rowKey={(_, index) => String(index)}
              scroll={{ x: 'max-content' }}
              size="small"
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
              }}
            />
          </div>
        )}
      </Modal>

      {/* Export Modal */}
      <Modal
        title={
          <Space>
            <DownloadOutlined />
            导出: {selectedAsset?.name}
          </Space>
        }
        open={exportModalOpen}
        onCancel={() => setExportModalOpen(false)}
        footer={null}
        width={600}
      >
        <Form form={exportForm} layout="vertical" onFinish={handleExport}>
          <Form.Item name="format" label="导出格式" initialValue="csv">
            <Select>
              {exportFormats.map((f) => (
                <Select.Option key={f.value} value={f.value}>
                  <Space>
                    {f.icon}
                    {f.label}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="limit" label="导出行数 (留空导出全部)">
            <InputNumber min={1} style={{ width: '100%' }} placeholder="不限制" />
          </Form.Item>

          <Card
            size="small"
            title={
              <Space>
                <FilterOutlined />
                筛选条件
              </Space>
            }
            extra={
              <Button size="small" onClick={addFilter}>
                添加条件
              </Button>
            }
            style={{ marginBottom: 16 }}
          >
            {filters.length === 0 ? (
              <Alert message="无筛选条件，将导出全部数据" type="info" />
            ) : (
              filters.map((filter, index) => (
                <Row key={index} gutter={8} style={{ marginBottom: 8 }}>
                  <Col span={8}>
                    <Input
                      placeholder="列名"
                      value={filter.column}
                      onChange={(e) => updateFilter(index, 'column', e.target.value)}
                    />
                  </Col>
                  <Col span={6}>
                    <Select
                      style={{ width: '100%' }}
                      value={filter.operator}
                      onChange={(v) => updateFilter(index, 'operator', v)}
                      options={filterOperators}
                    />
                  </Col>
                  <Col span={8}>
                    <Input
                      placeholder="值"
                      value={String(filter.value)}
                      onChange={(e) => updateFilter(index, 'value', e.target.value)}
                    />
                  </Col>
                  <Col span={2}>
                    <Button danger onClick={() => removeFilter(index)}>
                      删除
                    </Button>
                  </Col>
                </Row>
              ))
            )}
          </Card>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={exportLoading} icon={<DownloadOutlined />}>
              开始导出
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* API Config Modal */}
      <Modal
        title={
          <Space>
            <ApiOutlined />
            API 配置: {selectedAsset?.name}
          </Space>
        }
        open={apiConfigModalOpen}
        onCancel={() => {
          setApiConfigModalOpen(false);
          setApiConfig(null);
          setApiDocs(null);
        }}
        footer={null}
        width={900}
      >
        {apiConfigLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Form form={apiConfigForm} layout="vertical">
            <Row gutter={24}>
              <Col span={14}>
                <Card size="small" title="基础配置" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="is_enabled" label="启用 API" valuePropName="checked">
                        <Switch />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="endpoint_slug" label="自定义路径 (可选)">
                        <Input placeholder="例如: user-orders" />
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>

                <Card size="small" title="速率限制" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="rate_limit_requests" label="请求次数限制">
                        <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="rate_limit_window_seconds" label="时间窗口 (秒)">
                        <InputNumber min={1} max={3600} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>

                <Card size="small" title="操作权限" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="allow_query" label="允许查询" valuePropName="checked">
                        <Switch />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="allow_export" label="允许导出" valuePropName="checked">
                        <Switch />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="allowed_export_formats" label="导出格式">
                        <Checkbox.Group options={['csv', 'json', 'excel', 'parquet']} />
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>

                <Card size="small" title="行数限制" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="default_limit" label="默认返回行数">
                        <InputNumber min={1} max={10000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="max_limit" label="最大返回行数">
                        <InputNumber min={1} max={100000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>

                <Card size="small" title="字段控制" style={{ marginBottom: 16 }}>
                  <Form.Item name="exposed_columns" label="暴露字段 (留空返回全部)">
                    <Select mode="tags" placeholder="输入字段名后按回车" />
                  </Form.Item>
                  <Form.Item name="hidden_columns" label="隐藏字段">
                    <Select mode="tags" placeholder="输入需要隐藏的字段名" />
                  </Form.Item>
                </Card>

                <Card size="small" title="认证与安全" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="require_auth" label="需要认证" valuePropName="checked">
                        <Switch />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="enable_desensitization" label="数据脱敏" valuePropName="checked">
                        <Switch />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="allowed_roles" label="允许的角色">
                        <Select mode="tags" placeholder="留空允许所有角色" />
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>

                <Space>
                  <Button type="primary" icon={<SettingOutlined />} onClick={handleSaveApiConfig} loading={apiConfigSaving}>
                    保存配置
                  </Button>
                  <Button danger onClick={handleDeleteApiConfig}>
                    删除配置
                  </Button>
                </Space>
              </Col>

              <Col span={10}>
                <Card size="small" title="API 端点信息" style={{ marginBottom: 16 }}>
                  {apiDocs ? (
                    <>
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>端点地址:</Text>
                        <div style={{ display: 'flex', alignItems: 'center', marginTop: 4 }}>
                          <Text code style={{ flex: 1 }}>{apiDocs.api_endpoint}</Text>
                          <Button
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => copyToClipboard(apiDocs.api_endpoint)}
                          />
                        </div>
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>状态:</Text>{' '}
                        <Tag color={apiDocs.is_enabled ? 'green' : 'red'}>
                          {apiDocs.is_enabled ? '已启用' : '已禁用'}
                        </Tag>
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>速率限制:</Text>{' '}
                        <Text>{apiDocs.rate_limit.requests} 次 / {apiDocs.rate_limit.window_seconds} 秒</Text>
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>可用操作:</Text>{' '}
                        {apiDocs.available_operations.map((op) => (
                          <Tag key={op} color="blue">{op}</Tag>
                        ))}
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <Text strong>导出格式:</Text>{' '}
                        {apiDocs.allowed_formats.map((fmt) => (
                          <Tag key={fmt}>{fmt}</Tag>
                        ))}
                      </div>
                    </>
                  ) : (
                    <Text type="secondary">保存配置后显示 API 信息</Text>
                  )}
                </Card>

                <Collapse size="small">
                  <Panel header="cURL 示例" key="curl">
                    {apiDocs?.request_examples?.curl_query ? (
                      <div style={{ position: 'relative' }}>
                        <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 150 }}>
                          {apiDocs.request_examples.curl_query}
                        </pre>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          style={{ position: 'absolute', top: 4, right: 4 }}
                          onClick={() => copyToClipboard(apiDocs.request_examples.curl_query)}
                        />
                      </div>
                    ) : (
                      <Text type="secondary">保存配置后显示示例</Text>
                    )}
                  </Panel>
                  <Panel header="JavaScript 示例" key="js">
                    {apiDocs?.request_examples?.javascript_query ? (
                      <div style={{ position: 'relative' }}>
                        <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 150 }}>
                          {apiDocs.request_examples.javascript_query}
                        </pre>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          style={{ position: 'absolute', top: 4, right: 4 }}
                          onClick={() => copyToClipboard(apiDocs.request_examples.javascript_query)}
                        />
                      </div>
                    ) : (
                      <Text type="secondary">保存配置后显示示例</Text>
                    )}
                  </Panel>
                  <Panel header="Python 示例" key="python">
                    {apiDocs?.request_examples?.python_query ? (
                      <div style={{ position: 'relative' }}>
                        <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 150 }}>
                          {apiDocs.request_examples.python_query}
                        </pre>
                        <Button
                          size="small"
                          icon={<CopyOutlined />}
                          style={{ position: 'absolute', top: 4, right: 4 }}
                          onClick={() => copyToClipboard(apiDocs.request_examples.python_query)}
                        />
                      </div>
                    ) : (
                      <Text type="secondary">保存配置后显示示例</Text>
                    )}
                  </Panel>
                  <Panel header="响应示例" key="response">
                    {apiDocs?.response_example ? (
                      <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 150 }}>
                        {JSON.stringify(apiDocs.response_example, null, 2)}
                      </pre>
                    ) : (
                      <Text type="secondary">保存配置后显示示例</Text>
                    )}
                  </Panel>
                </Collapse>
              </Col>
            </Row>
          </Form>
        )}
      </Modal>
    </AuthGuard>
  );
}
