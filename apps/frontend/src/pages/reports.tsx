'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Tag,
  Popconfirm,
  message,
  Row,
  Col,
  Empty,
  Spin,
  Tabs,
  Collapse,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SendOutlined,
  ReloadOutlined,
  FileTextOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import ChartRenderer from '@/components/ChartRenderer';
import { reportsApi, analysisApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface ReportChart {
  id: string;
  title: string;
  description?: string;
  chart_type: string;
  query_type: string;
  nl_query?: string;
  sql_query?: string;
  asset_id?: string;
  chart_options?: Record<string, unknown>;
  x_field?: string;
  y_field?: string;
  group_by?: string;
  position: number;
  grid_x: number;
  grid_y: number;
  grid_width: number;
  grid_height: number;
  cached_data?: {
    data?: Record<string, unknown>[];
    columns?: string[];
  };
}

interface Report {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  department?: string;
  status: string;
  is_public: boolean;
  tags: string[];
  auto_refresh: boolean;
  refresh_interval_seconds?: number;
  last_refreshed_at?: string;
  charts: ReportChart[];
  created_at: string;
  updated_at: string;
}

const CHART_TYPES = [
  { value: 'bar', label: '柱状图', icon: <BarChartOutlined /> },
  { value: 'line', label: '折线图', icon: <LineChartOutlined /> },
  { value: 'pie', label: '饼图', icon: <PieChartOutlined /> },
  { value: 'scatter', label: '散点图' },
  { value: 'area', label: '面积图' },
  { value: 'table', label: '表格' },
  { value: 'stat', label: '统计数字' },
];

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [chartModalOpen, setChartModalOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [chartData, setChartData] = useState<{ data: Record<string, unknown>[]; columns: string[] } | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [form] = Form.useForm();
  const [chartForm] = Form.useForm();

  const fetchReports = async () => {
    setLoading(true);
    try {
      const response = await reportsApi.list();
      setReports(response.data.items);
    } catch (error) {
      message.error('加载报表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleCreate = () => {
    setSelectedReport(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (report: Report) => {
    setSelectedReport(report);
    form.setFieldsValue({
      name: report.name,
      description: report.description,
      department: report.department,
      is_public: report.is_public,
      tags: report.tags,
      auto_refresh: report.auto_refresh,
      refresh_interval_seconds: report.refresh_interval_seconds,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (selectedReport) {
        await reportsApi.update(selectedReport.id, values);
        message.success('报表更新成功');
      } else {
        await reportsApi.create(values as Parameters<typeof reportsApi.create>[0]);
        message.success('报表创建成功');
      }
      setModalOpen(false);
      fetchReports();
    } catch (error) {
      message.error('保存报表失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await reportsApi.delete(id);
      message.success('报表删除成功');
      fetchReports();
    } catch (error) {
      message.error('删除报表失败');
    }
  };

  const handlePublish = async (report: Report) => {
    try {
      await reportsApi.publish(report.id);
      message.success('报表发布成功');
      fetchReports();
    } catch (error) {
      message.error('发布报表失败');
    }
  };

  const handleRefresh = async (report: Report) => {
    try {
      const response = await reportsApi.refresh(report.id);
      message.success(`已刷新 ${response.data.refreshed_charts} 个图表`);
      fetchReports();
    } catch (error) {
      message.error('刷新报表失败');
    }
  };

  const handlePreview = (report: Report) => {
    setSelectedReport(report);
    setPreviewOpen(true);
  };

  const handleAddChart = (report: Report) => {
    setSelectedReport(report);
    chartForm.resetFields();
    setChartModalOpen(true);
  };

  const handleTestQuery = async () => {
    const nlQuery = chartForm.getFieldValue('nl_query');
    if (!nlQuery) {
      message.warning('请先输入查询语句');
      return;
    }

    setChartLoading(true);
    try {
      const response = await analysisApi.nlQuery(nlQuery);
      setChartData({
        data: response.data.data || [],
        columns: response.data.columns || [],
      });
      message.success('查询执行成功');
    } catch (error) {
      message.error('查询执行失败');
    } finally {
      setChartLoading(false);
    }
  };

  const handleChartSubmit = async (values: Record<string, unknown>) => {
    if (!selectedReport) return;

    try {
      await reportsApi.addChart(selectedReport.id, values as Parameters<typeof reportsApi.addChart>[1]);
      message.success('图表添加成功');
      setChartModalOpen(false);
      setChartData(null);
      fetchReports();
    } catch (error) {
      message.error('添加图表失败');
    }
  };

  const columns: ColumnsType<Report> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <FileTextOutlined />
          <Text strong>{name}</Text>
          {record.is_public && <Tag color="blue">公开</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const colors: Record<string, string> = {
          draft: 'default',
          published: 'success',
          archived: 'warning',
        };
        const labels: Record<string, string> = {
          draft: '草稿',
          published: '已发布',
          archived: '已归档',
        };
        return <Tag color={colors[status]}>{labels[status] || status}</Tag>;
      },
    },
    {
      title: '图表数',
      dataIndex: 'charts',
      key: 'charts',
      render: (charts) => charts?.length || 0,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => tags?.map((t) => <Tag key={t}>{t}</Tag>),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)}>
            预览
          </Button>
          <Button size="small" icon={<PlusOutlined />} onClick={() => handleAddChart(record)}>
            图表
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          {record.status === 'draft' && (
            <Button
              size="small"
              icon={<SendOutlined />}
              onClick={() => handlePublish(record)}
              type="primary"
            />
          )}
          <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRefresh(record)} />
          <Popconfirm title="确定删除此报表?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <AuthGuard>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <Title level={4} style={{ margin: 0 }}>报表设计器</Title>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建报表
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Report Modal */}
      <Modal
        title={selectedReport ? '编辑报表' : '创建报表'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="报表名称" rules={[{ required: true }]}>
            <Input placeholder="输入报表名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="描述此报表" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="department" label="部门">
                <Input placeholder="部门" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tags" label="标签">
                <Select mode="tags" placeholder="添加标签" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="is_public" label="公开" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="auto_refresh" label="自动刷新" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="refresh_interval_seconds" label="刷新间隔(秒)">
                <Input type="number" placeholder="300" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Add Chart Modal */}
      <Modal
        title="添加图表"
        open={chartModalOpen}
        onCancel={() => {
          setChartModalOpen(false);
          setChartData(null);
        }}
        onOk={() => chartForm.submit()}
        width={800}
      >
        <Form form={chartForm} layout="vertical" onFinish={handleChartSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="title" label="图表标题" rules={[{ required: true }]}>
                <Input placeholder="图表标题" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="chart_type" label="图表类型" rules={[{ required: true }]}>
                <Select options={CHART_TYPES} placeholder="选择图表类型" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="图表描述" />
          </Form.Item>
          <Form.Item name="nl_query" label="自然语言查询" rules={[{ required: true }]}>
            <TextArea
              rows={3}
              placeholder="例如：显示上月各产品类别的总销售额"
            />
          </Form.Item>
          <Button onClick={handleTestQuery} loading={chartLoading} style={{ marginBottom: 16 }}>
            测试查询
          </Button>

          {chartData && chartData.data.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <ChartRenderer
                data={chartData.data}
                columns={chartData.columns}
                height={300}
                title="预览"
              />
            </div>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="x_field" label="X轴字段">
                <Input placeholder="x_field" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="y_field" label="Y轴字段">
                <Input placeholder="y_field" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="group_by" label="分组字段">
                <Input placeholder="group_by" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title={`预览: ${selectedReport?.name}`}
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={null}
        width={1000}
      >
        {selectedReport && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {selectedReport.description && (
              <Paragraph type="secondary">{selectedReport.description}</Paragraph>
            )}

            {selectedReport.charts.length === 0 ? (
              <Empty description="此报表暂无图表">
                <Button type="primary" onClick={() => {
                  setPreviewOpen(false);
                  handleAddChart(selectedReport);
                }}>
                  添加第一个图表
                </Button>
              </Empty>
            ) : (
              <Row gutter={[16, 16]}>
                {selectedReport.charts.map((chart) => (
                  <Col span={chart.grid_width * 2} key={chart.id}>
                    <Card title={chart.title} size="small">
                      {chart.cached_data && chart.cached_data.data ? (
                        <ChartRenderer
                          data={chart.cached_data.data}
                          columns={chart.cached_data.columns || []}
                          suggestion={{
                            chart_type: chart.chart_type as 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'table',
                            x_axis: chart.x_field,
                            y_axis: chart.y_field,
                          }}
                          height={250}
                          showTypeSelector={false}
                        />
                      ) : (
                        <Empty description="无数据 - 点击刷新加载" />
                      )}
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Space>
        )}
      </Modal>
    </AuthGuard>
  );
}
