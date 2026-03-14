/**
 * SSO Configuration Page
 *
 * Configure Single Sign-On for enterprise authentication.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Form,
  Input,
  Switch,
  Select,
  Tabs,
  Table,
  Space,
  message,
  Modal,
  Tag,
  Alert,
  Divider,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  GoogleOutlined,
  GithubOutlined,
  MicrosoftOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';

const { TextArea } = Input;
const { Option } = Select;
const { TabPane } = Tabs;
const { Text, Paragraph } = Typography;

interface SSOProvider {
  id: string;
  name: string;
  type: 'oauth2' | 'saml' | 'ldap';
  provider: 'google' | 'github' | 'microsoft' | 'azure_ad' | 'saml' | 'ldap';
  enabled: boolean;
  config?: Record<string, any>;
}

const SSOPage: React.FC = () => {
  const router = useRouter();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<SSOProvider[]>([
    {
      id: 'google',
      name: 'Google',
      type: 'oauth2',
      provider: 'google',
      enabled: false,
    },
    {
      id: 'github',
      name: 'GitHub',
      type: 'oauth2',
      provider: 'github',
      enabled: false,
    },
    {
      id: 'microsoft',
      name: 'Microsoft',
      type: 'oauth2',
      provider: 'microsoft',
      enabled: false,
    },
    {
      id: 'saml',
      name: 'SAML 2.0',
      type: 'saml',
      provider: 'saml',
      enabled: false,
    },
    {
      id: 'ldap',
      name: 'LDAP / Active Directory',
      type: 'ldap',
      provider: 'ldap',
      enabled: false,
    },
  ]);
  const [activeProvider, setActiveProvider] = useState<SSOProvider | null>(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);

  const handleToggleProvider = (providerId: string) => {
    setProviders(providers.map(p =>
      p.id === providerId ? { ...p, enabled: !p.enabled } : p
    ));
    message.success('Provider status updated');
  };

  const handleConfigure = (provider: SSOProvider) => {
    setActiveProvider(provider);
    setConfigModalOpen(true);

    // Set form values based on provider
    if (provider.type === 'oauth2') {
      form.setFieldsValue({
        client_id: provider.config?.client_id || '',
        client_secret: '',
        redirect_uri: `${window.location.origin}/api/v1/auth/sso/callback/${provider.provider}`,
      });
    } else if (provider.type === 'ldap') {
      form.setFieldsValue({
        server: provider.config?.server || '',
        port: provider.config?.port || 389,
        bind_dn: provider.config?.bind_dn || '',
        base_dn: provider.config?.base_dn || '',
      });
    }
  };

  const handleSaveConfig = async () => {
    const values = form.getFieldsValue();

    // In production, save to backend
    setProviders(providers.map(p => {
      if (p.id === activeProvider?.id) {
        return {
          ...p,
          config: { ...p.config, ...values },
        };
      }
      return p;
    }));

    message.success('Configuration saved');
    setConfigModalOpen(false);
  };

  const getProviderIcon = (provider: SSOProvider) => {
    switch (provider.provider) {
      case 'google':
        return <GoogleOutlined style={{ fontSize: 24, color: '#4285f4' }} />;
      case 'github':
        return <GithubOutlined style={{ fontSize: 24, color: '#333' }} />;
      case 'microsoft':
        return <MicrosoftOutlined style={{ fontSize: 24, color: '#00a4ef' }} />;
      case 'saml':
      case 'ldap':
        return <ExclamationCircleOutlined style={{ fontSize: 24, color: '#666' }} />;
      default:
        return null;
    }
  };

  const columns = [
    {
      title: 'Provider',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: SSOProvider) => (
        <Space>
          {getProviderIcon(record)}
          <span>{name}</span>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'default'}>
          {enabled ? 'Enabled' : 'Disabled'}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: SSOProvider) => (
        <Space>
          <Switch
            checked={record.enabled}
            onChange={() => handleToggleProvider(record.id)}
            checkedChildren="ON"
            unCheckedChildren="OFF"
          />
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleConfigure(record)}
          >
            Configure
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>Single Sign-On (SSO)</h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            Configure enterprise authentication providers
          </p>
        </Col>
      </Row>

      <Alert
        message="SSO Configuration"
        description="Configure SSO providers to allow users to authenticate using their existing enterprise credentials. Supports OAuth 2.0, SAML 2.0, and LDAP."
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Card title="Authentication Providers">
        <Table
          dataSource={providers}
          columns={columns}
          rowKey="id"
          pagination={false}
        />
      </Card>

      {/* Configuration Modal */}
      <Modal
        title={`Configure ${activeProvider?.name}`}
        open={configModalOpen}
        onOk={handleSaveConfig}
        onCancel={() => setConfigModalOpen(false)}
        width={600}
      >
        <Tabs defaultActiveKey="general">
          <TabPane tab="General" key="general">
            <Form form={form} layout="vertical">
              {activeProvider?.type === 'oauth2' && (
                <>
                  <Form.Item
                    name="client_id"
                    label="Client ID"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="Enter OAuth2 Client ID" />
                  </Form.Item>
                  <Form.Item
                    name="client_secret"
                    label="Client Secret"
                    rules={[{ required: true }]}
                  >
                    <Input.Password placeholder="Enter OAuth2 Client Secret" />
                  </Form.Item>
                  <Form.Item
                    name="redirect_uri"
                    label="Redirect URI"
                  >
                    <Input disabled />
                  </Form.Item>
                  <Paragraph style={{ fontSize: 12, color: '#999' }}>
                    Add this redirect URI to your OAuth app configuration.
                  </Paragraph>
                </>
              )}

              {activeProvider?.type === 'ldap' && (
                <>
                  <Form.Item
                    name="server"
                    label="LDAP Server"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="ldap.example.com" />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="port"
                        label="Port"
                        initialValue={389}
                      >
                        <Input type="number" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="use_ssl"
                        label="Use SSL"
                        valuePropName="checked"
                      >
                        <Switch />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item
                    name="bind_dn"
                    label="Bind DN"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="cn=admin,dc=example,dc=com" />
                  </Form.Item>
                  <Form.Item
                    name="bind_password"
                    label="Bind Password"
                    rules={[{ required: true }]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Form.Item
                    name="base_dn"
                    label="Base DN"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="dc=example,dc=com" />
                  </Form.Item>
                  <Form.Item
                    name="user_filter"
                    label="User Search Filter"
                    initialValue="(uid={username})"
                  >
                    <Input />
                  </Form.Item>
                </>
              )}

              {activeProvider?.type === 'saml' && (
                <>
                  <Form.Item
                    name="idp_metadata_url"
                    label="IdP Metadata URL"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="https://idp.example.com/metadata" />
                  </Form.Item>
                  <Form.Item
                    name="idp_sso_url"
                    label="IdP SSO URL"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="https://idp.example.com/sso" />
                  </Form.Item>
                  <Form.Item
                    name="idp_certificate"
                    label="IdP Certificate"
                    rules={[{ required: true }]}
                  >
                    <TextArea rows={4} placeholder="-----BEGIN CERTIFICATE-----" />
                  </Form.Item>
                </>
              )}
            </Form>
          </TabPane>

          <TabPane tab="Advanced" key="advanced">
            <Form layout="vertical">
              <Form.Item
                name="auto_create_users"
                label="Auto-create Users"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
              <Paragraph style={{ fontSize: 12, color: '#999' }}>
                Automatically create user accounts on first SSO login.
              </Paragraph>

              <Form.Item
                name="default_role"
                label="Default Role"
                initialValue="member"
              >
                <Select>
                  <Option value="viewer">Viewer</Option>
                  <Option value="member">Member</Option>
                  <Option value="admin">Admin</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="domain_restriction"
                label="Domain Restriction"
              >
                <Input placeholder="example.com" />
              </Form.Item>
              <Paragraph style={{ fontSize: 12, color: '#999' }}>
                Only allow users from specific email domains (optional).
              </Paragraph>
            </Form>
          </TabPane>
        </Tabs>
      </Modal>
    </div>
  );
};

export default SSOPage;
