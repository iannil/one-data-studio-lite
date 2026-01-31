import React, { useEffect, useState } from 'react';
import { Card, Button, Input, message, Typography, Space, Spin, Alert, Table } from 'antd';
import { LockOutlined, ReloadOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { getMaskRulesV1, createMaskRuleV1, deleteMaskRulesV1 } from '../../api/shardingsphere';
import type { MaskRule } from '../../api/shardingsphere';

const { Title } = Typography;
const { TextArea } = Input;

const MaskRules: React.FC = () => {
  const [rules, setRules] = useState<MaskRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTableName, setNewTableName] = useState('');
  const [newColumnName, setNewColumnName] = useState('');
  const [newAlgorithm, setNewAlgorithm] = useState('KEEP_FIRST_N_LAST_M');
  const [adding, setAdding] = useState(false);

  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getMaskRulesV1();
      setRules(resp.data?.rules || []);
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.detail || '获取脱敏规则失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleAdd = async () => {
    if (!newTableName.trim() || !newColumnName.trim()) {
      message.warning('请输入表名和列名');
      return;
    }
    setAdding(true);
    try {
      await createMaskRuleV1({
        table_name: newTableName,
        column_name: newColumnName,
        algorithm_type: newAlgorithm,
        algorithm_props: {
          'first-n': '3',
          'last-m': '4',
          'replace-char': '*',
        },
      });
      message.success('脱敏规则已添加');
      setNewTableName('');
      setNewColumnName('');
      fetchRules();
    } catch (err: any) {
      message.error(err.response?.data?.message || err.response?.data?.detail || '添加失败');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (tableName: string, columnName: string) => {
    try {
      await deleteMaskRulesV1(tableName, columnName);
      message.success('脱敏规则已删除');
      fetchRules();
    } catch (err: any) {
      message.error(err.response?.data?.message || err.response?.data?.detail || '删除失败');
    }
  };

  const columns = [
    { title: '表名', dataIndex: 'table_name', key: 'table_name' },
    { title: '列名', dataIndex: 'column_name', key: 'column_name' },
    { title: '算法', dataIndex: 'algorithm_type', key: 'algorithm_type' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: MaskRule) => (
        <Button
          danger
          size="small"
          icon={<DeleteOutlined />}
          onClick={() => handleDelete(record.table_name, record.column_name)}
        >
          删除
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <LockOutlined /> 数据脱敏规则
      </Title>

      {error && (
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Card
        size="small"
        title="添加脱敏规则"
        extra={<Button icon={<ReloadOutlined />} onClick={fetchRules}>刷新</Button>}
        style={{ marginBottom: 16 }}
      >
        <Space>
          <Input
            placeholder="表名"
            value={newTableName}
            onChange={(e) => setNewTableName(e.target.value)}
            style={{ width: 150 }}
          />
          <Input
            placeholder="列名"
            value={newColumnName}
            onChange={(e) => setNewColumnName(e.target.value)}
            style={{ width: 150 }}
          />
          <Input
            placeholder="算法类型"
            value={newAlgorithm}
            onChange={(e) => setNewAlgorithm(e.target.value)}
            style={{ width: 200 }}
          />
          <Button type="primary" icon={<PlusOutlined />} loading={adding} onClick={handleAdd}>
            添加规则
          </Button>
        </Space>
      </Card>

      <Card size="small">
        {loading ? (
          <Spin />
        ) : (
          <Table
            columns={columns}
            dataSource={rules.map((r, i) => ({ ...r, key: i }))}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        )}
      </Card>
    </div>
  );
};

export default MaskRules;
