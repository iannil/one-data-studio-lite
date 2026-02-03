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
  ApiOutlined,
} from '@ant-design/icons';
import { WORKSPACE_CONFIG } from '../../config/constants';

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

const DEMO_QUICK_ACTIONS: QuickAction[] = WORKSPACE_CONFIG.DEMO_QUICK_ACTIONS.map((action) => ({
  ...action,
  icon:
    action.name === '数据源配置' ? (
      <AppstoreOutlined />
    ) : action.name === '数据质量检测' ? (
      <CheckCircleOutlined />
    ) : action.name === 'NL2SQL 查询' ? (
      <ThunderboltOutlined />
    ) : (
      <FileTextOutlined />
    ),
}));

const DEMO_TODOS: TodoItem[] = [...WORKSPACE_CONFIG.DEMO_TODOS];
const DEMO_RECENTS: RecentItem[] = [...WORKSPACE_CONFIG.DEMO_RECENTS];
const DEMO_FAVORITES: RecentItem[] = [...WORKSPACE_CONFIG.DEMO_FAVORITES];

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
                value={WORKSPACE_CONFIG.DEFAULT_STATS.TODAY_VISITS}
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
                value={WORKSPACE_CONFIG.DEFAULT_STATS.WEEK_COMPLETED}
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
              <Statistic title="数据表" value={WORKSPACE_CONFIG.DATA_ASSET_DEFAULTS.TABLES} suffix="个" />
              <Progress percent={75} showInfo={false} size="small" strokeColor="#1890ff" />
            </Col>
            <Col span={6}>
              <Statistic title="API 接口" value={WORKSPACE_CONFIG.DATA_ASSET_DEFAULTS.APIS} suffix="个" />
              <Progress percent={45} showInfo={false} size="small" strokeColor="#52c41a" />
            </Col>
            <Col span={6}>
              <Statistic title="看板" value={WORKSPACE_CONFIG.DATA_ASSET_DEFAULTS.DASHBOARDS} suffix="个" />
              <Progress percent={60} showInfo={false} size="small" strokeColor="#722ed1" />
            </Col>
            <Col span={6}>
              <Statistic title="数据流程" value={WORKSPACE_CONFIG.DATA_ASSET_DEFAULTS.PIPELINES} suffix="个" />
              <Progress percent={80} showInfo={false} size="small" strokeColor="#fa8c16" />
            </Col>
          </Row>
        </Card>
      </Space>
    </div>
  );
};

export default Workspace;
