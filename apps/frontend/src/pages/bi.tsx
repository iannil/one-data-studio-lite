'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Typography,
  Tag,
  message,
  Spin,
  Result,
  Row,
  Col,
  Statistic,
  Modal,
  Input,
  Tooltip,
  Badge,
  Alert,
} from 'antd';
import {
  CloudSyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
  DeleteOutlined,
  PlusOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { biApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;

interface BIDataset {
  dataset_id: number;
  table_name: string;
  schema_name: string;
  superset_url: string;
  changed_on: string;
}

interface BIStatus {
  superset_url: string;
  health: string;
  authenticated: boolean;
  auth_error?: string;
  database_count?: number;
}

export default function BIPage() {
  const [status, setStatus] = useState<BIStatus | null>(null);
  const [datasets, setDatasets] = useState<BIDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [tableName, setTableName] = useState('');
  const [schemaName, setSchemaName] = useState('public');

  const fetchStatus = async () => {
    try {
      const response = await biApi.getStatus();
      setStatus(response.data);
    } catch (error: any) {
      message.error('获取 Superset 状态失败');
    }
  };

  const fetchDatasets = async () => {
    try {
      const response = await biApi.listDatasets();
      setDatasets(response.data);
    } catch (error: any) {
      console.error('Failed to fetch datasets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchDatasets();
  }, []);

  const handleSync = async () => {
    if (!tableName.trim()) {
      message.warning('请输入表名');
      return;
    }

    setSyncing(true);
    try {
      const response = await biApi.syncTable(tableName, schemaName);
      if (response.data.success) {
        message.success(`同步成功: ${tableName}`);
        setSyncModalOpen(false);
        setTableName('');
        fetchDatasets();
      } else {
        message.error(response.data.error || '同步失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleRefresh = async (tableName: string, schema: string) => {
    try {
      const response = await biApi.syncTable(tableName, schema);
      if (response.data.success) {
        message.success('刷新成功');
        fetchDatasets();
      } else {
        message.error(response.data.error || '刷新失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '刷新失败');
    }
  };

  const handleDelete = async (tableName: string, schema: string) => {
    try {
      const response = await biApi.unsyncTable(tableName, schema);
      if (response.data.success) {
        message.success('删除成功');
        fetchDatasets();
      } else {
        message.error('删除失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const columns: ColumnsType<BIDataset> = [
    {
      title: '数据集 ID',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 100,
    },
    {
      title: '表名',
      dataIndex: 'table_name',
      key: 'table_name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'Schema',
      dataIndex: 'schema_name',
      key: 'schema_name',
      width: 120,
      render: (text) => <Tag>{text || 'public'}</Tag>,
    },
    {
      title: '最后更新',
      dataIndex: 'changed_on',
      key: 'changed_on',
      width: 180,
      render: (date) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title="在 Superset 中查看">
            <Button
              size="small"
              icon={<LinkOutlined />}
              onClick={() => window.open(record.superset_url, '_blank')}
            >
              查看
            </Button>
          </Tooltip>
          <Tooltip title="刷新数据集">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRefresh(record.table_name, record.schema_name)}
            />
          </Tooltip>
          <Tooltip title="删除数据集">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.table_name, record.schema_name)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const isConnected = status?.health === 'healthy' && status?.authenticated;

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title={<Title level={4}><BarChartOutlined /> BI 集成 (Superset)</Title>}>
          <Row gutter={24}>
            <Col span={6}>
              <Statistic
                title="连接状态"
                value={isConnected ? '已连接' : '未连接'}
                valueStyle={{ color: isConnected ? '#52c41a' : '#ff4d4f' }}
                prefix={isConnected ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Superset URL"
                value={status?.superset_url || '-'}
                valueStyle={{ fontSize: 14 }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="数据库连接数"
                value={status?.database_count ?? '-'}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="已同步数据集"
                value={datasets.length}
              />
            </Col>
          </Row>

          {status?.auth_error && (
            <Alert
              message="认证错误"
              description={status.auth_error}
              type="error"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}

          {!isConnected && !loading && (
            <Alert
              message="Superset 未连接"
              description="请检查 Superset 服务是否运行，以及配置的用户名密码是否正确。"
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Card>

        <Card
          title="已同步的数据集"
          extra={
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => { fetchStatus(); fetchDatasets(); }}>
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setSyncModalOpen(true)}
                disabled={!isConnected}
              >
                同步新表
              </Button>
            </Space>
          }
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" />
              <Paragraph style={{ marginTop: 16 }}>正在加载数据集...</Paragraph>
            </div>
          ) : datasets.length === 0 ? (
            <Result
              icon={<CloudSyncOutlined style={{ color: '#1890ff' }} />}
              title="暂无同步的数据集"
              subTitle="点击上方「同步新表」按钮将数据表同步到 Superset"
              extra={
                <Button
                  type="primary"
                  onClick={() => setSyncModalOpen(true)}
                  disabled={!isConnected}
                >
                  同步第一个表
                </Button>
              }
            />
          ) : (
            <Table
              columns={columns}
              dataSource={datasets}
              rowKey="dataset_id"
              pagination={false}
            />
          )}
        </Card>

        <Card title="使用说明" size="small">
          <Space direction="vertical">
            <Text>
              <Badge status="processing" /> 此功能将本平台的数据表同步到 Superset，便于创建可视化报表和仪表板。
            </Text>
            <Text>
              <Badge status="processing" /> 同步后的数据集会出现在 Superset 的「Datasets」菜单中。
            </Text>
            <Text>
              <Badge status="processing" /> ETL 管道执行时，如果开启了「同步到 BI」选项，目标表会自动同步。
            </Text>
            <Text type="secondary">
              提示：确保 Superset 已启动并可访问 ({status?.superset_url || 'http://localhost:8088'})
            </Text>
          </Space>
        </Card>
      </Space>

      <Modal
        title="同步表到 Superset"
        open={syncModalOpen}
        onCancel={() => setSyncModalOpen(false)}
        onOk={handleSync}
        confirmLoading={syncing}
        okText="同步"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>表名 *</Text>
            <Input
              placeholder="输入要同步的表名"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>
          <div>
            <Text strong>Schema</Text>
            <Input
              placeholder="默认 public"
              value={schemaName}
              onChange={(e) => setSchemaName(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>
          <Alert
            message="同步后，您可以在 Superset 中基于此数据集创建图表和仪表板。"
            type="info"
            showIcon
          />
        </Space>
      </Modal>
    </AuthGuard>
  );
}
