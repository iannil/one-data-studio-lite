'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Card,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tag,
  Popconfirm,
  Typography,
  Tabs,
  Row,
  Col,
  Statistic,
  Switch,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  CloudSyncOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { etlApi, sourcesApi, metadataApi, biApi } from '@/services/api';
import type { ETLPipeline, ETLExecution, DataSource } from '@/types';

const { Title, Text } = Typography;

const STEP_TYPES = [
  { value: 'filter', label: '过滤' },
  { value: 'deduplicate', label: '去重' },
  { value: 'map_values', label: '值映射' },
  { value: 'calculate', label: '计算字段' },
  { value: 'fill_missing', label: '填充缺失值' },
  { value: 'mask', label: '数据脱敏' },
  { value: 'rename', label: '重命名' },
  { value: 'type_cast', label: '类型转换' },
  { value: 'aggregate', label: '聚合' },
  { value: 'sort', label: '排序' },
  { value: 'drop_columns', label: '删除列' },
  { value: 'select_columns', label: '选择列' },
];

export default function ETLPage() {
  const [pipelines, setPipelines] = useState<ETLPipeline[]>([]);
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [selectedPipeline, setSelectedPipeline] = useState<ETLPipeline | null>(null);
  const [executions, setExecutions] = useState<ETLExecution[]>([]);
  const [form] = Form.useForm();

  const fetchPipelines = async () => {
    setLoading(true);
    try {
      const response = await etlApi.listPipelines();
      setPipelines(response.data);
    } catch (error) {
      message.error('获取 ETL 管道列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchSources = async () => {
    try {
      const response = await sourcesApi.list();
      setSources(response.data);
    } catch (error) {
      console.error('Failed to fetch sources');
    }
  };

  useEffect(() => {
    fetchPipelines();
    fetchSources();
  }, []);

  const handleCreate = () => {
    setSelectedPipeline(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleRun = async (id: string) => {
    try {
      await etlApi.runPipeline(id);
      message.success('管道执行已启动');
      fetchPipelines();
    } catch (error) {
      message.error('管道执行失败');
    }
  };

  const handlePreview = async (id: string) => {
    try {
      const response = await etlApi.previewPipeline(id, 50);
      setPreviewData(response.data);
      setPreviewOpen(true);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '预览失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await etlApi.deletePipeline(id);
      message.success('删除成功');
      fetchPipelines();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleViewExecutions = async (pipeline: ETLPipeline) => {
    setSelectedPipeline(pipeline);
    try {
      const response = await etlApi.listExecutions(pipeline.id);
      setExecutions(response.data);
    } catch (error) {
      message.error('获取执行历史失败');
    }
  };

  const handleSubmit = async (values: any) => {
    const data = {
      name: values.name,
      description: values.description,
      source_type: 'table',
      source_config: {
        source_id: values.source_id,
        table_name: values.table_name,
      },
      target_type: 'table',
      target_config: {
        table_name: values.target_table,
        if_exists: 'replace',
        sync_to_bi: values.sync_to_bi || false,
      },
      steps: values.steps || [],
    };

    try {
      await etlApi.createPipeline(data);
      message.success('创建成功');
      setModalOpen(false);
      fetchPipelines();
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleSyncToBi = async (tableName: string) => {
    try {
      const response = await biApi.syncTable(tableName);
      if (response.data.success) {
        message.success(`已同步到 Superset: ${tableName}`);
        if (response.data.superset_url) {
          Modal.info({
            title: 'Superset 数据集已创建',
            content: (
              <div>
                <p>数据集 ID: {response.data.dataset_id}</p>
                <a href={response.data.superset_url} target="_blank" rel="noopener noreferrer">
                  在 Superset 中查看 <LinkOutlined />
                </a>
              </div>
            ),
          });
        }
      } else {
        message.error(response.data.error || '同步失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '同步到 BI 失败');
    }
  };

  const columns: ColumnsType<ETLPipeline> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const colors: Record<string, string> = {
          draft: 'default',
          active: 'success',
          paused: 'warning',
          archived: 'default',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
    {
      title: '最近执行',
      key: 'last_execution',
      render: (_, record: any) => {
        if (!record.last_execution_status) {
          return <Tag>未执行</Tag>;
        }
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          cancelled: 'warning',
        };
        return (
          <Space direction="vertical" size={0}>
            <Tag color={colors[record.last_execution_status]}>{record.last_execution_status}</Tag>
            {record.last_run_at && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {new Date(record.last_run_at).toLocaleString()}
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: '步骤数',
      dataIndex: 'steps',
      key: 'steps',
      render: (steps) => steps?.length || 0,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => tags?.map((t) => <Tag key={t}>{t}</Tag>),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleRun(record.id)}>
            执行
          </Button>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record.id)}>
            预览
          </Button>
          <Tooltip title="同步到 Superset BI">
            <Button
              size="small"
              icon={<CloudSyncOutlined />}
              onClick={() => handleSyncToBi(record.target_config?.table_name)}
              disabled={!record.target_config?.table_name}
            />
          </Tooltip>
          <Button size="small" onClick={() => handleViewExecutions(record)}>
            历史
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const executionColumns: ColumnsType<ETLExecution> = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          cancelled: 'warning',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
    {
      title: '输入行数',
      dataIndex: 'rows_input',
      key: 'rows_input',
    },
    {
      title: '输出行数',
      dataIndex: 'rows_output',
      key: 'rows_output',
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      render: (date) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
    },
  ];

  return (
    <AuthGuard>
      <Card
        title={<Title level={4}>ETL 管道</Title>}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建管道
          </Button>
        }
      >
        <Tabs
          items={[
            {
              key: 'pipelines',
              label: '管道列表',
              children: (
                <Table columns={columns} dataSource={pipelines} rowKey="id" loading={loading} />
              ),
            },
            {
              key: 'history',
              label: '执行历史',
              children: selectedPipeline ? (
                <>
                  <Text strong>管道: {selectedPipeline.name}</Text>
                  <Table
                    columns={executionColumns}
                    dataSource={executions}
                    rowKey="id"
                    style={{ marginTop: 16 }}
                  />
                </>
              ) : (
                <Text type="secondary">请选择一个管道查看执行历史</Text>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="创建 ETL 管道"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="管道名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="source_id" label="数据源" rules={[{ required: true }]}>
                <Select
                  options={sources.map((s) => ({ value: s.id, label: s.name }))}
                  placeholder="选择数据源"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="table_name" label="源表名" rules={[{ required: true }]}>
                <Input placeholder="输入源表名" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="target_table" label="目标表名" rules={[{ required: true }]}>
            <Input placeholder="输入目标表名" />
          </Form.Item>
          <Form.Item
            name="sync_to_bi"
            label="同步到 BI"
            valuePropName="checked"
            tooltip="执行完成后自动同步数据到 Superset"
          >
            <Switch checkedChildren="开" unCheckedChildren="关" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="数据预览"
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={null}
        width={900}
      >
        {previewData && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col>
                <Statistic title="行数" value={previewData.row_count} />
              </Col>
              <Col>
                <Statistic title="列数" value={previewData.columns?.length} />
              </Col>
            </Row>
            <Table
              columns={previewData.columns?.map((col: string) => ({
                title: col,
                dataIndex: col,
                key: col,
                ellipsis: true,
              }))}
              dataSource={previewData.data}
              rowKey={(_, index) => String(index)}
              scroll={{ x: true }}
              size="small"
            />
          </>
        )}
      </Modal>
    </AuthGuard>
  );
}
