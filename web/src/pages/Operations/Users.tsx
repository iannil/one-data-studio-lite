import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Form,
  Input,
  Select,
  message,
  Typography,
  Space,
  Alert,
  Modal,
  Tabs,
  Tree,
  Switch,
  Divider,
  Row,
  Col,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import {
  UserOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  TeamOutlined,
  LockOutlined,
  SearchOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

type UserStatus = 'active' | 'inactive' | 'locked';
type UserRole = 'admin' | 'analyst' | 'developer' | 'viewer';

interface User {
  id: string;
  username: string;
  realName: string;
  email: string;
  phone?: string;
  status: UserStatus;
  roles: UserRole[];
  department?: string;
  position?: string;
  lastLoginTime?: string;
  createdAt: string;
}

interface Organization {
  id: string;
  name: string;
  code: string;
  parentId?: string;
  level: number;
  userCount: number;
  children?: Organization[];
}

interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  permissions: string[];
  userCount: number;
  isSystem: boolean;
}

const DEMO_USERS: User[] = [
  {
    id: '1',
    username: 'admin',
    realName: '系统管理员',
    email: 'admin@example.com',
    phone: '13800138000',
    status: 'active',
    roles: ['admin'],
    department: '技术部',
    position: '技术总监',
    lastLoginTime: '2026-02-01 09:30:00',
    createdAt: '2025-01-01 10:00:00',
  },
  {
    id: '2',
    username: 'zhang_san',
    realName: '张三',
    email: 'zhangsan@example.com',
    phone: '13900139001',
    status: 'active',
    roles: ['analyst'],
    department: '数据部',
    position: '数据分析师',
    lastLoginTime: '2026-02-01 08:45:00',
    createdAt: '2025-03-15 14:20:00',
  },
  {
    id: '3',
    username: 'li_si',
    realName: '李四',
    email: 'lisi@example.com',
    phone: '13900139002',
    status: 'active',
    roles: ['developer'],
    department: '技术部',
    position: '后端开发',
    lastLoginTime: '2026-01-31 18:20:00',
    createdAt: '2025-05-20 10:30:00',
  },
  {
    id: '4',
    username: 'wang_wu',
    realName: '王五',
    email: 'wangwu@example.com',
    phone: '13900139003',
    status: 'inactive',
    roles: ['viewer'],
    department: '市场部',
    position: '市场专员',
    lastLoginTime: '2026-01-25 11:00:00',
    createdAt: '2025-08-10 09:15:00',
  },
  {
    id: '5',
    username: 'zhao_liu',
    realName: '赵六',
    email: 'zhaoliu@example.com',
    phone: '13900139004',
    status: 'locked',
    roles: ['viewer'],
    department: '销售部',
    position: '销售代表',
    lastLoginTime: '2026-01-20 16:30:00',
    createdAt: '2025-10-05 13:40:00',
  },
];

const DEMO_ORGANIZATIONS: Organization[] = [
  {
    id: '1',
    name: '总公司',
    code: 'HQ',
    level: 0,
    userCount: 50,
    children: [
      {
        id: '2',
        name: '技术部',
        code: 'TECH',
        parentId: '1',
        level: 1,
        userCount: 18,
        children: [
          { id: '5', name: '前端组', code: 'FE', parentId: '2', level: 2, userCount: 6 },
          { id: '6', name: '后端组', code: 'BE', parentId: '2', level: 2, userCount: 8 },
          { id: '7', name: '运维组', code: 'OPS', parentId: '2', level: 2, userCount: 4 },
        ],
      },
      {
        id: '3',
        name: '数据部',
        code: 'DATA',
        parentId: '1',
        level: 1,
        userCount: 12,
        children: [
          { id: '8', name: '数据工程组', code: 'DE', parentId: '3', level: 2, userCount: 7 },
          { id: '9', name: '数据分析组', code: 'DA', parentId: '3', level: 2, userCount: 5 },
        ],
      },
      {
        id: '4',
        name: '市场部',
        code: 'MKT',
        parentId: '1',
        level: 1,
        userCount: 10,
        children: [
          { id: '10', name: '品牌组', code: 'BRAND', parentId: '4', level: 2, userCount: 5 },
          { id: '11', name: '数字营销组', code: 'DIGITAL', parentId: '4', level: 2, userCount: 5 },
        ],
      },
    ],
  },
];

const DEMO_ROLES: Role[] = [
  {
    id: '1',
    name: '管理员',
    code: 'admin',
    description: '系统管理员，拥有所有权限',
    permissions: ['*'],
    userCount: 2,
    isSystem: true,
  },
  {
    id: '2',
    name: '数据分析师',
    code: 'analyst',
    description: '数据查询与分析权限',
    permissions: ['data.query', 'data.export', 'report.view', 'report.create'],
    userCount: 12,
    isSystem: false,
  },
  {
    id: '3',
    name: '开发人员',
    code: 'developer',
    description: '系统开发与配置权限',
    permissions: ['system.config', 'data.source', 'etl.config', 'api.manage'],
    userCount: 8,
    isSystem: false,
  },
  {
    id: '4',
    name: '访客',
    code: 'viewer',
    description: '只读权限，仅可查看报表',
    permissions: ['report.view'],
    userCount: 28,
    isSystem: false,
  },
];

const USER_STATUS_OPTIONS = [
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'inactive' },
  { label: '锁定', value: 'locked' },
];

const ROLE_OPTIONS = [
  { label: '管理员', value: 'admin' },
  { label: '数据分析师', value: 'analyst' },
  { label: '开发人员', value: 'developer' },
  { label: '访客', value: 'viewer' },
];

const DEPARTMENT_OPTIONS = [
  { label: '技术部', value: '技术部' },
  { label: '数据部', value: '数据部' },
  { label: '市场部', value: '市场部' },
  { label: '销售部', value: '销售部' },
  { label: '财务部', value: '财务部' },
  { label: '人事部', value: '人事部' },
];

const Users: React.FC = () => {
  const [users, setUsers] = useState<User[]>(DEMO_USERS);
  const [organizations] = useState<Organization[]>(DEMO_ORGANIZATIONS);
  const [roles, setRoles] = useState<Role[]>(DEMO_ROLES);
  const [userModalVisible, setUserModalVisible] = useState(false);
  const [orgModalVisible, setOrgModalVisible] = useState(false);
  const [roleModalVisible, setRoleModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<UserStatus | 'all'>('all');
  const [userForm] = Form.useForm();
  const [orgForm] = Form.useForm();
  const [roleForm] = Form.useForm();

  // User management handlers
  const handleCreateUser = () => {
    setEditingUser(null);
    userForm.resetFields();
    userForm.setFieldsValue({
      status: 'active',
      roles: ['viewer'],
    });
    setUserModalVisible(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    userForm.setFieldsValue(user);
    setUserModalVisible(true);
  };

  const handleDeleteUser = (id: string) => {
    setUsers(users.filter((u) => u.id !== id));
    message.success('用户删除成功');
  };

  const handleToggleUserStatus = (id: string) => {
    setUsers((prev) =>
      prev.map((u) =>
        u.id === id
          ? { ...u, status: u.status === 'active' ? ('inactive' as const) : ('active' as const) }
          : u
      )
    );
    message.success('用户状态已更新');
  };

  const handleUserModalOk = () => {
    userForm.validateFields().then((values) => {
      if (editingUser) {
        setUsers((prev) =>
          prev.map((u) =>
            u.id === editingUser.id ? { ...u, ...values } : u
          )
        );
        message.success('用户更新成功');
      } else {
        const newUser: User = {
          id: Date.now().toString(),
          username: values.username,
          realName: values.realName,
          email: values.email,
          phone: values.phone,
          status: values.status,
          roles: values.roles,
          department: values.department,
          position: values.position,
          createdAt: new Date().toLocaleString('zh-CN'),
        };
        setUsers([newUser, ...users]);
        message.success('用户创建成功');
      }
      setUserModalVisible(false);
    });
  };

  // Organization handlers
  const handleCreateOrg = () => {
    orgForm.resetFields();
    setOrgModalVisible(true);
  };

  const handleOrgModalOk = () => {
    message.success('组织创建成功');
    setOrgModalVisible(false);
  };

  // Role handlers
  const handleCreateRole = () => {
    setEditingRole(null);
    roleForm.resetFields();
    setRoleModalVisible(true);
  };

  const handleEditRole = (role: Role) => {
    setEditingRole(role);
    roleForm.setFieldsValue(role);
    setRoleModalVisible(true);
  };

  const handleDeleteRole = (id: string) => {
    setRoles(roles.filter((r) => r.id !== id));
    message.success('角色删除成功');
  };

  const handleRoleModalOk = () => {
    roleForm.validateFields().then((values) => {
      if (editingRole) {
        setRoles((prev) =>
          prev.map((r) =>
            r.id === editingRole.id ? { ...r, ...values } : r
          )
        );
        message.success('角色更新成功');
      } else {
        const newRole: Role = {
          id: Date.now().toString(),
          name: values.name,
          code: values.code,
          description: values.description,
          permissions: values.permissions || [],
          userCount: 0,
          isSystem: false,
        };
        setRoles([...roles, newRole]);
        message.success('角色创建成功');
      }
      setRoleModalVisible(false);
    });
  };

  const getUserStatusTag = (status: UserStatus) => {
    const config = {
      active: { color: 'success', text: '启用' },
      inactive: { color: 'default', text: '禁用' },
      locked: { color: 'error', text: '锁定' },
    };
    const { color, text } = config[status];
    return <Tag color={color}>{text}</Tag>;
  };

  const getRoleTag = (role: UserRole) => {
    const config = {
      admin: { color: 'red', text: '管理员' },
      analyst: { color: 'blue', text: '分析师' },
      developer: { color: 'purple', text: '开发' },
      viewer: { color: 'default', text: '访客' },
    };
    const { color, text } = config[role];
    return <Tag color={color}>{text}</Tag>;
  };

  const filteredUsers = users.filter((user) => {
    const matchSearch =
      !searchText ||
      user.realName.toLowerCase().includes(searchText.toLowerCase()) ||
      user.username.toLowerCase().includes(searchText.toLowerCase()) ||
      user.email.toLowerCase().includes(searchText.toLowerCase());
    const matchStatus = statusFilter === 'all' || user.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const userColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: '姓名', dataIndex: 'realName', key: 'realName', width: 100 },
    { title: '邮箱', dataIndex: 'email', key: 'email', ellipsis: true },
    { title: '手机', dataIndex: 'phone', key: 'phone', width: 120, render: (p?: string) => p || '-' },
    { title: '部门', dataIndex: 'department', key: 'department', width: 100, render: (d?: string) => d || '-' },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      width: 150,
      render: (roles: UserRole[]) => roles.map((r) => getRoleTag(r)),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: UserStatus, record: User) => (
        <Switch
          size="small"
          checked={status === 'active'}
          onChange={() => handleToggleUserStatus(record.id)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    { title: '最后登录', dataIndex: 'lastLoginTime', key: 'lastLoginTime', width: 160 },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: User) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditUser(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDeleteUser(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const roleColumns = [
    { title: '角色名称', dataIndex: 'name', key: 'name' },
    { title: '编码', dataIndex: 'code', key: 'code' },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '权限',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (perms: string[]) => perms.length > 0
        ? perms.slice(0, 3).map((p) => <Tag key={p} color="blue">{p}</Tag>)
        : '-',
    },
    { title: '用户数', dataIndex: 'userCount', key: 'userCount', width: 80 },
    {
      title: '系统角色',
      dataIndex: 'isSystem',
      key: 'isSystem',
      width: 100,
      render: (isSystem: boolean) => isSystem
        ? <Tag color="orange">是</Tag>
        : <Tag>否</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: Role) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditRole(record)}
            disabled={record.isSystem}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDeleteRole(record.id)}
            disabled={record.isSystem}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const renderOrgTree = (data: Organization[]): DataNode[] => {
    return data.map((org) => ({
      title: (
        <Space>
          <span>{org.name}</span>
          <Tag color="blue">{org.userCount}人</Tag>
        </Space>
      ),
      key: org.id,
      icon: <TeamOutlined />,
      children: org.children ? renderOrgTree(org.children) : undefined,
    }));
  };

  const tabItems = [
    {
      key: 'users',
      label: `用户管理 (${users.length})`,
      children: (
        <Card
          size="small"
          title="用户列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateUser}>
              新建用户
            </Button>
          }
        >
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="搜索用户名/姓名/邮箱..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 250 }}
              prefix={<SearchOutlined />}
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="active">启用</Select.Option>
              <Select.Option value="inactive">禁用</Select.Option>
              <Select.Option value="locked">锁定</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Space>
          <Table
            columns={userColumns}
            dataSource={filteredUsers.map((u) => ({ ...u, key: u.id }))}
            pagination={{ pageSize: 10 }}
            size="small"
            scroll={{ x: 1200 }}
          />
        </Card>
      ),
    },
    {
      key: 'org',
      label: '组织架构',
      children: (
        <Card
          size="small"
          title="组织结构"
          extra={
            <Button icon={<PlusOutlined />} onClick={handleCreateOrg}>
              新建组织
            </Button>
          }
        >
          <Row gutter={16}>
            <Col span={8}>
              <Alert
                message="组织架构说明"
                description="左侧展示组织树形结构，支持多层级部门管理。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Card size="small" title="组织树">
                <Tree
                  showIcon
                  defaultExpandAll
                  treeData={renderOrgTree(organizations)}
                  onSelect={(keys) => {
                    const findOrg = (data: Organization[], id: string): Organization | null => {
                      for (const org of data) {
                        if (org.id === id) return org;
                        if (org.children) {
                          const found = findOrg(org.children, id);
                          if (found) return found;
                        }
                      }
                      return null;
                    };
                    if (keys.length > 0) {
                      setSelectedOrg(findOrg(organizations, keys[0] as string));
                    }
                  }}
                />
              </Card>
            </Col>
            <Col span={16}>
              <Card size="small" title="组织详情">
                {selectedOrg ? (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Text strong>组织名称：</Text>
                        <Text>{selectedOrg.name}</Text>
                      </Col>
                      <Col span={8}>
                        <Text strong>组织编码：</Text>
                        <Text>{selectedOrg.code}</Text>
                      </Col>
                      <Col span={8}>
                        <Text strong>人员数量：</Text>
                        <Text>{selectedOrg.userCount} 人</Text>
                      </Col>
                    </Row>
                    <Divider />
                    <Alert
                      message="成员列表"
                      description={`该组织下的 ${selectedOrg.userCount} 名成员`}
                      type="info"
                    />
                  </Space>
                ) : (
                  <Alert
                    message="请选择左侧组织查看详情"
                    type="info"
                    showIcon
                  />
                )}
              </Card>
            </Col>
          </Row>
        </Card>
      ),
    },
    {
      key: 'roles',
      label: `角色管理 (${roles.length})`,
      children: (
        <Card
          size="small"
          title="角色列表"
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateRole}>
              新建角色
            </Button>
          }
        >
          <Table
            columns={roleColumns}
            dataSource={roles.map((r) => ({ ...r, key: r.id }))}
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <UserOutlined /> 用户与组织管理
      </Title>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Alert
          message="用户与组织管理说明"
          description="管理系统用户、组织架构和角色权限。支持用户增删改查、组织树形管理、角色权限配置。"
          type="info"
          showIcon
        />
        <Tabs items={tabItems} />
      </Space>

      {/* User Modal */}
      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={userModalVisible}
        onCancel={() => setUserModalVisible(false)}
        onOk={handleUserModalOk}
        width={700}
        destroyOnClose
      >
        <Form form={userForm} layout="vertical" preserve={false}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="如：zhang_san" disabled={!!editingUser} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="realName"
                label="真实姓名"
                rules={[{ required: true, message: '请输入真实姓名' }]}
              >
                <Input placeholder="如：张三" />
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
                <Input placeholder="如：zhangsan@example.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="手机号">
                <Input placeholder="如：13800138000" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="department" label="部门">
                <Select options={DEPARTMENT_OPTIONS} placeholder="选择部门" allowClear />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="position" label="职位">
                <Input placeholder="如：数据分析师" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="roles"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select mode="multiple" options={ROLE_OPTIONS} placeholder="选择角色" />
          </Form.Item>

          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select options={USER_STATUS_OPTIONS} />
          </Form.Item>

          {!editingUser && (
            <Alert
              message="默认密码"
              description="新建用户的初始密码为：123456，用户首次登录后需要修改密码。"
              type="info"
              showIcon
            />
          )}
        </Form>
      </Modal>

      {/* Organization Modal */}
      <Modal
        title="新建组织"
        open={orgModalVisible}
        onCancel={() => setOrgModalVisible(false)}
        onOk={handleOrgModalOk}
        destroyOnClose
      >
        <Form form={orgForm} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label="组织名称"
            rules={[{ required: true, message: '请输入组织名称' }]}
          >
            <Input placeholder="如：技术部" />
          </Form.Item>
          <Form.Item
            name="code"
            label="组织编码"
            rules={[{ required: true, message: '请输入组织编码' }]}
          >
            <Input placeholder="如：TECH" />
          </Form.Item>
          <Form.Item name="parentId" label="上级组织">
            <Select placeholder="选择上级组织（可选）" allowClear>
              <Select.Option value="1">总公司</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Role Modal */}
      <Modal
        title={editingRole ? '编辑角色' : '新建角色'}
        open={roleModalVisible}
        onCancel={() => setRoleModalVisible(false)}
        onOk={handleRoleModalOk}
        destroyOnClose
      >
        <Form form={roleForm} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="如：数据分析师" />
          </Form.Item>
          <Form.Item
            name="code"
            label="角色编码"
            rules={[{ required: true, message: '请输入角色编码' }]}
          >
            <Input placeholder="如：analyst" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="角色描述" />
          </Form.Item>
          <Form.Item
            name="permissions"
            label="权限"
            rules={[{ required: true, message: '请输入权限列表' }]}
          >
            <Select
              mode="tags"
              placeholder="输入权限标识，如：data.query"
              options={[
                { label: 'data.query', value: 'data.query' },
                { label: 'data.export', value: 'data.export' },
                { label: 'system.config', value: 'system.config' },
                { label: 'report.view', value: 'report.view' },
                { label: 'report.create', value: 'report.create' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Users;
