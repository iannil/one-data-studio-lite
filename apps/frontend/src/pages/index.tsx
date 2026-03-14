'use client';

import { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Space,
  Typography,
  List,
  Tag,
  Timeline,
  Spin,
  Button,
  message,
} from 'antd';
import {
  DatabaseOutlined,
  FundOutlined,
  ApiOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
  FileSearchOutlined,
  ArrowRightOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import AuthGuard from '@/components/AuthGuard';
import ChartRenderer from '@/components/ChartRenderer';
import { sourcesApi, assetsApi, etlApi, alertsApi, collectApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;

interface DashboardStats {
  sources: number;
  assets: number;
  pipelines: number;
  alerts: number;
  collectTasks: number;
  recentExecutions: Array<{
    id: string;
    name: string;
    status: string;
    started_at: string;
    type: string;
  }>;
}

interface QuickAction {
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  color: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    title: '数据源管理',
    description: '管理数据库连接',
    icon: <DatabaseOutlined />,
    path: '/sources',
    color: '#1890ff',
  },
  {
    title: '数据资产',
    description: '浏览数据目录',
    icon: <FileSearchOutlined />,
    path: '/assets',
    color: '#52c41a',
  },
  {
    title: 'ETL 管道',
    description: '配置数据转换',
    icon: <SyncOutlined />,
    path: '/etl',
    color: '#722ed1',
  },
  {
    title: '数据分析',
    description: '自然语言查询',
    icon: <FundOutlined />,
    path: '/analysis',
    color: '#fa8c16',
  },
  {
    title: '数据服务',
    description: '数据 API 访问',
    icon: <ApiOutlined />,
    path: '/data-service',
    color: '#13c2c2',
  },
  {
    title: '安全管理',
    description: '访问控制与审计',
    icon: <SafetyCertificateOutlined />,
    path: '/security',
    color: '#eb2f96',
  },
];

const STATUS_MAP: Record<string, string> = {
  success: '成功',
  failed: '失败',
  running: '运行中',
  pending: '等待中',
};

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({
    sources: 0,
    assets: 0,
    pipelines: 0,
    alerts: 0,
    collectTasks: 0,
    recentExecutions: [],
  });

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [sourcesRes, assetsRes, pipelinesRes, alertsRes, tasksRes] = await Promise.all([
        sourcesApi.list(0, 100).catch(() => ({ data: [] })),
        assetsApi.list({ limit: 100 }).catch(() => ({ data: [] })),
        etlApi.listPipelines(undefined, 0, 100).catch(() => ({ data: [] })),
        alertsApi.listAlerts('active', 0, 100).catch(() => ({ data: [] })),
        collectApi.listTasks(undefined, undefined, 0, 100).catch(() => ({ data: [] })),
      ]);

      const pipelineExecutions = await Promise.all(
        pipelinesRes.data.slice(0, 3).map(async (p: { id: string; name: string }) => {
          try {
            const execRes = await etlApi.listExecutions(p.id, 0, 1);
            if (execRes.data.length > 0) {
              return {
                id: execRes.data[0].id,
                name: p.name,
                status: execRes.data[0].status,
                started_at: execRes.data[0].started_at,
                type: 'etl',
              };
            }
          } catch {
            return null;
          }
          return null;
        })
      );

      const taskExecutions = await Promise.all(
        tasksRes.data.slice(0, 3).map(async (t: { id: string; name: string }) => {
          try {
            const execRes = await collectApi.listExecutions(t.id, 0, 1);
            if (execRes.data.length > 0) {
              return {
                id: execRes.data[0].id,
                name: t.name,
                status: execRes.data[0].status,
                started_at: execRes.data[0].started_at,
                type: 'collect',
              };
            }
          } catch {
            return null;
          }
          return null;
        })
      );

      const allExecutions = [...pipelineExecutions, ...taskExecutions]
        .filter(Boolean)
        .sort((a, b) =>
          new Date(b!.started_at).getTime() - new Date(a!.started_at).getTime()
        )
        .slice(0, 5);

      setStats({
        sources: sourcesRes.data.length,
        assets: assetsRes.data.length,
        pipelines: pipelinesRes.data.length,
        alerts: alertsRes.data.length,
        collectTasks: tasksRes.data.length,
        recentExecutions: allExecutions as DashboardStats['recentExecutions'],
      });
    } catch (error) {
      message.error('加载仪表盘数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'processing';
      default:
        return 'default';
    }
  };

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 页面标题 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} style={{ margin: 0 }}>
              智能数据平台
            </Title>
            <Text type="secondary">
              欢迎回来！以下是您的数据概览。
            </Text>
          </div>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchDashboardData}
            loading={loading}
          >
            刷新
          </Button>
        </div>

        {/* 统计卡片 */}
        <Spin spinning={loading}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Card hoverable onClick={() => router.push('/sources')}>
                <Statistic
                  title="数据源"
                  value={stats.sources}
                  prefix={<DatabaseOutlined style={{ color: '#1890ff' }} />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Card hoverable onClick={() => router.push('/assets')}>
                <Statistic
                  title="数据资产"
                  value={stats.assets}
                  prefix={<FileSearchOutlined style={{ color: '#52c41a' }} />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Card hoverable onClick={() => router.push('/etl')}>
                <Statistic
                  title="ETL 管道"
                  value={stats.pipelines}
                  prefix={<SyncOutlined style={{ color: '#722ed1' }} />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Card hoverable onClick={() => router.push('/collect')}>
                <Statistic
                  title="采集任务"
                  value={stats.collectTasks}
                  prefix={<ApiOutlined style={{ color: '#13c2c2' }} />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={4}>
              <Card hoverable onClick={() => router.push('/security')}>
                <Statistic
                  title="活跃告警"
                  value={stats.alerts}
                  prefix={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
                  valueStyle={stats.alerts > 0 ? { color: '#ff4d4f' } : undefined}
                />
              </Card>
            </Col>
          </Row>
        </Spin>

        <Row gutter={[16, 16]}>
          {/* 快捷操作 */}
          <Col xs={24} lg={16}>
            <Card title="快捷操作">
              <Row gutter={[16, 16]}>
                {QUICK_ACTIONS.map((action) => (
                  <Col xs={12} md={8} key={action.path}>
                    <Card
                      hoverable
                      size="small"
                      onClick={() => router.push(action.path)}
                      style={{ textAlign: 'center', height: '100%' }}
                    >
                      <div
                        style={{
                          fontSize: 28,
                          color: action.color,
                          marginBottom: 8,
                        }}
                      >
                        {action.icon}
                      </div>
                      <Text strong>{action.title}</Text>
                      <Paragraph
                        type="secondary"
                        style={{ fontSize: 12, margin: 0, marginTop: 4 }}
                      >
                        {action.description}
                      </Paragraph>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>

          {/* 最近活动 */}
          <Col xs={24} lg={8}>
            <Card
              title="最近活动"
              extra={
                <Button type="link" size="small" onClick={() => router.push('/etl')}>
                  查看全部 <ArrowRightOutlined />
                </Button>
              }
            >
              {stats.recentExecutions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 20 }}>
                  <Text type="secondary">暂无最近活动</Text>
                </div>
              ) : (
                <Timeline
                  items={stats.recentExecutions.map((exec) => ({
                    dot: getStatusIcon(exec.status),
                    children: (
                      <div>
                        <Space>
                          <Text strong>{exec.name}</Text>
                          <Tag color={exec.type === 'etl' ? 'purple' : 'cyan'}>
                            {exec.type === 'etl' ? 'ETL' : '采集'}
                          </Tag>
                        </Space>
                        <div>
                          <Tag color={getStatusColor(exec.status)}>
                            {STATUS_MAP[exec.status] || exec.status}
                          </Tag>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {new Date(exec.started_at).toLocaleString('zh-CN')}
                          </Text>
                        </div>
                      </div>
                    ),
                  }))}
                />
              )}
            </Card>
          </Col>
        </Row>

        {/* 平台功能 */}
        <Card title="平台能力">
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card size="small" type="inner" title="数据集成">
                <List
                  size="small"
                  dataSource={[
                    '多源数据采集',
                    '定时批量采集',
                    '增量数据同步',
                    '支持 API/数据库/文件',
                  ]}
                  renderItem={(item) => (
                    <List.Item>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      {item}
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card size="small" type="inner" title="数据加工">
                <List
                  size="small"
                  dataSource={[
                    '可视化 ETL 管道设计',
                    'AI 驱动数据清洗',
                    '数据脱敏与安全',
                    '基于 Pandas 的数据转换',
                  ]}
                  renderItem={(item) => (
                    <List.Item>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      {item}
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card size="small" type="inner" title="数据分析">
                <List
                  size="small"
                  dataSource={[
                    '自然语言查询 (NL2SQL)',
                    'AI 数据洞察与预测',
                    'BI 集成 (Superset)',
                    '数据质量监控',
                  ]}
                  renderItem={(item) => (
                    <List.Item>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      {item}
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        </Card>
      </Space>
    </AuthGuard>
  );
}
