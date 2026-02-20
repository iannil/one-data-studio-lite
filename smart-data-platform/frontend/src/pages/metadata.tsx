'use client';

import { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Tag,
  Space,
  Typography,
  Select,
  Descriptions,
  Empty,
  Spin,
  message,
  Row,
  Col,
  Input,
  Tooltip,
  Badge,
  Button,
  Modal,
  Checkbox,
} from 'antd';
import {
  TableOutlined,
  KeyOutlined,
  DatabaseOutlined,
  SearchOutlined,
  TagsOutlined,
  PlusOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import AuthGuard from '@/components/AuthGuard';
import { metadataApi, sourcesApi } from '@/services/api';
import type { MetadataTable, MetadataColumn, DataSource } from '@/types';

const { Title, Text } = Typography;
const { Search } = Input;

const COMMON_TAGS = [
  'PII',
  'Sensitive',
  'Financial',
  'Personal',
  'Internal',
  'Public',
  'Deprecated',
  'Core',
  'Analytics',
  'Audit',
];

export default function MetadataPage() {
  const [tables, setTables] = useState<MetadataTable[]>([]);
  const [sources, setSources] = useState<DataSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | undefined>();
  const [selectedTable, setSelectedTable] = useState<MetadataTable | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');

  const [selectedTableIds, setSelectedTableIds] = useState<string[]>([]);
  const [tagModalVisible, setTagModalVisible] = useState(false);
  const [tagModalMode, setTagModalMode] = useState<'add' | 'remove'>('add');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [customTag, setCustomTag] = useState('');
  const [existingTags, setExistingTags] = useState<string[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  const fetchSources = async () => {
    try {
      const response = await sourcesApi.list();
      setSources(response.data);
    } catch (error) {
      message.error('获取数据源列表失败');
    }
  };

  const fetchTables = async (sourceId?: string) => {
    setLoading(true);
    try {
      const response = await metadataApi.listTables(sourceId);
      setTables(response.data);
      setSelectedTable(null);
      setSelectedTableIds([]);
    } catch (error) {
      message.error('获取元数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchExistingTags = async () => {
    try {
      const response = await metadataApi.listAllTags();
      setExistingTags(response.data);
    } catch (error) {
      // Silently fail - existing tags are optional
    }
  };

  useEffect(() => {
    fetchSources();
    fetchTables();
    fetchExistingTags();
  }, []);

  const handleSourceChange = (value: string | undefined) => {
    setSelectedSourceId(value);
    fetchTables(value);
  };

  const handleTableClick = async (table: MetadataTable) => {
    setDetailLoading(true);
    try {
      const response = await metadataApi.getTable(table.id);
      setSelectedTable(response.data);
    } catch (error) {
      message.error('获取表详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const getSourceName = (sourceId: string) => {
    const source = sources.find(s => s.id === sourceId);
    return source?.name || sourceId;
  };

  const filteredTables = tables.filter(table => {
    if (!searchKeyword.trim()) return true;
    const keyword = searchKeyword.toLowerCase();
    return (
      table.table_name.toLowerCase().includes(keyword) ||
      table.schema_name?.toLowerCase().includes(keyword) ||
      table.description?.toLowerCase().includes(keyword)
    );
  });

  const handleBatchTagClick = (mode: 'add' | 'remove') => {
    setTagModalMode(mode);
    setSelectedTags([]);
    setCustomTag('');
    setTagModalVisible(true);
  };

  const handleBatchTagSubmit = async () => {
    const tagsToApply = [...selectedTags];
    if (customTag.trim() && !tagsToApply.includes(customTag.trim())) {
      tagsToApply.push(customTag.trim());
    }

    if (tagsToApply.length === 0) {
      message.warning('请选择或输入至少一个标签');
      return;
    }

    setBatchLoading(true);
    try {
      const payload = {
        table_ids: selectedTableIds,
        tags_to_add: tagModalMode === 'add' ? tagsToApply : [],
        tags_to_remove: tagModalMode === 'remove' ? tagsToApply : [],
      };

      await metadataApi.batchUpdateTags(payload);
      message.success(
        tagModalMode === 'add'
          ? `成功为 ${selectedTableIds.length} 个表添加标签`
          : `成功从 ${selectedTableIds.length} 个表移除标签`
      );

      setTagModalVisible(false);
      setSelectedTableIds([]);
      fetchTables(selectedSourceId);
      fetchExistingTags();
    } catch (error) {
      message.error('批量操作失败');
    } finally {
      setBatchLoading(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedTableIds(filteredTables.map(t => t.id));
    } else {
      setSelectedTableIds([]);
    }
  };

  const handleSelectTable = (tableId: string, checked: boolean) => {
    if (checked) {
      setSelectedTableIds(prev => [...prev, tableId]);
    } else {
      setSelectedTableIds(prev => prev.filter(id => id !== tableId));
    }
  };

  const allTagOptions = Array.from(new Set([...COMMON_TAGS, ...existingTags])).sort();

  const tableColumns: ColumnsType<MetadataTable> = [
    {
      title: (
        <Checkbox
          checked={selectedTableIds.length === filteredTables.length && filteredTables.length > 0}
          indeterminate={selectedTableIds.length > 0 && selectedTableIds.length < filteredTables.length}
          onChange={(e) => handleSelectAll(e.target.checked)}
        />
      ),
      key: 'select',
      width: 40,
      render: (_, record) => (
        <Checkbox
          checked={selectedTableIds.includes(record.id)}
          onChange={(e) => {
            e.stopPropagation();
            handleSelectTable(record.id, e.target.checked);
          }}
          onClick={(e) => e.stopPropagation()}
        />
      ),
    },
    {
      title: '表名',
      dataIndex: 'table_name',
      key: 'table_name',
      width: 180,
      ellipsis: true,
      render: (name, record) => (
        <Space>
          <TableOutlined />
          <Tooltip title={record.description || record.ai_description}>
            <a onClick={() => handleTableClick(record)}>{name}</a>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Schema',
      dataIndex: 'schema_name',
      key: 'schema_name',
      width: 80,
      render: (schema) => <Text type="secondary">{schema || 'public'}</Text>,
    },
    {
      title: '数据源',
      dataIndex: 'source_id',
      key: 'source_id',
      width: 140,
      ellipsis: true,
      render: (sourceId) => (
        <Tag icon={<DatabaseOutlined />} color="blue">
          {getSourceName(sourceId)}
        </Tag>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 180,
      ellipsis: true,
      render: (tags: string[]) => (
        <Space size={2} wrap>
          {tags && tags.length > 0 ? (
            tags.slice(0, 3).map((tag) => (
              <Tag key={tag} color="cyan" style={{ margin: 0 }}>
                {tag}
              </Tag>
            ))
          ) : (
            <Text type="secondary">-</Text>
          )}
          {tags && tags.length > 3 && (
            <Tooltip title={tags.slice(3).join(', ')}>
              <Tag color="default">+{tags.length - 3}</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '列数',
      dataIndex: 'columns',
      key: 'column_count',
      width: 60,
      render: (columns) => (
        <Badge count={columns?.length || 0} showZero color="#8c8c8c" />
      ),
    },
  ];

  const columnColumns: ColumnsType<MetadataColumn> = [
    {
      title: '#',
      dataIndex: 'ordinal_position',
      key: 'ordinal_position',
      width: 45,
      render: (pos) => <Text type="secondary">{pos}</Text>,
    },
    {
      title: '列名',
      dataIndex: 'column_name',
      key: 'column_name',
      render: (name, record) => (
        <Space>
          {record.is_primary_key && <KeyOutlined style={{ color: '#faad14' }} />}
          <Text strong={record.is_primary_key}>{name}</Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 120,
      render: (type) => <Tag color="purple">{type}</Tag>,
    },
    {
      title: '可空',
      dataIndex: 'nullable',
      key: 'nullable',
      width: 60,
      render: (nullable) => (
        <Tag color={nullable ? 'default' : 'red'}>
          {nullable ? 'YES' : 'NO'}
        </Tag>
      ),
    },
    {
      title: '主键',
      dataIndex: 'is_primary_key',
      key: 'is_primary_key',
      width: 60,
      render: (isPK) => isPK ? <Tag color="gold">PK</Tag> : '-',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      render: (tags: string[]) => (
        <Space size={2} wrap>
          {tags && tags.length > 0 ? (
            tags.slice(0, 2).map((tag) => (
              <Tag key={tag} color="cyan" style={{ margin: 0 }}>
                {tag}
              </Tag>
            ))
          ) : (
            <Text type="secondary">-</Text>
          )}
          {tags && tags.length > 2 && (
            <Tooltip title={tags.slice(2).join(', ')}>
              <Tag color="default">+{tags.length - 2}</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc, record) => (
        <Tooltip title={desc || record.ai_inferred_meaning}>
          <Text type="secondary">{desc || record.ai_inferred_meaning || '-'}</Text>
        </Tooltip>
      ),
    },
  ];

  return (
    <AuthGuard>
      <Row gutter={16} style={{ height: 'calc(100vh - 120px)' }}>
        {/* 左侧: 表列表 */}
        <Col span={selectedTable ? 10 : 24} style={{ height: '100%' }}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>元数据浏览</span>
                <Badge count={filteredTables.length} showZero color="#1890ff" />
              </Space>
            }
            extra={
              <Space>
                {selectedTableIds.length > 0 && (
                  <Space size={4}>
                    <Text type="secondary">已选 {selectedTableIds.length} 项</Text>
                    <Button
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={() => handleBatchTagClick('add')}
                    >
                      添加标签
                    </Button>
                    <Button
                      size="small"
                      icon={<DeleteOutlined />}
                      danger
                      onClick={() => handleBatchTagClick('remove')}
                    >
                      移除标签
                    </Button>
                  </Space>
                )}
                <Select
                  allowClear
                  placeholder="筛选数据源"
                  style={{ width: 160 }}
                  value={selectedSourceId}
                  onChange={handleSourceChange}
                  options={sources.map(s => ({ value: s.id, label: s.name }))}
                />
              </Space>
            }
            style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            bodyStyle={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}
          >
            <Search
              placeholder="搜索表名..."
              prefix={<SearchOutlined />}
              allowClear
              value={searchKeyword}
              onChange={e => setSearchKeyword(e.target.value)}
              style={{ marginBottom: 12, flexShrink: 0 }}
            />

            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
              <Spin spinning={loading} style={{ height: '100%' }}>
                {filteredTables.length > 0 ? (
                  <Table
                    columns={tableColumns}
                    dataSource={filteredTables}
                    rowKey="id"
                    size="small"
                    scroll={{ y: 'calc(100vh - 340px)' }}
                  pagination={{
                    defaultPageSize: 10,
                    size: 'small',
                    showSizeChanger: true,
                    showQuickJumper: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showTotal: (total, range) =>
                      `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                    hideOnSinglePage: false,
                  }}
                  onRow={(record) => ({
                    onClick: () => handleTableClick(record),
                    style: {
                      cursor: 'pointer',
                      background: selectedTable?.id === record.id ? '#e6f7ff' : undefined,
                    },
                  })}
                />
              ) : (
                <Empty description="暂无元数据，请先扫描数据源" />
              )}
              </Spin>
            </div>
          </Card>
        </Col>

        {/* 右侧: 表详情 */}
        {selectedTable && (
          <Col span={14} style={{ height: '100%' }}>
            <Card
              title={
                <Space>
                  <TableOutlined />
                  <span>{selectedTable.table_name}</span>
                  <Tag color="blue">{selectedTable.schema_name || 'public'}</Tag>
                </Space>
              }
              extra={
                <Text type="secondary">
                  {getSourceName(selectedTable.source_id)}
                </Text>
              }
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
              bodyStyle={{ flex: 1, overflow: 'auto' }}
            >
              <Spin spinning={detailLoading}>
                <Descriptions
                  bordered
                  size="small"
                  column={2}
                  style={{ marginBottom: 16 }}
                >
                  <Descriptions.Item label="表名">
                    {selectedTable.table_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="Schema">
                    {selectedTable.schema_name || 'public'}
                  </Descriptions.Item>
                  <Descriptions.Item label="数据源">
                    <Tag icon={<DatabaseOutlined />} color="blue">
                      {getSourceName(selectedTable.source_id)}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="行数">
                    {selectedTable.row_count?.toLocaleString() || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="标签" span={2}>
                    <Space wrap>
                      {selectedTable.tags && selectedTable.tags.length > 0 ? (
                        selectedTable.tags.map((tag) => (
                          <Tag key={tag} color="cyan">
                            {tag}
                          </Tag>
                        ))
                      ) : (
                        <Text type="secondary">无标签</Text>
                      )}
                    </Space>
                  </Descriptions.Item>
                  {(selectedTable.description || selectedTable.ai_description) && (
                    <Descriptions.Item label="描述" span={2}>
                      {selectedTable.description || selectedTable.ai_description}
                    </Descriptions.Item>
                  )}
                </Descriptions>

                <div style={{ marginBottom: 12 }}>
                  <Space>
                    <Title level={5} style={{ margin: 0 }}>列信息</Title>
                    <Badge
                      count={selectedTable.columns?.length || 0}
                      showZero
                      color="#722ed1"
                    />
                  </Space>
                </div>

                <Table
                  columns={columnColumns}
                  dataSource={selectedTable.columns}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  scroll={{ y: 'calc(100vh - 450px)' }}
                />
              </Spin>
            </Card>
          </Col>
        )}

        {/* 右侧: 空状态提示 */}
        {!selectedTable && (
          <Col span={0}>
            {/* Hidden when no table selected - left side expands to full width */}
          </Col>
        )}
      </Row>

      {/* 批量标签管理 Modal */}
      <Modal
        title={
          <Space>
            <TagsOutlined />
            <span>{tagModalMode === 'add' ? '批量添加标签' : '批量移除标签'}</span>
          </Space>
        }
        open={tagModalVisible}
        onCancel={() => setTagModalVisible(false)}
        onOk={handleBatchTagSubmit}
        confirmLoading={batchLoading}
        okText={tagModalMode === 'add' ? '添加' : '移除'}
        okButtonProps={{
          danger: tagModalMode === 'remove',
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text type="secondary">
              {tagModalMode === 'add'
                ? `将为选中的 ${selectedTableIds.length} 个表添加以下标签：`
                : `将从选中的 ${selectedTableIds.length} 个表移除以下标签：`}
            </Text>
          </div>

          <div>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>
              常用标签
            </Text>
            <Space wrap>
              {allTagOptions.map((tag) => (
                <Tag.CheckableTag
                  key={tag}
                  checked={selectedTags.includes(tag)}
                  onChange={(checked) => {
                    if (checked) {
                      setSelectedTags(prev => [...prev, tag]);
                    } else {
                      setSelectedTags(prev => prev.filter(t => t !== tag));
                    }
                  }}
                  style={{
                    border: '1px solid #d9d9d9',
                    padding: '2px 8px',
                  }}
                >
                  {tag}
                </Tag.CheckableTag>
              ))}
            </Space>
          </div>

          <div>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>
              自定义标签
            </Text>
            <Input
              placeholder="输入自定义标签名称"
              value={customTag}
              onChange={(e) => setCustomTag(e.target.value)}
              onPressEnter={() => {
                if (customTag.trim() && !selectedTags.includes(customTag.trim())) {
                  setSelectedTags(prev => [...prev, customTag.trim()]);
                  setCustomTag('');
                }
              }}
              suffix={
                <Button
                  type="link"
                  size="small"
                  disabled={!customTag.trim()}
                  onClick={() => {
                    if (customTag.trim() && !selectedTags.includes(customTag.trim())) {
                      setSelectedTags(prev => [...prev, customTag.trim()]);
                      setCustomTag('');
                    }
                  }}
                >
                  添加
                </Button>
              }
            />
          </div>

          {selectedTags.length > 0 && (
            <div>
              <Text strong style={{ marginBottom: 8, display: 'block' }}>
                已选标签
              </Text>
              <Space wrap>
                {selectedTags.map((tag) => (
                  <Tag
                    key={tag}
                    closable
                    color={tagModalMode === 'add' ? 'green' : 'red'}
                    onClose={() => setSelectedTags(prev => prev.filter(t => t !== tag))}
                  >
                    {tag}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
        </Space>
      </Modal>
    </AuthGuard>
  );
}
