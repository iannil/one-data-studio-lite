import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Typography,
  Space,
  Alert,
  Tabs,
  Descriptions,
  Upload,
  Avatar,
  Switch,
  Select,
  DatePicker,
  Table,
  Tag,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SettingOutlined,
  HistoryOutlined,
  EditOutlined,
  CameraOutlined,
  MailOutlined,
  PhoneOutlined,
  BankOutlined,
  EnvironmentOutlined,
  UploadOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface UserProfile {
  id: string;
  username: string;
  realName: string;
  email: string;
  phone?: string;
  avatar?: string;
  department?: string;
  position?: string;
  location?: string;
  bio?: string;
  status: 'active' | 'inactive' | 'locked';
  lastLoginTime?: string;
  createdAt: string;
}

interface OperationLog {
  id: string;
  operation: string;
  module: string;
  ip: string;
  result: 'success' | 'failure';
  createdAt: string;
}

interface Preference {
  key: string;
  label: string;
  value: boolean | string;
  type: 'switch' | 'select';
  options?: { label: string; value: string }[];
}

const DEMO_USER: UserProfile = {
  id: '1',
  username: 'admin',
  realName: '系统管理员',
  email: 'admin@example.com',
  phone: '13800138000',
  avatar: '',
  department: '技术部',
  position: '技术总监',
  location: '北京',
  bio: '负责系统架构设计与团队管理',
  status: 'active',
  lastLoginTime: '2026-02-01 09:30:00',
  createdAt: '2025-01-01 10:00:00',
};

const DEMO_LOGS: OperationLog[] = [
  { id: '1', operation: '用户登录', module: '认证', ip: '192.168.1.100', result: 'success', createdAt: '2026-02-01 09:30:00' },
  { id: '2', operation: '修改密码', module: '个人中心', ip: '192.168.1.100', result: 'success', createdAt: '2026-01-28 14:20:00' },
  { id: '3', operation: '创建数据源', module: '数据规划', ip: '192.168.1.100', result: 'success', createdAt: '2026-01-25 10:15:00' },
  { id: '4', operation: '删除用户', module: '用户管理', ip: '192.168.1.100', result: 'success', createdAt: '2026-01-20 16:45:00' },
  { id: '5', operation: '登录失败', module: '认证', ip: '192.168.1.105', result: 'failure', createdAt: '2026-01-18 08:30:00' },
  { id: '6', operation: '修改配置', module: '系统设置', ip: '192.168.1.100', result: 'success', createdAt: '2026-01-15 11:20:00' },
  { id: '7', operation: '导出数据', module: '数据分析', ip: '192.168.1.100', result: 'success', createdAt: '2026-01-10 15:30:00' },
];

const PREFERENCES: Preference[] = [
  { key: 'emailNotification', label: '邮件通知', value: true, type: 'switch' },
  { key: 'smsNotification', label: '短信通知', value: false, type: 'switch' },
  { key: 'desktopNotification', label: '桌面通知', value: true, type: 'switch' },
  { key: 'taskReminder', label: '任务提醒', value: true, type: 'switch' },
  { key: 'language', label: '语言设置', value: 'zh-CN', type: 'select', options: [
    { label: '简体中文', value: 'zh-CN' },
    { label: 'English', value: 'en-US' },
  ]},
  { key: 'timezone', label: '时区设置', value: 'Asia/Shanghai', type: 'select', options: [
    { label: '北京时间 (GMT+8)', value: 'Asia/Shanghai' },
    { label: '纽约时间 (GMT-5)', value: 'America/New_York' },
    { label: '伦敦时间 (GMT+0)', value: 'Europe/London' },
  ]},
  { key: 'theme', label: '主题风格', value: 'light', type: 'select', options: [
    { label: '浅色', value: 'light' },
    { label: '深色', value: 'dark' },
    { label: '跟随系统', value: 'auto' },
  ]},
  { key: 'pageSize', label: '每页显示数量', value: '20', type: 'select', options: [
    { label: '10条/页', value: '10' },
    { label: '20条/页', value: '20' },
    { label: '50条/页', value: '50' },
    { label: '100条/页', value: '100' },
  ]},
];

const Profile: React.FC = () => {
  const [user, setUser] = useState<UserProfile>(DEMO_USER);
  const [preferences, setPreferences] = useState<Record<string, boolean | string>>(
    PREFERENCES.reduce((acc, p) => ({ ...acc, [p.key]: p.value }), {})
  );
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  const handleEditProfile = () => {
    setEditingProfile(true);
    profileForm.setFieldsValue(user);
  };

  const handleProfileCancel = () => {
    setEditingProfile(false);
    profileForm.resetFields();
  };

  const handleProfileSave = () => {
    profileForm.validateFields().then((values) => {
      setUser({ ...user, ...values });
      setEditingProfile(false);
      message.success('个人信息更新成功');
    });
  };

  const handlePasswordChange = () => {
    passwordForm.validateFields().then((values) => {
      if (values.newPassword !== values.confirmPassword) {
        message.error('两次输入的密码不一致');
        return;
      }
      message.success('密码修改成功，请重新登录');
      passwordForm.resetFields();
    });
  };

  const handlePreferenceChange = (key: string, value: boolean | string) => {
    setPreferences((prev) => ({ ...prev, [key]: value }));
    message.success('设置已保存');
  };

  const handleAvatarUpload = (info: any) => {
    if (info.file.status === 'done') {
      message.success('头像上传成功');
      setUser({ ...user, avatar: URL.createObjectURL(info.file.originFileObj) });
    }
  };

  const getLogResultTag = (result: OperationLog['result']) => {
    return result === 'success' ? (
      <Tag color="success">成功</Tag>
    ) : (
      <Tag color="error">失败</Tag>
    );
  };

  const logColumns = [
    { title: '操作', dataIndex: 'operation', key: 'operation' },
    { title: '模块', dataIndex: 'module', key: 'module' },
    { title: 'IP地址', dataIndex: 'ip', key: 'ip' },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 80,
      render: (result: OperationLog['result']) => getLogResultTag(result),
    },
    { title: '时间', dataIndex: 'createdAt', key: 'createdAt', width: 160 },
  ];

  const tabItems = [
    {
      key: 'profile',
      label: (
        <span>
          <UserOutlined /> 基本信息
        </span>
      ),
      children: (
        <Row gutter={24}>
          <Col span={8}>
            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }} align="center">
                <Avatar size={120} src={user.avatar} icon={<UserOutlined />} />
                <Upload
                  showUploadList={false}
                  beforeUpload={() => false}
                  onChange={handleAvatarUpload}
                  accept="image/*"
                >
                  <Button icon={<CameraOutlined />} size="small">
                    更换头像
                  </Button>
                </Upload>
                <Divider style={{ margin: '12px 0', width: '100%' }} />
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={user.status === 'active' ? 'success' : 'error'}>
                      {user.status === 'active' ? '正常' : '异常'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="注册时间">{user.createdAt}</Descriptions.Item>
                  <Descriptions.Item label="最后登录">{user.lastLoginTime}</Descriptions.Item>
                </Descriptions>
              </Space>
            </Card>
          </Col>
          <Col span={16}>
            <Card
              size="small"
              title="个人信息"
              extra={
                !editingProfile && (
                  <Button icon={<EditOutlined />} onClick={handleEditProfile}>
                    编辑
                  </Button>
                )
              }
            >
              {editingProfile ? (
                <Form
                  form={profileForm}
                  layout="vertical"
                  initialValues={user}
                >
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="realName"
                        label="真实姓名"
                        rules={[{ required: true, message: '请输入真实姓名' }]}
                      >
                        <Input prefix={<UserOutlined />} placeholder="请输入真实姓名" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="username"
                        label="用户名"
                      >
                        <Input prefix={<UserOutlined />} disabled />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="email"
                        label="邮箱"
                        rules={[
                          { required: true, message: '请输入邮箱' },
                          { type: 'email', message: '邮箱格式不正确' },
                        ]}
                      >
                        <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="phone"
                        label="手机号"
                        rules={[{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }]}
                      >
                        <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="department" label="部门">
                        <Input prefix={<BankOutlined />} placeholder="请输入部门" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="position" label="职位">
                        <Input prefix={<UserOutlined />} placeholder="请输入职位" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item name="location" label="所在地">
                    <Input prefix={<EnvironmentOutlined />} placeholder="请输入所在地" />
                  </Form.Item>

                  <Form.Item name="bio" label="个人简介">
                    <TextArea rows={3} placeholder="请输入个人简介" />
                  </Form.Item>

                  <Form.Item>
                    <Space>
                      <Button type="primary" onClick={handleProfileSave}>
                        保存
                      </Button>
                      <Button onClick={handleProfileCancel}>
                        取消
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>
              ) : (
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="真实姓名">{user.realName}</Descriptions.Item>
                  <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
                  <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
                  <Descriptions.Item label="手机号">{user.phone || '-'}</Descriptions.Item>
                  <Descriptions.Item label="部门">{user.department || '-'}</Descriptions.Item>
                  <Descriptions.Item label="职位">{user.position || '-'}</Descriptions.Item>
                  <Descriptions.Item label="所在地" span={2}>{user.location || '-'}</Descriptions.Item>
                  <Descriptions.Item label="个人简介" span={2}>{user.bio || '-'}</Descriptions.Item>
                </Descriptions>
              )}
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'security',
      label: (
        <span>
          <LockOutlined /> 安全设置
        </span>
      ),
      children: (
        <Row gutter={24}>
          <Col span={12}>
            <Card size="small" title="修改密码">
              <Alert
                message="密码安全提示"
                description="为了您的账户安全，建议定期更换密码。密码长度不少于8位，包含大小写字母、数字和特殊字符。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Form form={passwordForm} layout="vertical">
                <Form.Item
                  name="oldPassword"
                  label="当前密码"
                  rules={[{ required: true, message: '请输入当前密码' }]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="请输入当前密码" />
                </Form.Item>
                <Form.Item
                  name="newPassword"
                  label="新密码"
                  rules={[
                    { required: true, message: '请输入新密码' },
                    { min: 8, message: '密码长度不少于8位' },
                    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, message: '密码需包含大小写字母和数字' },
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" />
                </Form.Item>
                <Form.Item
                  name="confirmPassword"
                  label="确认新密码"
                  dependencies={['newPassword']}
                  rules={[
                    { required: true, message: '请再次输入新密码' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('newPassword') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('两次输入的密码不一致'));
                      },
                    }),
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="请再次输入新密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" onClick={handlePasswordChange} block>
                    修改密码
                  </Button>
                </Form.Item>
              </Form>
            </Card>
          </Col>
          <Col span={12}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Card size="small" title="登录安全">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="上次登录时间">
                    {user.lastLoginTime}
                  </Descriptions.Item>
                  <Descriptions.Item label="上次登录IP">
                    192.168.1.100
                  </Descriptions.Item>
                  <Descriptions.Item label="登录地点">
                    北京市
                  </Descriptions.Item>
                </Descriptions>
              </Card>
              <Card size="small" title="安全建议">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Alert message="定期更换密码" type="info" showIcon />
                  <Alert message="不要在公共设备上保存密码" type="info" showIcon />
                  <Alert message="开启二次验证（即将上线）" type="warning" showIcon />
                </Space>
              </Card>
            </Space>
          </Col>
        </Row>
      ),
    },
    {
      key: 'preferences',
      label: (
        <span>
          <SettingOutlined /> 偏好设置
        </span>
      ),
      children: (
        <Row gutter={24}>
          <Col span={12}>
            <Card size="small" title="通知设置">
              <Space direction="vertical" style={{ width: '100%' }}>
                {PREFERENCES.filter(p => p.type === 'switch' && p.key.includes('Notification')).map((pref) => (
                  <Row key={pref.key} gutter={16} align="middle">
                    <Col span={16}>
                      <Text>{pref.label}</Text>
                    </Col>
                    <Col span={8} style={{ textAlign: 'right' }}>
                      <Switch
                        checked={preferences[pref.key] as boolean}
                        onChange={(checked) => handlePreferenceChange(pref.key, checked)}
                      />
                    </Col>
                  </Row>
                ))}
              </Space>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="系统设置">
              <Space direction="vertical" style={{ width: '100%' }}>
                {PREFERENCES.filter(p => p.type === 'select').map((pref) => (
                  <Form.Item key={pref.key} label={pref.label} style={{ marginBottom: 12 }}>
                    <Select
                      value={preferences[pref.key]}
                      onChange={(value) => handlePreferenceChange(pref.key, value)}
                      options={pref.options}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'logs',
      label: (
        <span>
          <HistoryOutlined /> 操作日志
        </span>
      ),
      children: (
        <Card size="small" title="近期操作记录">
          <Alert
            message="日志说明"
            description="系统记录您的操作历史，包括登录、数据修改、配置变更等。日志保留最近90天的记录。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            columns={logColumns}
            dataSource={DEMO_LOGS.map((log) => ({ ...log, key: log.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <UserOutlined /> 个人中心
      </Title>
      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
};

export default Profile;
