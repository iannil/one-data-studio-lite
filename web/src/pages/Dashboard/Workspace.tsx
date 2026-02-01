import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Statistic,
  List,
  Tag,
  Button,
  Avatar,
  Progress,
} from 'antd';
import {
  UserOutlined,
  ClockCircleOutlined,
  StarOutlined,
  HistoryOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface QuickAction {
  id: string;
  name: string;
  icon: React.ReactNode;
  path: string;
  color: string;
}

interface TodoItem {
  id: string;
  title: string;
  priority: 'high' | 'medium' | 'low';
  dueDate?: string;
}

interface RecentItem {
  id: string;
  name: string;
  type: 'table' | 'dashboard' | 'api' | 'pipeline';
  visitedAt: string;
}

const DEMO_QUICK_ACTIONS: QuickAction[] = [
  { id: '1', name: '数据源配置', icon: <AppstoreOutlined />, path: '/planning/datasources', color: '#1890ff' },
  { id: '2', name: '数据质量检测', icon: <CheckCircleOutlined />, path: '/development/quality', color: '#52c41a' },
  { id: '3', name: 'NL2SQL 查询', icon: <ThunderboltOutlined />, path: '/analysis/nl2sql', color: '#722ed1' },
  { id: '4', name: '清洗规则配置', icon: <FileTextOutlined />, path: '/development/cleaning', color: '#fa8c16' },
];

const DEMO_TODOS: TodoItem[] = [
  { id: '1', title: '完成用户表数据质量检测', priority: 'high', dueDate: '2026-02-02' },
  { id: '2', title: '审核待发布的数据API', priority: 'medium' },
  { id: '3', title: '配置 SeaTunnel 同步任务', priority: 'high' },
  { id: '4', title: '查看系统告警信息', priority: 'low' },
];

const DEMO_RECENTS: RecentItem[] = [
  { id: '1', name: 'user_info', type: 'table', visitedAt: '10:30' },
  { id: '2', name: 'sales_dashboard', type: 'dashboard', visitedAt: '10:15' },
  { id: '3', name: 'user_profile_api', type: 'api', visitedAt: '09:45' },
  { id: '4', name: 'daily_sync_pipeline', type: 'pipeline', visitedAt: '09:30' },
];

const DEMO_FAVORITES: RecentItem[] = [
  { id: '1', name: 'user_info', type: 'table', visitedAt: '' },
  { id: '2', name: 'orders', type: 'table', visitedAt: '' },
  { id: '3', name: 'sales_dashboard', type: 'dashboard', visitedAt: '' },
  { id: '4', name: 'user_profile_api', type: 'api', visitedAt: '' },
];

const Workspace: React.FC = () => {
  const [todos, setTodos] = useState<TodoItem[]>(DEMO_TODOS);
  const [recents, setRecents] = useState<RecentItem[]>(DEMO_RECENTS);
  const [favorites, setFavorites] = useState<RecentItem[]>(DEMO_FAVORITES);

  const handleTodoComplete = (id: string) => {
    setTodos(todos.filter((t) => t.id !== id));
  };

  const getPriorityTag = (priority: TodoItem['priority']) => {
    const config = {
      high: { color: 'error', text: '高' },
      medium: { color: 'warning', text: '中' },
      low: { color: 'default', text: '低' },
    };
    const { color, text } = config[priority];
    return <Tag color={color}>{text}</Tag>;
  };

  const getTypeTag = (type: RecentItem['type']) => {
    const config = {
      table: { color: 'blue', text: '数据表' },
      dashboard: { color: 'purple', text: '看板' },
      api: { color: 'orange', text: 'API' },
      pipeline: { color: 'green', text: '流程' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <UserOutlined /> 个人工作台
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 统计概览 */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="待处理任务"
                value={todos.length}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: todos.length > 0 ? '#faad14' : undefined }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="今日访问"
                value={12}
                suffix="个"
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="收藏资产"
                value={favorites.length}
                suffix="个"
                prefix={<StarOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="本周完成"
                value={28}
                suffix="个"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16}>
          {/* 快捷操作 */}
          <Col span={12}>
            <Card title="快捷功能" size="small">
              <Row gutter={8}>
                {DEMO_QUICK_ACTIONS.map((action) => (
                  <Col span={12} key={action.id}>
                    <Button
                      block
                      style={{ marginBottom: 8, height: 60, borderColor: action.color }}
                    >
                      <Space direction="vertical" size={2}>
                        <span style={{ color: action.color }}>{action.icon}</span>
                        <span>{action.name}</span>
                      </Space>
                    </Button>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>

          {/* 待办事项 */}
          <Col span={12}>
            <Card
              size="small"
              title={`待办事项 (${todos.length})`}
              extra={<Text type="secondary">今日</Text>}
            >
              <List
                size="small"
                dataSource={todos}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        size="small"
                        onClick={() => handleTodoComplete(item.id)}
                      >
                        完成
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size="small"
                          style={{
                            backgroundColor:
                              item.priority === 'high'
                                ? '#f5222d'
                                : item.priority === 'medium'
                                ? '#faad14'
                                : '#52c41a',
                          }}
                        >
                          {item.title[0]}
                        </Avatar>
                      }
                      title={item.title}
                      description={
                        <Space>
                          {getPriorityTag(item.priority)}
                          {item.dueDate && <Text type="secondary">截止: {item.dueDate}</Text>}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16}>
          {/* 最近访问 */}
          <Col span={12}>
            <Card
              size="small"
              title="最近访问"
              extra={<Button type="link" size="small">清空</Button>}
            >
              <List
                size="small"
                dataSource={recents}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size="small"
                          icon={
                            item.type === 'table'
                              ? <FileTextOutlined />
                              : item.type === 'dashboard'
                              ? <AppstoreOutlined />
                              : <ApiOutlined />
                          }
                        />
                      }
                      title={item.name}
                      description={getTypeTag(item.type)}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {item.visitedAt}
                    </Text>
                  </List.Item>
                )}
              />
            </Card>
          </Col>

          {/* 我的收藏 */}
          <Col span={12}>
            <Card
              size="small"
              title="我的收藏"
              extra={<Button type="link" size="small">管理</Button>}
            >
              <List
                size="small"
                dataSource={favorites}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size="small"
                          icon={<StarOutlined />}
                          style={{ backgroundColor: '#faad14' }}
                        />
                      }
                      title={item.name}
                      description={getTypeTag(item.type)}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>

        {/* 数据概览 */}
        <Card size="small" title="数据资产概览">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="数据表" value={156} suffix="个" />
              <Progress percent={75} showInfo={false} size="small" strokeColor="#1890ff" />
            </Col>
            <Col span={6}>
              <Statistic title="API 接口" value={23} suffix="个" />
              <Progress percent={45} showInfo={false} size="small" strokeColor="#52c41a" />
            </Col>
            <Col span={6}>
              <Statistic title="看板" value={8} suffix="个" />
              <Progress percent={60} showInfo={false} size="small" strokeColor="#722ed1" />
            </Col>
            <Col span={6}>
              <Statistic title="数据流程" value={12} suffix="个" />
              <Progress percent={80} showInfo={false} size="small" strokeColor="#fa8c16" />
            </Col>
          </Row>
        </Card>
      </Space>
    </div>
  );
};

export default Workspace;
