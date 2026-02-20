'use client';

import { useState, useMemo } from 'react';
import {
  Card,
  Space,
  Typography,
  Tag,
  Table,
  Select,
  Empty,
  Spin,
  Row,
  Col,
  Descriptions,
  Timeline,
  Badge,
  Tooltip,
} from 'antd';
import {
  HistoryOutlined,
  PlusCircleOutlined,
  MinusCircleOutlined,
  EditOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

export interface VersionColumn {
  column_name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
  default_value?: string;
  description?: string;
  ordinal_position: number;
}

export interface VersionSnapshot {
  table_name: string;
  schema_name?: string;
  description?: string;
  columns: VersionColumn[];
  row_count?: number;
}

export interface MetadataVersionInfo {
  id: string;
  version: number;
  snapshot_json: VersionSnapshot;
  created_at: string;
}

export interface ColumnDiff {
  column_name: string;
  status: 'added' | 'removed' | 'modified' | 'unchanged';
  old_column?: VersionColumn;
  new_column?: VersionColumn;
  changes?: string[];
}

export interface VersionDiffProps {
  versions: MetadataVersionInfo[];
  loading?: boolean;
  title?: string;
}

const getColumnDiffs = (
  oldSnapshot: VersionSnapshot | null,
  newSnapshot: VersionSnapshot
): ColumnDiff[] => {
  const diffs: ColumnDiff[] = [];

  if (!oldSnapshot) {
    newSnapshot.columns.forEach((col) => {
      diffs.push({
        column_name: col.column_name,
        status: 'added',
        new_column: col,
      });
    });
    return diffs;
  }

  const oldColumns = new Map(
    oldSnapshot.columns.map((col) => [col.column_name, col])
  );
  const newColumns = new Map(
    newSnapshot.columns.map((col) => [col.column_name, col])
  );

  newSnapshot.columns.forEach((newCol) => {
    const oldCol = oldColumns.get(newCol.column_name);

    if (!oldCol) {
      diffs.push({
        column_name: newCol.column_name,
        status: 'added',
        new_column: newCol,
      });
    } else {
      const changes: string[] = [];

      if (oldCol.data_type !== newCol.data_type) {
        changes.push(`类型: ${oldCol.data_type} → ${newCol.data_type}`);
      }
      if (oldCol.nullable !== newCol.nullable) {
        changes.push(`可空: ${oldCol.nullable ? 'YES' : 'NO'} → ${newCol.nullable ? 'YES' : 'NO'}`);
      }
      if (oldCol.is_primary_key !== newCol.is_primary_key) {
        changes.push(`主键: ${oldCol.is_primary_key ? 'YES' : 'NO'} → ${newCol.is_primary_key ? 'YES' : 'NO'}`);
      }
      if (oldCol.default_value !== newCol.default_value) {
        changes.push(`默认值: ${oldCol.default_value || 'NULL'} → ${newCol.default_value || 'NULL'}`);
      }
      if (oldCol.description !== newCol.description) {
        changes.push('描述已更新');
      }

      if (changes.length > 0) {
        diffs.push({
          column_name: newCol.column_name,
          status: 'modified',
          old_column: oldCol,
          new_column: newCol,
          changes,
        });
      } else {
        diffs.push({
          column_name: newCol.column_name,
          status: 'unchanged',
          old_column: oldCol,
          new_column: newCol,
        });
      }
    }
  });

  oldSnapshot.columns.forEach((oldCol) => {
    if (!newColumns.has(oldCol.column_name)) {
      diffs.push({
        column_name: oldCol.column_name,
        status: 'removed',
        old_column: oldCol,
      });
    }
  });

  return diffs.sort((a, b) => {
    const statusOrder = { added: 1, modified: 2, removed: 3, unchanged: 4 };
    return statusOrder[a.status] - statusOrder[b.status];
  });
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'added':
      return '#52c41a';
    case 'removed':
      return '#ff4d4f';
    case 'modified':
      return '#faad14';
    default:
      return '#8c8c8c';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'added':
      return <PlusCircleOutlined style={{ color: '#52c41a' }} />;
    case 'removed':
      return <MinusCircleOutlined style={{ color: '#ff4d4f' }} />;
    case 'modified':
      return <EditOutlined style={{ color: '#faad14' }} />;
    default:
      return null;
  }
};

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'added':
      return '新增';
    case 'removed':
      return '删除';
    case 'modified':
      return '修改';
    default:
      return '未变';
  }
};

export default function VersionDiff({
  versions,
  loading = false,
  title = '版本对比',
}: VersionDiffProps) {
  const sortedVersions = useMemo(
    () => [...versions].sort((a, b) => b.version - a.version),
    [versions]
  );

  const [leftVersionId, setLeftVersionId] = useState<string | undefined>(
    sortedVersions[1]?.id
  );
  const [rightVersionId, setRightVersionId] = useState<string | undefined>(
    sortedVersions[0]?.id
  );

  const leftVersion = sortedVersions.find((v) => v.id === leftVersionId);
  const rightVersion = sortedVersions.find((v) => v.id === rightVersionId);

  const columnDiffs = useMemo(() => {
    if (!rightVersion) return [];
    return getColumnDiffs(
      leftVersion?.snapshot_json || null,
      rightVersion.snapshot_json
    );
  }, [leftVersion, rightVersion]);

  const diffStats = useMemo(() => {
    return {
      added: columnDiffs.filter((d) => d.status === 'added').length,
      removed: columnDiffs.filter((d) => d.status === 'removed').length,
      modified: columnDiffs.filter((d) => d.status === 'modified').length,
      unchanged: columnDiffs.filter((d) => d.status === 'unchanged').length,
    };
  }, [columnDiffs]);

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
            加载版本信息...
          </Text>
        </div>
      </Card>
    );
  }

  if (versions.length === 0) {
    return (
      <Card title={title}>
        <Empty description="暂无版本历史记录" />
      </Card>
    );
  }

  const diffColumns: ColumnsType<ColumnDiff> = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>
        </Space>
      ),
      filters: [
        { text: '新增', value: 'added' },
        { text: '删除', value: 'removed' },
        { text: '修改', value: 'modified' },
        { text: '未变', value: 'unchanged' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '列名',
      dataIndex: 'column_name',
      key: 'column_name',
      render: (name, record) => (
        <Text
          strong
          style={{
            textDecoration: record.status === 'removed' ? 'line-through' : undefined,
            color: getStatusColor(record.status),
          }}
        >
          {name}
        </Text>
      ),
    },
    {
      title: '旧类型',
      key: 'old_type',
      width: 120,
      render: (_, record) =>
        record.old_column ? (
          <Tag color="default">{record.old_column.data_type}</Tag>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '新类型',
      key: 'new_type',
      width: 120,
      render: (_, record) =>
        record.new_column ? (
          <Tag
            color={
              record.old_column?.data_type !== record.new_column.data_type
                ? 'orange'
                : 'default'
            }
          >
            {record.new_column.data_type}
          </Tag>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '变更详情',
      dataIndex: 'changes',
      key: 'changes',
      render: (changes: string[] | undefined) =>
        changes && changes.length > 0 ? (
          <Tooltip title={changes.join('\n')}>
            <Space size={4} wrap>
              {changes.slice(0, 2).map((change, i) => (
                <Tag key={i} color="orange" style={{ margin: 0 }}>
                  {change}
                </Tag>
              ))}
              {changes.length > 2 && (
                <Tag color="default">+{changes.length - 2}</Tag>
              )}
            </Space>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>{title}</span>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Version Selectors */}
        <Row gutter={16} align="middle">
          <Col span={10}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">旧版本 (基准)</Text>
              <Select
                style={{ width: '100%' }}
                placeholder="选择旧版本"
                value={leftVersionId}
                onChange={setLeftVersionId}
                allowClear
                options={sortedVersions.map((v) => ({
                  value: v.id,
                  label: `v${v.version} - ${new Date(v.created_at).toLocaleString()}`,
                }))}
              />
            </Space>
          </Col>
          <Col span={4} style={{ textAlign: 'center' }}>
            <SwapOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          </Col>
          <Col span={10}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">新版本 (对比)</Text>
              <Select
                style={{ width: '100%' }}
                placeholder="选择新版本"
                value={rightVersionId}
                onChange={setRightVersionId}
                options={sortedVersions.map((v) => ({
                  value: v.id,
                  label: `v${v.version} - ${new Date(v.created_at).toLocaleString()}`,
                }))}
              />
            </Space>
          </Col>
        </Row>

        {/* Diff Statistics */}
        {rightVersion && (
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small" style={{ background: '#f6ffed', borderColor: '#b7eb8f' }}>
                <Space>
                  <PlusCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                  <div>
                    <Text type="secondary">新增列</Text>
                    <Title level={4} style={{ margin: 0, color: '#52c41a' }}>
                      {diffStats.added}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: '#fff2f0', borderColor: '#ffccc7' }}>
                <Space>
                  <MinusCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
                  <div>
                    <Text type="secondary">删除列</Text>
                    <Title level={4} style={{ margin: 0, color: '#ff4d4f' }}>
                      {diffStats.removed}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ background: '#fffbe6', borderColor: '#ffe58f' }}>
                <Space>
                  <EditOutlined style={{ color: '#faad14', fontSize: 20 }} />
                  <div>
                    <Text type="secondary">修改列</Text>
                    <Title level={4} style={{ margin: 0, color: '#faad14' }}>
                      {diffStats.modified}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Space>
                  <Badge status="default" />
                  <div>
                    <Text type="secondary">未变列</Text>
                    <Title level={4} style={{ margin: 0, color: '#8c8c8c' }}>
                      {diffStats.unchanged}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>
        )}

        {/* Version Info Comparison */}
        {leftVersion && rightVersion && (
          <Row gutter={16}>
            <Col span={12}>
              <Card
                title={`v${leftVersion.version} (旧)`}
                size="small"
                style={{ borderColor: '#d9d9d9' }}
              >
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="表名">
                    {leftVersion.snapshot_json.table_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="列数">
                    {leftVersion.snapshot_json.columns?.length || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label="记录时间">
                    {new Date(leftVersion.created_at).toLocaleString()}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col span={12}>
              <Card
                title={`v${rightVersion.version} (新)`}
                size="small"
                style={{ borderColor: '#1890ff' }}
              >
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="表名">
                    {rightVersion.snapshot_json.table_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="列数">
                    {rightVersion.snapshot_json.columns?.length || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label="记录时间">
                    {new Date(rightVersion.created_at).toLocaleString()}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>
        )}

        {/* Column Diff Table */}
        {rightVersion && (
          <Card title="列变更详情" size="small">
            <Table
              columns={diffColumns}
              dataSource={columnDiffs}
              rowKey="column_name"
              size="small"
              pagination={false}
              rowClassName={(record) => {
                if (record.status === 'added') return 'diff-row-added';
                if (record.status === 'removed') return 'diff-row-removed';
                if (record.status === 'modified') return 'diff-row-modified';
                return '';
              }}
            />
          </Card>
        )}

        {/* Version Timeline */}
        {versions.length > 2 && (
          <Card title="版本历史时间线" size="small">
            <Timeline
              mode="left"
              items={sortedVersions.slice(0, 10).map((v) => ({
                color: v.id === rightVersionId ? 'blue' : v.id === leftVersionId ? 'gray' : 'gray',
                children: (
                  <Space direction="vertical" size={0}>
                    <Text strong>v{v.version}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(v.created_at).toLocaleString()}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {v.snapshot_json.columns?.length || 0} 列
                    </Text>
                  </Space>
                ),
              }))}
            />
          </Card>
        )}
      </Space>

      <style jsx global>{`
        .diff-row-added {
          background-color: #f6ffed;
        }
        .diff-row-removed {
          background-color: #fff2f0;
        }
        .diff-row-modified {
          background-color: #fffbe6;
        }
      `}</style>
    </Card>
  );
}
