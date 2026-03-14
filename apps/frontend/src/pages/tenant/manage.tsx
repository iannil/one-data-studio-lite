/**
 * Tenant Management Page
 *
 * Multi-tenant administration, quota management, and user administration.
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Tabs,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tooltip,
  message,
  Progress,
  Badge,
  Descriptions,
  Switch,
  Popconfirm,
  Alert,
} from 'antd';
import {
  ReloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserAddOutlined,
  KeyOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  StopOutlined,
  PlayCircleOutlined,
  CrownOutlined,
  TeamOutlined,
  InboxOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { TabsProps, FormInstance } from 'antd';
import { useTenantStore, selectActiveTenants } from '../../stores/tenant';
import {
  Tenant,
  TenantStatus,
  TenantTier,
  TenantUserRole,
  QuotaSummary,
  TIER_COLORS,
  TIER_ICONS,
  TIER_LABELS,
  STATUS_COLORS,
  STATUS_LABELS,
  ROLE_COLORS,
  ROLE_LABELS,
  TIER_FEATURES,
  RESOURCE_TYPE_LABELS,
  QUOTA_WARNING_THRESHOLD,
  QUOTA_CRITICAL_THRESHOLD,
} from '../../types/tenant';

const TenantManagePage: React.FC = () => {
  const tenantStore = useTenantStore();

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [quotaSummary, setQuotaSummary] = useState<QuotaSummary | null>(null);

  // Modals
  const [createTenantModalOpen, setCreateTenantModalOpen] = useState(false);
  const [editTenantModalOpen, setEditTenantModalOpen] = useState(false);
  const [tierModalOpen, setTierModalOpen] = useState(false);
  const [inviteUserModalOpen, setInviteUserModalOpen] = useState(false);
  const [createKeyModalOpen, setCreateKeyModalOpen] = useState(false);

  // Forms
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [tierForm] = Form.useForm();
  const [inviteForm] = Form.useForm();
  const [keyForm] = Form.useForm();

  // Initial data fetch
  useEffect(() => {
    fetchAllTenants();
  }, []);

  // Fetch quota summary when tenant selected
  useEffect(() => {
    if (selectedTenant) {
      tenantStore.setCurrentTenant(selectedTenant.id);
      fetchQuotaSummary(selectedTenant.id);
    }
  }, [selectedTenant]);

  const fetchAllTenants = async () => {
    setLoading(true);
    try {
      await tenantStore.fetchTenants();
    } catch (error) {
      console.error('Failed to fetch tenants:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchQuotaSummary = async (tenantId: number) => {
    try {
      const summary = await tenantStore.fetchQuotaSummary(tenantId);
      setQuotaSummary(summary);
    } catch (error) {
      console.error('Failed to fetch quota summary:', error);
    }
  };

  const handleCreateTenant = async () => {
    try {
      const values = await createForm.validateFields();
      await tenantStore.createTenant({
        name: values.name,
        slug: values.slug,
        contact_email: values.contact_email,
        contact_name: values.contact_name,
        description: values.description,
        tier: values.tier,
      });
      message.success('Tenant created successfully');
      setCreateTenantModalOpen(false);
      createForm.resetFields();
      await fetchAllTenants();
    } catch (error: any) {
      message.error(`Failed to create tenant: ${error.message || error}`);
    }
  };

  const handleUpdateTenant = async () => {
    try {
      const values = await editForm.validateFields();
      if (selectedTenant) {
        await tenantStore.updateTenant(selectedTenant.id, {
          name: values.name,
          description: values.description,
          contact_email: values.contact_email,
          contact_name: values.contact_name,
          contact_phone: values.contact_phone,
        });
        message.success('Tenant updated successfully');
        setEditTenantModalOpen(false);
        await fetchAllTenants();
      }
    } catch (error: any) {
      message.error(`Failed to update tenant: ${error.message || error}`);
    }
  };

  const handleChangeTier = async () => {
    try {
      const values = await tierForm.validateFields();
      if (selectedTenant) {
        await tenantStore.changeTier(selectedTenant.id, values.tier);
        message.success(`Tier changed to ${values.tier}`);
        setTierModalOpen(false);
        await fetchAllTenants();
        if (selectedTenant) {
          await fetchQuotaSummary(selectedTenant.id);
        }
      }
    } catch (error: any) {
      message.error(`Failed to change tier: ${error.message || error}`);
    }
  };

  const handleSuspendTenant = async () => {
    if (selectedTenant) {
      try {
        await tenantStore.suspendTenant(selectedTenant.id, 'Suspended by admin');
        message.success('Tenant suspended');
        await fetchAllTenants();
      } catch (error: any) {
        message.error(`Failed to suspend tenant: ${error.message || error}`);
      }
    }
  };

  const handleActivateTenant = async () => {
    if (selectedTenant) {
      try {
        await tenantStore.activateTenant(selectedTenant.id);
        message.success('Tenant activated');
        await fetchAllTenants();
      } catch (error: any) {
        message.error(`Failed to activate tenant: ${error.message || error}`);
      }
    }
  };

  const handleInviteUser = async () => {
    try {
      const values = await inviteForm.validateFields();
      if (selectedTenant) {
        await tenantStore.inviteUser(selectedTenant.id, {
          email: values.email,
          role: values.role,
        });
        message.success('Invitation sent');
        setInviteUserModalOpen(false);
        inviteForm.resetFields();
      }
    } catch (error: any) {
      message.error(`Failed to send invitation: ${error.message || error}`);
    }
  };

  const handleCreateAPIKey = async () => {
    try {
      const values = await keyForm.validateFields();
      if (selectedTenant) {
        const result = await tenantStore.createAPIKey(selectedTenant.id, {
          name: values.name,
          scopes: values.scopes,
          expires_in_days: values.expires_in_days,
        });
        message.success(
          <div>
            <div>API key created successfully</div>
            <div className="mt-2 p-2 bg-gray-100 rounded text-sm font-mono">
              {result.key} (save this key, it won't be shown again)
            </div>
          </div>
        );
        setCreateKeyModalOpen(false);
        keyForm.resetFields();
      }
    } catch (error: any) {
      message.error(`Failed to create API key: ${error.message || error}`);
    }
  };

  // Tenant columns
  const tenantColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Tenant) => (
        <Space>
          <span
            style={{ color: TIER_COLORS[record.tier] }}
            className="text-lg"
          >
            {TIER_ICONS[record.tier]}
          </span>
          <a onClick={() => setSelectedTenant(record)}>{name}</a>
        </Space>
      ),
    },
    {
      title: 'Slug',
      dataIndex: 'slug',
      key: 'slug',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: TenantStatus) => (
        <Tag color={STATUS_COLORS[status]} icon={<CheckCircleOutlined />}>
          {STATUS_LABELS[status]}
        </Tag>
      ),
    },
    {
      title: 'Tier',
      dataIndex: 'tier',
      key: 'tier',
      render: (tier: TenantTier) => (
        <Tag color={TIER_COLORS[tier]}>{TIER_LABELS[tier]}</Tag>
      ),
    },
    {
      title: 'Users',
      key: 'users',
      render: (_: any, record: Tenant) => (
        <Tag icon={<TeamOutlined />}>{record.slug}</Tag>
      ),
    },
    {
      title: 'Trial',
      dataIndex: 'is_trial',
      key: 'trial',
      render: (isTrial: boolean) =>
        isTrial ? <Tag color="gold">Trial</Tag> : <Tag>Production</Tag>,
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (ts: string) => new Date(ts).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: Tenant) => (
        <Space>
          {record.status === TenantStatus.ACTIVE ? (
            <Tooltip title="Suspend">
              <Button
                type="text"
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => {
                  setSelectedTenant(record);
                  handleSuspendTenant();
                }}
              />
            </Tooltip>
          ) : (
            <Tooltip title="Activate">
              <Button
                type="text"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => {
                  setSelectedTenant(record);
                  handleActivateTenant();
                }}
              />
            </Tooltip>
          )}
          <Tooltip title="Edit">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedTenant(record);
                editForm.setFieldsValue({
                  name: record.name,
                  description: record.description,
                  contact_email: record.contact_email,
                  contact_name: record.contact_name,
                  contact_phone: record.contact_phone,
                });
                setEditTenantModalOpen(true);
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Get quota bar color
  const getQuotaColor = (percent: number) => {
    if (percent >= QUOTA_CRITICAL_THRESHOLD) return 'error';
    if (percent >= QUOTA_WARNING_THRESHOLD) return 'warning';
    return 'success';
  };

  const tabItems: TabsProps['items'] = [
    {
      key: 'overview',
      label: (
        <span>
          <TeamOutlined />
          Overview
        </span>
      ),
      children: (
        <div>
          {/* Statistics */}
          <Row gutter={16} className="mb-6">
            <Col span={6}>
              <Card>
                <Statistic
                  title="Total Tenants"
                  value={tenantStore.tenants.length}
                  prefix={<TeamOutlined />}
                  suffix={
                    <span className="text-sm text-gray-500">
                      {selectActiveTenants(tenantStore).length} active
                    </span>
                  }
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Trial Tenants"
                  value={tenantStore.tenants.filter((t) => t.is_trial).length}
                  prefix={<InboxOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Suspended"
                  value={tenantStore.tenants.filter((t) => t.status === TenantStatus.SUSPENDED).length}
                  prefix={<WarningOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Enterprise"
                  value={tenantStore.tenants.filter((t) => t.tier === TenantTier.ENTERPRISE).length}
                  prefix={<CrownOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Tenant Table */}
          <Card
            title="All Tenants"
            extra={
              <Space>
                <Button icon={<PlusOutlined />} onClick={() => setCreateTenantModalOpen(true)}>
                  Create Tenant
                </Button>
                <Button icon={<ReloadOutlined />} onClick={fetchAllTenants} loading={loading}>
                  Refresh
                </Button>
              </Space>
            }
          >
            <Table
              columns={tenantColumns}
              dataSource={tenantStore.tenants}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'selected',
      label: (
        <span>
          <SettingOutlined />
          {selectedTenant ? selectedTenant.name : 'Select Tenant'}
        </span>
      ),
      disabled: !selectedTenant,
      children: selectedTenant ? (
        <div>
          {/* Tenant Info */}
          <Card className="mb-4" title="Tenant Information">
            <Descriptions column={3} size="small">
              <Descriptions.Item label="Name">{selectedTenant.name}</Descriptions.Item>
              <Descriptions.Item label="Slug">{selectedTenant.slug}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_COLORS[selectedTenant.status]}>
                  {STATUS_LABELS[selectedTenant.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Tier">
                <Tag color={TIER_COLORS[selectedTenant.tier]}>
                  {TIER_ICONS[selectedTenant.tier]} {TIER_LABELS[selectedTenant.tier]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Contact Email">{selectedTenant.contact_email}</Descriptions.Item>
              <Descriptions.Item label="Trial">
                {selectedTenant.is_trial ? (
                  <Tag color="gold">Trial (ends {new Date(selectedTenant.trial_ends_at || '').toLocaleDateString()})</Tag>
                ) : (
                  <Tag>Production</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
            <div className="mt-4 flex gap-2">
              <Button icon={<EditOutlined />} onClick={() => setEditTenantModalOpen(true)}>
                Edit
              </Button>
              <Button icon={<CrownOutlined />} onClick={() => setTierModalOpen(true)}>
                Change Tier
              </Button>
              {selectedTenant.status === TenantStatus.ACTIVE ? (
                <Button danger icon={<StopOutlined />} onClick={handleSuspendTenant}>
                  Suspend
                </Button>
              ) : (
                <Button icon={<PlayCircleOutlined />} onClick={handleActivateTenant}>
                  Activate
                </Button>
              )}
            </div>
          </Card>

          {/* Quota Summary */}
          {quotaSummary && (
            <Card title="Resource Quota" className="mb-4">
              <Row gutter={16}>
                <Col span={8}>
                  <Card size="small" title="Compute Resources" className="mb-2">
                    <Space direction="vertical" className="w-full">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>CPU Cores</span>
                          <span>{quotaSummary.cpu_cores.current} / {quotaSummary.cpu_cores.limit === -1 ? 'Unlimited' : quotaSummary.cpu_cores.limit}</span>
                        </div>
                        {quotaSummary.cpu_cores.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.cpu_cores.percent}
                            status={getQuotaColor(quotaSummary.cpu_cores.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Memory (GB)</span>
                          <span>{quotaSummary.memory_gb.current} / {quotaSummary.memory_gb.limit === -1 ? 'Unlimited' : quotaSummary.memory_gb.limit}</span>
                        </div>
                        {quotaSummary.memory_gb.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.memory_gb.percent}
                            status={getQuotaColor(quotaSummary.memory_gb.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>GPUs</span>
                          <span>{quotaSummary.gpu_count.current} / {quotaSummary.gpu_count.limit === -1 ? 'Unlimited' : quotaSummary.gpu_count.limit}</span>
                        </div>
                        {quotaSummary.gpu_count.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.gpu_count.percent}
                            status={getQuotaColor(quotaSummary.gpu_count.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                    </Space>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" title="Services" className="mb-2">
                    <Space direction="vertical" className="w-full">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Notebooks</span>
                          <span>{quotaSummary.notebooks.current} / {quotaSummary.notebooks.limit === -1 ? 'Unlimited' : quotaSummary.notebooks.limit}</span>
                        </div>
                        {quotaSummary.notebooks.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.notebooks.percent}
                            status={getQuotaColor(quotaSummary.notebooks.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Training Jobs</span>
                          <span>{quotaSummary.training_jobs.current} / {quotaSummary.training_jobs.limit === -1 ? 'Unlimited' : quotaSummary.training_jobs.limit}</span>
                        </div>
                        {quotaSummary.training_jobs.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.training_jobs.percent}
                            status={getQuotaColor(quotaSummary.training_jobs.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Inference Services</span>
                          <span>{quotaSummary.inference_services.current} / {quotaSummary.inference_services.limit === -1 ? 'Unlimited' : quotaSummary.inference_services.limit}</span>
                        </div>
                        {quotaSummary.inference_services.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.inference_services.percent}
                            status={getQuotaColor(quotaSummary.inference_services.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                    </Space>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" title="Data & Storage" className="mb-2">
                    <Space direction="vertical" className="w-full">
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Storage (GB)</span>
                          <span>{quotaSummary.storage_gb.current} / {quotaSummary.storage_gb.limit === -1 ? 'Unlimited' : quotaSummary.storage_gb.limit}</span>
                        </div>
                        {quotaSummary.storage_gb.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.storage_gb.percent}
                            status={getQuotaColor(quotaSummary.storage_gb.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Data Sources</span>
                          <span>{quotaSummary.data_sources.current} / {quotaSummary.data_sources.limit === -1 ? 'Unlimited' : quotaSummary.data_sources.limit}</span>
                        </div>
                        {quotaSummary.data_sources.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.data_sources.percent}
                            status={getQuotaColor(quotaSummary.data_sources.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span>Users</span>
                          <span>{quotaSummary.users.current} / {quotaSummary.users.limit === -1 ? 'Unlimited' : quotaSummary.users.limit}</span>
                        </div>
                        {quotaSummary.users.limit !== -1 && (
                          <Progress
                            percent={quotaSummary.users.percent}
                            status={getQuotaColor(quotaSummary.users.percent) as any}
                            size="small"
                          />
                        )}
                      </div>
                    </Space>
                  </Card>
                </Col>
              </Row>
            </Card>
          )}

          {/* Action Buttons */}
          <Card title="Actions">
            <Space wrap>
              <Button icon={<UserAddOutlined />} onClick={() => setInviteUserModalOpen(true)}>
                Invite User
              </Button>
              <Button icon={<KeyOutlined />} onClick={() => setCreateKeyModalOpen(true)}>
                Create API Key
              </Button>
              <Button icon={<AuditOutlined />}>
                View Audit Logs
              </Button>
            </Space>
          </Card>
        </div>
      ) : (
        <Card>
          <div className="text-center py-8 text-gray-500">
            Select a tenant from the Overview tab to view details
          </div>
        </Card>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Multi-Tenant Management</h1>
        <p className="text-gray-500">Manage tenants, quotas, and user access</p>
      </div>

      <Tabs activeKey={activeTab} items={tabItems} onChange={setActiveTab} />

      {/* Create Tenant Modal */}
      <Modal
        title="Create New Tenant"
        open={createTenantModalOpen}
        onOk={handleCreateTenant}
        onCancel={() => {
          setCreateTenantModalOpen(false);
          createForm.resetFields();
        }}
        width={600}
      >
        <Form form={createForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Tenant Name" rules={[{ required: true }]}>
                <Input placeholder="Acme Corp" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="slug" label="Slug" rules={[{ required: true, pattern: /^[a-z0-9-]+$/ }]}>
                <Input placeholder="acme-corp" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="contact_email" label="Contact Email" rules={[{ required: true, type: 'email' }]}>
            <Input placeholder="admin@example.com" />
          </Form.Item>
          <Form.Item name="contact_name" label="Contact Name">
            <Input placeholder="John Doe" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Tenant description..." />
          </Form.Item>
          <Form.Item name="tier" label="Initial Tier" initialValue={TenantTier.BASIC}>
            <Select>
              <Select.Option value={TenantTier.BASIC}>
                {TIER_ICONS[TenantTier.BASIC]} Basic
              </Select.Option>
              <Select.Option value={TenantTier.STANDARD}>
                {TIER_ICONS[TenantTier.STANDARD]} Standard
              </Select.Option>
              <Select.Option value={TenantTier.PREMIUM}>
                {TIER_ICONS[TenantTier.PREMIUM]} Premium
              </Select.Option>
              <Select.Option value={TenantTier.ENTERPRISE}>
                {TIER_ICONS[TenantTier.ENTERPRISE]} Enterprise
              </Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Tenant Modal */}
      <Modal
        title="Edit Tenant"
        open={editTenantModalOpen}
        onOk={handleUpdateTenant}
        onCancel={() => setEditTenantModalOpen(false)}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="name" label="Tenant Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="contact_email" label="Contact Email" rules={[{ type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label="Contact Name">
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label="Contact Phone">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      {/* Change Tier Modal */}
      <Modal
        title="Change Tenant Tier"
        open={tierModalOpen}
        onOk={handleChangeTier}
        onCancel={() => setTierModalOpen(false)}
      >
        <Form form={tierForm} layout="vertical">
          <Form.Item name="tier" label="New Tier" rules={[{ required: true }]}>
            <Select>
              <Select.Option value={TenantTier.BASIC}>
                {TIER_ICONS[TenantTier.BASIC]} Basic - {TIER_FEATURES[TenantTier.BASIC].slice(0, 3).join(', ')}
              </Select.Option>
              <Select.Option value={TenantTier.STANDARD}>
                {TIER_ICONS[TenantTier.STANDARD]} Standard - {TIER_FEATURES[TenantTier.STANDARD].slice(0, 3).join(', ')}
              </Select.Option>
              <Select.Option value={TenantTier.PREMIUM}>
                {TIER_ICONS[TenantTier.PREMIUM]} Premium - {TIER_FEATURES[TenantTier.PREMIUM].slice(0, 3).join(', ')}
              </Select.Option>
              <Select.Option value={TenantTier.ENTERPRISE}>
                {TIER_ICONS[TenantTier.ENTERPRISE]} Enterprise - {TIER_FEATURES[TenantTier.ENTERPRISE].slice(0, 3).join(', ')}
              </Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Invite User Modal */}
      <Modal
        title="Invite User to Tenant"
        open={inviteUserModalOpen}
        onOk={handleInviteUser}
        onCancel={() => {
          setInviteUserModalOpen(false);
          inviteForm.resetFields();
        }}
      >
        <Form form={inviteForm} layout="vertical">
          <Form.Item name="email" label="Email Address" rules={[{ required: true, type: 'email' }]}>
            <Input placeholder="user@example.com" />
          </Form.Item>
          <Form.Item name="role" label="Role" rules={[{ required: true }]} initialValue={TenantUserRole.MEMBER}>
            <Select>
              <Select.Option value={TenantUserRole.OWNER}>Owner</Select.Option>
              <Select.Option value={TenantUserRole.ADMIN}>Admin</Select.Option>
              <Select.Option value={TenantUserRole.MEMBER}>Member</Select.Option>
              <Select.Option value={TenantUserRole.VIEWER}>Viewer</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Create API Key Modal */}
      <Modal
        title="Create API Key"
        open={createKeyModalOpen}
        onOk={handleCreateAPIKey}
        onCancel={() => {
          setCreateKeyModalOpen(false);
          keyForm.resetFields();
        }}
      >
        <Form form={keyForm} layout="vertical">
          <Form.Item name="name" label="Key Name" rules={[{ required: true }]}>
            <Input placeholder="Production Key" />
          </Form.Item>
          <Form.Item name="expires_in_days" label="Expiration (Days)">
            <Input type="number" placeholder="Leave empty for no expiration" />
          </Form.Item>
        </Form>
        <Alert
          message="Important"
          description="The API key will only be shown once after creation. Save it securely."
          type="warning"
          showIcon
          className="mt-4"
        />
      </Modal>
    </div>
  );
};

export default TenantManagePage;
