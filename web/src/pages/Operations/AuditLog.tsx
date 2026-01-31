import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Select,
  Button,
  Tag,
  message,
  Typography,
  Space,
  Statistic,
  Row,
  Col,
  Spin,
  Drawer,
  Descriptions,
} from 'antd';
import {
  AuditOutlined,
  DownloadOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { getLogs, getStats, exportLogs, AuditQueryParams } from '../../api/audit';
import { AuditEvent, AuditStats } from '../../types';

const { Title, Text } = Typography;
const { Option } = Select;

const AuditLog: React.FC = () => {
  const [logs, setLogs] = useState<AuditEvent[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [filters, setFilters] = useState<AuditQueryParams>({
    page: 1,
    page_size: 20,
  });
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditEvent | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await getLogs(filters);
      setLogs(data);
    } catch (error) {
      message.error('获取审计日志失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (error) {
      message.error('获取统计信息失败');
    } finally {
      setLoadingStats(false);
    }
  };

  const handleExport = async (format: 'csv' | 'json') => {
    setExporting(true);
    try {
      const blob = await exportLogs(format, filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    } finally {
      setExporting(false);
    }
  };

  const handleViewDetail = (record: AuditEvent) => {
    setSelectedLog(record);
    setDrawerVisible(true);
  };

  const statusCodeColor = (code?: number) => {
    if (!code) return 'default';
    if (code >= 200 && code < 300) return 'success';
    if (code >= 400 && code < 500) return 'warning';
    if (code >= 500) return 'error';
    return 'default';
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: '子系统',
      dataIndex: 'subsystem',
      key: 'subsystem',
      width: 120,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '事件类型',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 100,
    },
    {
      title: '用户',
      dataIndex: 'user',
      key: 'user',
      width: 100,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      ellipsis: true,
    },
    {
      title: '状态码',
      dataIndex: 'status_code',
      key: 'status_code',
      width: 80,
      render: (code: number) => (
        <Tag color={statusCodeColor(code)}>{code || '-'}</Tag>
      ),
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 80,
      render: (v: number) => (v ? `${v.toFixed(0)}ms` : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: any, record: AuditEvent) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          详情
        </Button>
      ),
    },
  ];

  // 从统计中提取子系统和事件类型选项
  const subsystemOptions = stats
    ? Object.keys(stats.events_by_subsystem)
    : [];
  const eventTypeOptions = stats
    ? Object.keys(stats.events_by_type)
    : [];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <AuditOutlined /> 统一日志审计
      </Title>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            {loadingStats ? (
              <Spin />
            ) : (
              <Statistic title="总事件数" value={stats?.total_events || 0} />
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            {loadingStats ? (
              <Spin />
            ) : (
              <Statistic
                title="子系统数"
                value={Object.keys(stats?.events_by_subsystem || {}).length}
              />
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            {loadingStats ? (
              <Spin />
            ) : (
              <Statistic
                title="用户数"
                value={Object.keys(stats?.events_by_user || {}).length}
              />
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            {loadingStats ? (
              <Spin />
            ) : (
              <Statistic
                title="事件类型数"
                value={Object.keys(stats?.events_by_type || {}).length}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 筛选器和日志表格 */}
      <Card size="small">
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="子系统"
            allowClear
            style={{ width: 150 }}
            value={filters.subsystem}
            onChange={(v) => setFilters({ ...filters, subsystem: v, page: 1 })}
          >
            {subsystemOptions.map((s) => (
              <Option key={s} value={s}>
                {s}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="事件类型"
            allowClear
            style={{ width: 150 }}
            value={filters.event_type}
            onChange={(v) => setFilters({ ...filters, event_type: v, page: 1 })}
          >
            {eventTypeOptions.map((t) => (
              <Option key={t} value={t}>
                {t}
              </Option>
            ))}
          </Select>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchLogs();
              fetchStats();
            }}
          >
            刷新
          </Button>
          <Button
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={() => handleExport('csv')}
          >
            导出 CSV
          </Button>
          <Button
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={() => handleExport('json')}
          >
            导出 JSON
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={logs.map((l) => ({ ...l, key: l.id }))}
          loading={loading}
          pagination={{
            current: filters.page,
            pageSize: filters.page_size,
            onChange: (page, pageSize) =>
              setFilters({ ...filters, page, page_size: pageSize }),
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          size="small"
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="日志详情"
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        size={500}
      >
        {selectedLog && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{selectedLog.id}</Descriptions.Item>
            <Descriptions.Item label="时间">
              {new Date(selectedLog.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="子系统">
              {selectedLog.subsystem}
            </Descriptions.Item>
            <Descriptions.Item label="事件类型">
              {selectedLog.event_type}
            </Descriptions.Item>
            <Descriptions.Item label="用户">{selectedLog.user}</Descriptions.Item>
            <Descriptions.Item label="操作">{selectedLog.action}</Descriptions.Item>
            <Descriptions.Item label="资源">
              {selectedLog.resource || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="状态码">
              <Tag color={statusCodeColor(selectedLog.status_code)}>
                {selectedLog.status_code || '-'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="耗时">
              {selectedLog.duration_ms
                ? `${selectedLog.duration_ms.toFixed(2)} ms`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="IP 地址">
              {selectedLog.ip_address || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="User Agent">
              {selectedLog.user_agent || '-'}
            </Descriptions.Item>
            {selectedLog.details && (
              <Descriptions.Item label="详情">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default AuditLog;
