'use client';

import React, { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Space,
  theme,
} from 'antd';
import {
  DatabaseOutlined,
  CloudDownloadOutlined,
  ApiOutlined,
  LineChartOutlined,
  FolderOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TableOutlined,
  BarChartOutlined,
  FileProtectOutlined,
  CloudServerOutlined,
  LockOutlined,
  SettingOutlined,
  AppstoreOutlined,
  ToolOutlined,
  ScanOutlined,
  DashboardOutlined,
  ApartmentOutlined,
  FileTextOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useAuthStore } from '@/stores/auth';

const { Header, Sider, Content } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
}

const menuItems: MenuProps['items'] = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: 'data-management',
    icon: <AppstoreOutlined />,
    label: '数据管理',
    children: [
      {
        key: '/sources',
        icon: <DatabaseOutlined />,
        label: '数据源管理',
      },
      {
        key: '/metadata',
        icon: <TableOutlined />,
        label: '元数据浏览',
      },
      {
        key: '/collect',
        icon: <CloudDownloadOutlined />,
        label: '数据采集',
      },
      {
        key: '/standard',
        icon: <FileProtectOutlined />,
        label: '数据标准',
      },
      {
        key: '/quality',
        icon: <ExperimentOutlined />,
        label: '数据质量',
      },
      {
        key: '/lineage',
        icon: <ApartmentOutlined />,
        label: '数据血缘',
      },
    ],
  },
  {
    key: 'data-processing',
    icon: <ToolOutlined />,
    label: '数据加工',
    children: [
      {
        key: '/etl',
        icon: <ApiOutlined />,
        label: 'ETL管道',
      },
      {
        key: '/analysis',
        icon: <LineChartOutlined />,
        label: '数据分析',
      },
      {
        key: '/ocr',
        icon: <ScanOutlined />,
        label: 'OCR文档识别',
      },
    ],
  },
  {
    key: 'data-service',
    icon: <CloudServerOutlined />,
    label: '数据服务',
    children: [
      {
        key: '/assets',
        icon: <FolderOutlined />,
        label: '数据资产',
      },
      {
        key: '/data-service',
        icon: <CloudServerOutlined />,
        label: '数据服务',
      },
      {
        key: '/bi',
        icon: <BarChartOutlined />,
        label: 'BI 集成',
      },
      {
        key: '/reports',
        icon: <FileTextOutlined />,
        label: '报表设计',
      },
    ],
  },
  {
    key: 'system-management',
    icon: <SettingOutlined />,
    label: '系统管理',
    children: [
      {
        key: '/security',
        icon: <SafetyCertificateOutlined />,
        label: '安全管理',
      },
      {
        key: '/permission',
        icon: <LockOutlined />,
        label: '权限管理',
      },
    ],
  },
];

export default function MainLayout({ children }: MainLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { token } = theme.useToken();

  const getOpenKeys = (path: string): string[] => {
    if (['/sources', '/metadata', '/collect', '/standard', '/quality', '/lineage'].includes(path)) {
      return ['data-management'];
    }
    if (['/etl', '/analysis', '/ocr'].includes(path)) {
      return ['data-processing'];
    }
    if (['/assets', '/data-service', '/bi', '/reports'].includes(path)) {
      return ['data-service'];
    }
    if (['/security', '/permission'].includes(path)) {
      return ['system-management'];
    }
    return [];
  };

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    router.push(key);
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        logout();
        router.push('/login');
      },
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        style={{
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <span style={{ fontSize: collapsed ? 16 : 20, fontWeight: 'bold' }}>
            {collapsed ? 'SDP' : '智能数据平台'}
          </span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[pathname]}
          defaultOpenKeys={getOpenKeys(pathname)}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ border: 'none' }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <div
            onClick={() => setCollapsed(!collapsed)}
            style={{ cursor: 'pointer', fontSize: 18 }}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <span>{user?.full_name || user?.email}</span>
            </Space>
          </Dropdown>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
            minHeight: 'calc(100vh - 64px - 48px)',
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
