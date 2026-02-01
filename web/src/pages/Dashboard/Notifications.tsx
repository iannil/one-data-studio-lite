import React, { useState } from 'react';
import {
  Card,
  List,
  Tag,
  Badge,
  Button,
  Typography,
  Space,
  Tabs,
  Switch,
  Empty,
  Tooltip,
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  DeleteOutlined,
  CheckOutlined,
  CheckSquareOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

type NotificationType = 'system' | 'business' | 'alert' | 'task';
type NotificationStatus = 'unread' | 'read';
type Priority = 'low' | 'medium' | 'high' | 'critical';

interface Notification {
  id: string;
  type: NotificationType;
  status: NotificationStatus;
  priority: Priority;
  title: string;
  content: string;
  createdAt: string;
  link?: string;
}

const DEMO_NOTIFICATIONS: Notification[] = [
  {
    id: '1',
    type: 'alert',
    status: 'unread',
    priority: 'high',
    title: 'AI 清洗服务响应时间告警',
    content: 'AI 清洗服务当前响应时间超过 3000ms，建议检查服务状态',
    createdAt: '2026-02-01 10:30:00',
  },
  {
    id: '2',
    type: 'system',
    status: 'unread',
    priority: 'medium',
    title: '系统维护通知',
    content: '系统将于 2026-02-02 02:00 进行例行维护，预计耗时 30 分钟',
    createdAt: '2026-02-01 09:15:00',
  },
  {
    id: '3',
    type: 'business',
    status: 'unread',
    priority: 'low',
    title: '数据同步完成',
    content: 'orders 表数据同步已完成，共处理 125,430 条记录',
    createdAt: '2026-02-01 08:45:00',
  },
  {
    id: '4',
    type: 'task',
    status: 'read',
    priority: 'medium',
    title: '待审核的数据 API',
    content: '您有 2 个数据 API 等待审核，请及时处理',
    createdAt: '2026-01-31 16:20:00',
  },
  {
    id: '5',
    type: 'system',
    status: 'read',
    priority: 'low',
    title: '密码即将过期提醒',
    content: '您的密码将在 7 天后过期，请及时修改',
    createdAt: '2026-01-30 10:00:00',
  },
];

const Notifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>(DEMO_NOTIFICATIONS);
  const [activeTab, setActiveTab] = useState('all');

  const unreadCount = notifications.filter((n) => n.status === 'unread').length;

  const handleMarkAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, status: 'read' as const } : n
      )
    );
  };

  const handleMarkAllAsRead = () => {
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, status: 'read' as const }))
    );
  };

  const handleDelete = (id: string) => {
    setNotifications(notifications.filter((n) => n.id !== id));
  };

  const handleClearRead = () => {
    setNotifications(notifications.filter((n) => n.status === 'unread'));
  };

  const getIcon = (type: NotificationType, priority: Priority) => {
    if (priority === 'critical' || priority === 'high') {
      return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />;
    }
    switch (type) {
      case 'system':
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      case 'business':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'alert':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'task':
        return <CheckCircleOutlined style={{ color: '#722ed1' }} />;
      default:
        return <BellOutlined />;
    }
  };

  const getTypeTag = (type: NotificationType) => {
    const config = {
      system: { color: 'blue', text: '系统' },
      business: { color: 'green', text: '业务' },
      alert: { color: 'orange', text: '告警' },
      task: { color: 'purple', text: '任务' },
    };
    const { color, text } = config[type];
    return <Tag color={color}>{text}</Tag>;
  };

  const getPriorityTag = (priority: Priority) => {
    const config = {
      critical: { color: 'error', text: '紧急' },
      high: { color: 'warning', text: '高' },
      medium: { color: 'default', text: '中' },
      low: { color: 'default', text: '低' },
    };
    const { color, text } = config[priority];
    return <Tag color={color}>{text}</Tag>;
  };

  const getFilteredNotifications = () => {
    switch (activeTab) {
      case 'unread':
        return notifications.filter((n) => n.status === 'unread');
      case 'system':
        return notifications.filter((n) => n.type === 'system');
      case 'business':
        return notifications.filter((n) => n.type === 'business');
      case 'alert':
        return notifications.filter((n) => n.type === 'alert');
      case 'task':
        return notifications.filter((n) => n.type === 'task');
      default:
        return notifications;
    }
  };

  const tabItems = [
    {
      key: 'all',
      label: (
        <Badge count={notifications.length} overflowCount={99}>
          全部
        </Badge>
      ),
    },
    {
      key: 'unread',
      label: (
        <Badge count={unreadCount} overflowCount={99}>
          未读
        </Badge>
      ),
    },
    { key: 'system', label: '系统' },
    { key: 'business', label: '业务' },
    { key: 'alert', label: '告警' },
    { key: 'task', label: '任务' },
  ];

  const filteredNotifications = getFilteredNotifications();

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <BellOutlined /> 消息通知中心
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Card
          size="small"
          title={
            <Space>
              <span>通知消息</span>
              <Badge count={unreadCount} offset={[10, 0]}>
                <BellOutlined />
              </Badge>
            </Space>
          }
          extra={
            <Space>
              <Button size="small" onClick={handleMarkAllAsRead} disabled={unreadCount === 0}>
                全部已读
              </Button>
              <Button size="small" type="link" danger onClick={handleClearRead}>
                清空已读
              </Button>
            </Space>
          }
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems.map((tab) => ({
              key: tab.key,
              label: tab.label,
            }))}
          >
            {filteredNotifications.length === 0 ? (
              <Empty description="暂无通知" />
            ) : (
              <List
                size="small"
                dataSource={filteredNotifications}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      backgroundColor: item.status === 'unread' ? '#f0f5ff' : 'transparent',
                      padding: '12px',
                      borderRadius: 4,
                    }}
                    actions={[
                      item.status === 'unread' && (
                        <Button
                          type="link"
                          size="small"
                          icon={<CheckOutlined />}
                          onClick={() => handleMarkAsRead(item.id)}
                        >
                          标记已读
                        </Button>
                      ),
                      <Button
                        type="link"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(item.id)}
                      >
                        删除
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={getIcon(item.type, item.priority)}
                      title={
                        <Space>
                          <Text
                            strong={item.status === 'unread'}
                            style={{
                              textDecoration: item.status === 'unread' ? 'none' : 'line-through',
                            }}
                          >
                            {item.title}
                          </Text>
                          {getTypeTag(item.type)}
                          {item.priority !== 'low' && getPriorityTag(item.priority)}
                        </Space>
                      }
                      description={
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text>{item.content}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {item.createdAt}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Tabs>
        </Card>
      </Space>
    </div>
  );
};

export default Notifications;
