import React, { useState } from 'react';
import { Layout, Menu, Dropdown, Avatar, Space } from 'antd';
import {
  UserOutlined,
  LogoutOutlined,
  HomeOutlined,
  DatabaseOutlined,
  CloudDownloadOutlined,
  ToolOutlined,
  BarChartOutlined,
  GoldOutlined,
  SafetyOutlined,
  NodeIndexOutlined,
  TagsOutlined,
  SyncOutlined,
  ScheduleOutlined,
  MonitorOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  ClearOutlined,
  SettingOutlined,
  DashboardOutlined,
  LineChartOutlined,
  SearchOutlined,
  RobotOutlined,
  BookOutlined,
  ApiOutlined,
  SwapOutlined,
  EyeOutlined,
  LockOutlined,
  AuditOutlined,
  BellOutlined,
  FileTextOutlined,
  TeamOutlined,
  AppstoreOutlined,
  DesktopOutlined,
  AlertOutlined,
  ClusterOutlined,
  IdcardOutlined,
  NotificationOutlined,
  DollarOutlined,
  ContainerOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

const { Header, Sider, Content } = Layout;

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const menuItems = [
    {
      key: 'dashboard',
      icon: <HomeOutlined />,
      label: '工作台',
      children: [
        { key: '/dashboard/workspace', icon: <DesktopOutlined />, label: '个人工作台' },
        { key: '/dashboard/notifications', icon: <BellOutlined />, label: '消息通知中心' },
        { key: '/dashboard/profile', icon: <UserOutlined />, label: '个人中心' },
        { key: '/dashboard/cockpit', icon: <DashboardOutlined />, label: 'BI 驾驶舱' },
      ],
    },
    {
      key: 'planning',
      icon: <DatabaseOutlined />,
      label: '数据规划',
      children: [
        { key: '/planning/datasources', icon: <DatabaseOutlined />, label: '数据源管理' },
        { key: '/planning/metadata', icon: <NodeIndexOutlined />, label: '元数据管理' },
        { key: '/planning/tags', icon: <TagsOutlined />, label: '数据标签管理' },
        { key: '/planning/standards', icon: <FileTextOutlined />, label: '数据标准管理' },
        { key: '/planning/lineage', icon: <BranchesOutlined />, label: '数据血缘' },
      ],
    },
    {
      key: 'collection',
      icon: <CloudDownloadOutlined />,
      label: '数据汇聚',
      children: [
        { key: '/collection/sync-jobs', icon: <SyncOutlined />, label: '数据同步任务' },
        { key: '/collection/schedules', icon: <ScheduleOutlined />, label: '任务调度管理' },
        { key: '/collection/task-monitor', icon: <MonitorOutlined />, label: '任务监控日志' },
        { key: '/collection/etl-flows', icon: <BranchesOutlined />, label: 'ETL 流程管理' },
      ],
    },
    {
      key: 'development',
      icon: <ToolOutlined />,
      label: '数据开发',
      children: [
        { key: '/development/cleaning', icon: <ClearOutlined />, label: '清洗规则配置' },
        { key: '/development/field-mapping', icon: <SwapOutlined />, label: '字段映射管理' },
        { key: '/development/ocr', icon: <FileTextOutlined />, label: 'OCR 文档处理' },
        { key: '/development/fusion', icon: <ClusterOutlined />, label: '数据融合配置' },
        { key: '/development/fill-missing', icon: <SettingOutlined />, label: '缺失值填充' },
        { key: '/development/quality', icon: <CheckCircleOutlined />, label: '数据质量检测' },
        { key: '/development/transform', icon: <SettingOutlined />, label: '数据转换配置' },
      ],
    },
    {
      key: 'analysis',
      icon: <BarChartOutlined />,
      label: '数据分析',
      children: [
        { key: '/analysis/bi', icon: <DashboardOutlined />, label: '可视化分析 (BI)' },
        { key: '/analysis/alerts', icon: <AlertOutlined />, label: '智能预警配置' },
        { key: '/analysis/etl-link', icon: <SwapOutlined />, label: 'ETL 数据联动' },
        { key: '/analysis/charts', icon: <LineChartOutlined />, label: '图表管理' },
        { key: '/analysis/nl2sql', icon: <SearchOutlined />, label: '自然语言查询' },
        { key: '/analysis/pipelines', icon: <RobotOutlined />, label: 'AI Pipeline' },
      ],
    },
    {
      key: 'assets',
      icon: <GoldOutlined />,
      label: '数据资产',
      children: [
        { key: '/assets/catalog', icon: <BookOutlined />, label: '资产目录' },
        { key: '/assets/search', icon: <SearchOutlined />, label: '资产检索' },
        { key: '/assets/data-api', icon: <ApiOutlined />, label: '数据 API 管理' },
        { key: '/assets/sync', icon: <SwapOutlined />, label: '元数据同步' },
      ],
    },
    {
      key: 'security',
      icon: <SafetyOutlined />,
      label: '安全与权限',
      children: [
        { key: '/security/permissions', icon: <LockOutlined />, label: '数据权限管控' },
        { key: '/security/sso', icon: <IdcardOutlined />, label: '统一身份认证' },
        { key: '/security/sensitive', icon: <EyeOutlined />, label: '敏感数据检测' },
        { key: '/security/mask-rules', icon: <LockOutlined />, label: '数据脱敏规则' },
      ],
    },
    {
      key: 'support',
      icon: <AppstoreOutlined />,
      label: '统一支撑',
      children: [
        { key: '/support/announcements', icon: <NotificationOutlined />, label: '通知公告管理' },
        { key: '/support/invoices', icon: <DollarOutlined />, label: '财务开票信息' },
        { key: '/support/content', icon: <ContainerOutlined />, label: '内容发布管理' },
      ],
    },
    {
      key: 'operations',
      icon: <SettingOutlined />,
      label: '系统运维',
      children: [
        { key: '/operations/users', icon: <TeamOutlined />, label: '用户与组织管理' },
        { key: '/operations/audit', icon: <AuditOutlined />, label: '统一日志审计' },
        { key: '/operations/api-gateway', icon: <ApiOutlined />, label: '接口服务管理' },
        { key: '/operations/monitor', icon: <MonitorOutlined />, label: '系统监控' },
        { key: '/operations/tenants', icon: <TeamOutlined />, label: '租户管理' },
      ],
    },
  ];

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  // 计算当前展开的菜单组
  const getOpenKeys = () => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return ['dashboard'];
    if (path.startsWith('/planning')) return ['planning'];
    if (path.startsWith('/collection')) return ['collection'];
    if (path.startsWith('/development')) return ['development'];
    if (path.startsWith('/analysis')) return ['analysis'];
    if (path.startsWith('/assets')) return ['assets'];
    if (path.startsWith('/security')) return ['security'];
    if (path.startsWith('/support')) return ['support'];
    if (path.startsWith('/operations')) return ['operations'];
    return [];
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="light"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={220}
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.05)',
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <h2 style={{ margin: 0, color: '#1890ff', fontSize: collapsed ? 14 : 16, whiteSpace: 'nowrap' }}>
            {collapsed ? 'ODS' : 'ONE-DATA-STUDIO'}
          </h2>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={getOpenKeys()}
          items={menuItems}
          onClick={({ key }) => {
            if (key.startsWith('/')) navigate(key);
          }}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'margin-left 0.2s' }}>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
        }}>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <span>{user?.display_name || user?.username || '用户'}</span>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{
          margin: 24,
          padding: 24,
          background: '#fff',
          borderRadius: 8,
          minHeight: 'calc(100vh - 64px - 48px)',
        }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
