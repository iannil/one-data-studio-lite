'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tabs,
  Descriptions,
  Spin,
  Empty,
  Alert,
  List,
  Avatar,
  Result,
  Badge,
  Timeline,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  BulbOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SettingOutlined,
  TeamOutlined,
  FileProtectOutlined,
  SearchOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { permissionsApi, assetsApi, securityApi } from '@/services/api';

const { Title, Text, Paragraph } = Typography;

interface DataAsset {
  id: string;
  name: string;
  access_level: string;
  domain?: string;
  category?: string;
}

interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  role?: string;
}

interface PermissionSuggestion {
  asset_id?: string;
  asset_name?: string;
  user_id?: string;
  user_email?: string;
  access_level?: string;
  permission_rules?: Record<string, unknown>;
  suggested_roles?: Array<{ name: string; level: number; description?: string }>;
  recommendations?: string[];
  roles?: Array<{ name: string; level: number }>;
  max_role_level?: number;
  accessible_assets?: Array<{ id: string; name: string; access_level: string }>;
  restricted_assets?: Array<{ id: string; name: string; reason: string }>;
  upgrade_suggestions?: Array<{ role: string; benefit: string }>;
}

interface AutoConfigureResult {
  user_id: string;
  user_email: string;
  department: string;
  ai_suggestions: {
    recommended_roles: Array<{ name: string; reason: string }>;
    access_grants: Array<{ asset_type: string; access_level: string }>;
    restrictions: string[];
  };
  current_roles: Array<{ name: string; level: number }>;
}

interface PermissionCheckResult {
  allowed: boolean;
  reason: string;
  user_id: string;
  asset_id: string;
  operation?: string;
  required_level?: number;
}

interface AuditEntry {
  id: string;
  actor_id: string;
  target_user_id?: string;
  change_type?: string;
  details: Record<string, unknown>;
  created_at: string;
}

const accessLevelColors: Record<string, string> = {
  public: 'green',
  internal: 'blue',
  restricted: 'orange',
  confidential: 'red',
};

const accessLevelLabels: Record<string, string> = {
  public: '公开',
  internal: '内部',
  restricted: '受限',
  confidential: '机密',
};

export default function PermissionPage() {
  const [assets, setAssets] = useState<DataAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('asset-suggest');
  const [selectedAsset, setSelectedAsset] = useState<DataAsset | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [assetSuggestion, setAssetSuggestion] = useState<PermissionSuggestion | null>(null);
  const [userSuggestion, setUserSuggestion] = useState<PermissionSuggestion | null>(null);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [autoConfigModalOpen, setAutoConfigModalOpen] = useState(false);
  const [autoConfigResult, setAutoConfigResult] = useState<AutoConfigureResult | null>(null);
  const [autoConfigLoading, setAutoConfigLoading] = useState(false);
  const [checkModalOpen, setCheckModalOpen] = useState(false);
  const [checkResult, setCheckResult] = useState<PermissionCheckResult | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);
  const [auditHistory, setAuditHistory] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const [autoConfigForm] = Form.useForm();
  const [checkForm] = Form.useForm();

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const response = await assetsApi.list();
      setAssets(response.data);
    } catch (error) {
      message.error('获取数据资产列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditHistory = async (userId?: string) => {
    setAuditLoading(true);
    try {
      const response = await permissionsApi.getAuditHistory({
        user_id: userId,
        limit: 100,
      });
      setAuditHistory(response.data);
    } catch (error) {
      message.error('获取审计历史失败');
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditHistory();
    }
  }, [activeTab]);

  const handleAssetSuggest = async (asset: DataAsset) => {
    setSelectedAsset(asset);
    setSuggestionLoading(true);
    setAssetSuggestion(null);
    try {
      const response = await permissionsApi.suggestForAsset(asset.id);
      setAssetSuggestion(response.data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '获取权限建议失败');
    } finally {
      setSuggestionLoading(false);
    }
  };

  const handleUserSuggest = async () => {
    if (!selectedUserId) {
      message.warning('请输入用户ID');
      return;
    }
    setSuggestionLoading(true);
    setUserSuggestion(null);
    try {
      const response = await permissionsApi.suggestForUser(selectedUserId);
      setUserSuggestion(response.data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '获取用户权限建议失败');
    } finally {
      setSuggestionLoading(false);
    }
  };

  const handleAutoConfigure = async (values: { user_id: string; department?: string }) => {
    setAutoConfigLoading(true);
    try {
      const response = await permissionsApi.autoConfigure(values);
      setAutoConfigResult(response.data);
      message.success('AI 权限配置建议生成成功');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '生成配置建议失败');
    } finally {
      setAutoConfigLoading(false);
    }
  };

  const handlePermissionCheck = async (values: { user_id: string; asset_id: string; operation?: string }) => {
    setCheckLoading(true);
    try {
      const response = await permissionsApi.check(values);
      setCheckResult(response.data);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '权限检查失败');
    } finally {
      setCheckLoading(false);
    }
  };

  const assetColumns: ColumnsType<DataAsset> = [
    {
      title: '资产名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <FileProtectOutlined />
          <a onClick={() => handleAssetSuggest(record)}>{name}</a>
        </Space>
      ),
    },
    {
      title: '访问级别',
      dataIndex: 'access_level',
      key: 'access_level',
      render: (level) => (
        <Tag color={accessLevelColors[level]}>
          {accessLevelLabels[level] || level}
        </Tag>
      ),
    },
    {
      title: '领域',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Button size="small" icon={<BulbOutlined />} onClick={() => handleAssetSuggest(record)}>
          权限建议
        </Button>
      ),
    },
  ];

  const stats = {
    total: assets.length,
    public: assets.filter((a) => a.access_level === 'public').length,
    internal: assets.filter((a) => a.access_level === 'internal').length,
    restricted: assets.filter((a) => a.access_level === 'restricted').length,
    confidential: assets.filter((a) => a.access_level === 'confidential').length,
  };

  return (
    <AuthGuard>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Row gutter={24}>
            <Col span={5}>
              <Statistic title="总资产数" value={stats.total} prefix={<FileProtectOutlined />} />
            </Col>
            <Col span={5}>
              <Statistic
                title="公开资产"
                value={stats.public}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={5}>
              <Statistic
                title="内部资产"
                value={stats.internal}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={5}>
              <Statistic
                title="受限资产"
                value={stats.restricted}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
            <Col span={4}>
              <Statistic
                title="机密资产"
                value={stats.confidential}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
          </Row>
        </Card>

        <Card>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'asset-suggest',
                label: (
                  <Space>
                    <SafetyCertificateOutlined />
                    资产权限建议
                  </Space>
                ),
                children: (
                  <Row gutter={16}>
                    <Col span={14}>
                      <Table
                        columns={assetColumns}
                        dataSource={assets}
                        rowKey="id"
                        loading={loading}
                        size="small"
                      />
                    </Col>
                    <Col span={10}>
                      <Card title="权限建议" size="small">
                        {suggestionLoading ? (
                          <div style={{ textAlign: 'center', padding: 40 }}>
                            <Spin size="large" />
                          </div>
                        ) : assetSuggestion ? (
                          <div>
                            <Descriptions column={1} size="small" bordered>
                              <Descriptions.Item label="资产名称">
                                {assetSuggestion.asset_name}
                              </Descriptions.Item>
                              <Descriptions.Item label="访问级别">
                                <Tag color={accessLevelColors[assetSuggestion.access_level || '']}>
                                  {accessLevelLabels[assetSuggestion.access_level || ''] || assetSuggestion.access_level}
                                </Tag>
                              </Descriptions.Item>
                            </Descriptions>

                            {assetSuggestion.suggested_roles && assetSuggestion.suggested_roles.length > 0 && (
                              <Card size="small" title="建议角色" style={{ marginTop: 16 }}>
                                <List
                                  size="small"
                                  dataSource={assetSuggestion.suggested_roles}
                                  renderItem={(role) => (
                                    <List.Item>
                                      <List.Item.Meta
                                        avatar={<Avatar icon={<TeamOutlined />} />}
                                        title={role.name}
                                        description={role.description || `权限级别: ${role.level}`}
                                      />
                                    </List.Item>
                                  )}
                                />
                              </Card>
                            )}

                            {assetSuggestion.recommendations && assetSuggestion.recommendations.length > 0 && (
                              <Card size="small" title="安全建议" style={{ marginTop: 16 }}>
                                <List
                                  size="small"
                                  dataSource={assetSuggestion.recommendations}
                                  renderItem={(rec) => (
                                    <List.Item>
                                      <BulbOutlined style={{ marginRight: 8, color: '#faad14' }} />
                                      {rec}
                                    </List.Item>
                                  )}
                                />
                              </Card>
                            )}

                            {assetSuggestion.permission_rules && (
                              <Card size="small" title="权限规则" style={{ marginTop: 16 }}>
                                <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, fontSize: 12 }}>
                                  {JSON.stringify(assetSuggestion.permission_rules, null, 2)}
                                </pre>
                              </Card>
                            )}
                          </div>
                        ) : (
                          <Empty description="选择资产查看权限建议" />
                        )}
                      </Card>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'user-suggest',
                label: (
                  <Space>
                    <UserOutlined />
                    用户权限概览
                  </Space>
                ),
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Card title="查询用户权限" size="small">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Input
                            placeholder="输入用户ID"
                            value={selectedUserId}
                            onChange={(e) => setSelectedUserId(e.target.value)}
                            prefix={<UserOutlined />}
                          />
                          <Button
                            type="primary"
                            icon={<SearchOutlined />}
                            onClick={handleUserSuggest}
                            loading={suggestionLoading}
                            block
                          >
                            查询权限
                          </Button>
                        </Space>
                      </Card>
                    </Col>
                    <Col span={16}>
                      <Card title="用户权限概览" size="small">
                        {suggestionLoading ? (
                          <div style={{ textAlign: 'center', padding: 40 }}>
                            <Spin size="large" />
                          </div>
                        ) : userSuggestion ? (
                          <div>
                            <Descriptions column={2} size="small" bordered>
                              <Descriptions.Item label="用户邮箱">
                                {userSuggestion.user_email}
                              </Descriptions.Item>
                              <Descriptions.Item label="最高权限级别">
                                {userSuggestion.max_role_level || '-'}
                              </Descriptions.Item>
                            </Descriptions>

                            <Row gutter={16} style={{ marginTop: 16 }}>
                              <Col span={12}>
                                {userSuggestion.roles && userSuggestion.roles.length > 0 && (
                                  <Card size="small" title="当前角色">
                                    <List
                                      size="small"
                                      dataSource={userSuggestion.roles}
                                      renderItem={(role) => (
                                        <List.Item>
                                          <Tag color="blue">{role.name}</Tag>
                                          <Text type="secondary">级别: {role.level}</Text>
                                        </List.Item>
                                      )}
                                    />
                                  </Card>
                                )}
                              </Col>
                              <Col span={12}>
                                {userSuggestion.upgrade_suggestions && userSuggestion.upgrade_suggestions.length > 0 && (
                                  <Card size="small" title="升级建议">
                                    <List
                                      size="small"
                                      dataSource={userSuggestion.upgrade_suggestions}
                                      renderItem={(sug) => (
                                        <List.Item>
                                          <List.Item.Meta
                                            title={sug.role}
                                            description={sug.benefit}
                                          />
                                        </List.Item>
                                      )}
                                    />
                                  </Card>
                                )}
                              </Col>
                            </Row>

                            <Row gutter={16} style={{ marginTop: 16 }}>
                              <Col span={12}>
                                {userSuggestion.accessible_assets && userSuggestion.accessible_assets.length > 0 && (
                                  <Card size="small" title="可访问资产">
                                    <List
                                      size="small"
                                      dataSource={userSuggestion.accessible_assets.slice(0, 5)}
                                      renderItem={(asset) => (
                                        <List.Item>
                                          <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                                          {asset.name}
                                          <Tag style={{ marginLeft: 8 }} color={accessLevelColors[asset.access_level]}>
                                            {accessLevelLabels[asset.access_level]}
                                          </Tag>
                                        </List.Item>
                                      )}
                                    />
                                  </Card>
                                )}
                              </Col>
                              <Col span={12}>
                                {userSuggestion.restricted_assets && userSuggestion.restricted_assets.length > 0 && (
                                  <Card size="small" title="受限资产">
                                    <List
                                      size="small"
                                      dataSource={userSuggestion.restricted_assets.slice(0, 5)}
                                      renderItem={(asset) => (
                                        <List.Item>
                                          <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                                          {asset.name}
                                          <Text type="secondary" style={{ marginLeft: 8 }}>
                                            {asset.reason}
                                          </Text>
                                        </List.Item>
                                      )}
                                    />
                                  </Card>
                                )}
                              </Col>
                            </Row>
                          </div>
                        ) : (
                          <Empty description="输入用户ID查看权限概览" />
                        )}
                      </Card>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'auto-config',
                label: (
                  <Space>
                    <SettingOutlined />
                    AI 权限配置
                  </Space>
                ),
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Card title="自动配置权限" size="small">
                        <Form form={autoConfigForm} layout="vertical" onFinish={handleAutoConfigure}>
                          <Form.Item name="user_id" label="用户ID" rules={[{ required: true, message: '请输入用户ID' }]}>
                            <Input placeholder="输入用户ID" prefix={<UserOutlined />} />
                          </Form.Item>
                          <Form.Item name="department" label="部门 (可选)">
                            <Input placeholder="例如：数据分析部" />
                          </Form.Item>
                          <Form.Item>
                            <Button
                              type="primary"
                              htmlType="submit"
                              icon={<BulbOutlined />}
                              loading={autoConfigLoading}
                              block
                            >
                              生成 AI 配置建议
                            </Button>
                          </Form.Item>
                        </Form>
                      </Card>
                    </Col>
                    <Col span={16}>
                      <Card title="AI 配置建议" size="small">
                        {autoConfigLoading ? (
                          <div style={{ textAlign: 'center', padding: 40 }}>
                            <Spin size="large" />
                            <div style={{ marginTop: 16 }}>AI 正在分析用户属性...</div>
                          </div>
                        ) : autoConfigResult ? (
                          <div>
                            <Alert
                              message={`已为用户 ${autoConfigResult.user_email} (${autoConfigResult.department}) 生成权限配置建议`}
                              type="success"
                              style={{ marginBottom: 16 }}
                            />

                            <Row gutter={16}>
                              <Col span={12}>
                                <Card size="small" title="推荐角色">
                                  <List
                                    size="small"
                                    dataSource={autoConfigResult.ai_suggestions.recommended_roles}
                                    renderItem={(role) => (
                                      <List.Item>
                                        <List.Item.Meta
                                          avatar={<Avatar icon={<TeamOutlined />} style={{ backgroundColor: '#1890ff' }} />}
                                          title={role.name}
                                          description={role.reason}
                                        />
                                      </List.Item>
                                    )}
                                  />
                                </Card>
                              </Col>
                              <Col span={12}>
                                <Card size="small" title="访问授权建议">
                                  <List
                                    size="small"
                                    dataSource={autoConfigResult.ai_suggestions.access_grants}
                                    renderItem={(grant) => (
                                      <List.Item>
                                        <Tag>{grant.asset_type}</Tag>
                                        <Tag color={accessLevelColors[grant.access_level]}>
                                          {accessLevelLabels[grant.access_level]}
                                        </Tag>
                                      </List.Item>
                                    )}
                                  />
                                </Card>
                              </Col>
                            </Row>

                            {autoConfigResult.ai_suggestions.restrictions.length > 0 && (
                              <Card size="small" title="访问限制" style={{ marginTop: 16 }}>
                                <List
                                  size="small"
                                  dataSource={autoConfigResult.ai_suggestions.restrictions}
                                  renderItem={(restriction) => (
                                    <List.Item>
                                      <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                                      {restriction}
                                    </List.Item>
                                  )}
                                />
                              </Card>
                            )}

                            <Card size="small" title="当前角色" style={{ marginTop: 16 }}>
                              <Space>
                                {autoConfigResult.current_roles.map((role) => (
                                  <Tag key={role.name} color="blue">{role.name}</Tag>
                                ))}
                                {autoConfigResult.current_roles.length === 0 && (
                                  <Text type="secondary">暂无角色</Text>
                                )}
                              </Space>
                            </Card>
                          </div>
                        ) : (
                          <Empty description="输入用户信息生成 AI 配置建议" />
                        )}
                      </Card>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'check',
                label: (
                  <Space>
                    <LockOutlined />
                    权限检查
                  </Space>
                ),
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Card title="权限检查" size="small">
                        <Form form={checkForm} layout="vertical" onFinish={handlePermissionCheck}>
                          <Form.Item name="user_id" label="用户ID" rules={[{ required: true, message: '请输入用户ID' }]}>
                            <Input placeholder="输入用户ID" prefix={<UserOutlined />} />
                          </Form.Item>
                          <Form.Item name="asset_id" label="资产" rules={[{ required: true, message: '请选择资产' }]}>
                            <Select
                              showSearch
                              placeholder="选择资产"
                              optionFilterProp="children"
                              options={assets.map((a) => ({ value: a.id, label: a.name }))}
                            />
                          </Form.Item>
                          <Form.Item name="operation" label="操作类型" initialValue="read">
                            <Select
                              options={[
                                { value: 'read', label: '读取' },
                                { value: 'export', label: '导出' },
                                { value: 'write', label: '写入' },
                              ]}
                            />
                          </Form.Item>
                          <Form.Item>
                            <Button
                              type="primary"
                              htmlType="submit"
                              icon={<LockOutlined />}
                              loading={checkLoading}
                              block
                            >
                              检查权限
                            </Button>
                          </Form.Item>
                        </Form>
                      </Card>
                    </Col>
                    <Col span={16}>
                      <Card title="检查结果" size="small">
                        {checkLoading ? (
                          <div style={{ textAlign: 'center', padding: 40 }}>
                            <Spin size="large" />
                          </div>
                        ) : checkResult ? (
                          <Result
                            status={checkResult.allowed ? 'success' : 'error'}
                            title={checkResult.allowed ? '权限允许' : '权限拒绝'}
                            subTitle={checkResult.reason}
                            extra={
                              <Descriptions column={1} bordered size="small">
                                <Descriptions.Item label="用户ID">{checkResult.user_id}</Descriptions.Item>
                                <Descriptions.Item label="资产ID">{checkResult.asset_id}</Descriptions.Item>
                                {checkResult.operation && (
                                  <Descriptions.Item label="操作类型">{checkResult.operation}</Descriptions.Item>
                                )}
                                {checkResult.required_level !== undefined && (
                                  <Descriptions.Item label="所需权限级别">{checkResult.required_level}</Descriptions.Item>
                                )}
                              </Descriptions>
                            }
                          />
                        ) : (
                          <Empty description="执行权限检查查看结果" />
                        )}
                      </Card>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'audit',
                label: (
                  <Space>
                    <HistoryOutlined />
                    变更审计
                  </Space>
                ),
                children: (
                  <Card
                    title="权限变更审计历史"
                    extra={
                      <Button icon={<SyncOutlined />} onClick={() => fetchAuditHistory()}>
                        刷新
                      </Button>
                    }
                  >
                    {auditLoading ? (
                      <div style={{ textAlign: 'center', padding: 40 }}>
                        <Spin size="large" />
                      </div>
                    ) : auditHistory.length > 0 ? (
                      <Timeline
                        items={auditHistory.map((entry) => ({
                          color: entry.change_type === 'grant' ? 'green' : entry.change_type === 'revoke' ? 'red' : 'blue',
                          children: (
                            <div>
                              <Space>
                                <Text strong>{entry.change_type || '变更'}</Text>
                                <Text type="secondary">{new Date(entry.created_at).toLocaleString()}</Text>
                              </Space>
                              <div>
                                <Text type="secondary">操作者: {entry.actor_id}</Text>
                                {entry.target_user_id && (
                                  <Text type="secondary" style={{ marginLeft: 16 }}>目标用户: {entry.target_user_id}</Text>
                                )}
                              </div>
                              {Object.keys(entry.details).length > 0 && (
                                <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, fontSize: 12, marginTop: 8 }}>
                                  {JSON.stringify(entry.details, null, 2)}
                                </pre>
                              )}
                            </div>
                          ),
                        }))}
                      />
                    ) : (
                      <Empty description="暂无审计记录" />
                    )}
                  </Card>
                ),
              },
            ]}
          />
        </Card>
      </Space>
    </AuthGuard>
  );
}
