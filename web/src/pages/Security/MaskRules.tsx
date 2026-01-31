import React, { useEffect, useState } from 'react';
import { Card, Button, Input, message, Typography, Space, Spin, Alert } from 'antd';
import { LockOutlined, SaveOutlined, ReloadOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons';
import { getMaskRules, updateMaskRule } from '../../api/shardingsphere';

const { Title } = Typography;
const { TextArea } = Input;

const MaskRules: React.FC = () => {
  const [rules, setRules] = useState<any>(null);
  const [rawYaml, setRawYaml] = useState('');
  const [editText, setEditText] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMaskRules();
      setRules(data.rules);
      setRawYaml(data.raw_yaml);
      setEditText(JSON.stringify(data.rules, null, 2));
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取脱敏规则失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const parsed = JSON.parse(editText);
      await updateMaskRule(parsed);
      message.success('脱敏规则已保存');
      setEditing(false);
      fetchRules();
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        message.error('JSON 格式错误，请检查');
      } else {
        message.error(err.response?.data?.detail || '保存失败');
      }
    } finally {
      setSaving(false);
    }
  };

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
          style={{ marginBottom: 16 }}
        />
      )}

      <Card
        size="small"
        extra={
          <Space>
            {editing ? (
              <>
                <Button onClick={() => { setEditing(false); setEditText(JSON.stringify(rules, null, 2)); }}>
                  取消
                </Button>
                <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
                  保存
                </Button>
              </>
            ) : (
              <>
                <Button icon={<EditOutlined />} onClick={() => setEditing(true)}>
                  编辑
                </Button>
                <Button icon={<ReloadOutlined />} onClick={fetchRules}>
                  刷新
                </Button>
              </>
            )}
          </Space>
        }
      >
        {loading ? (
          <Spin />
        ) : editing ? (
          <TextArea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={25}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
        ) : (
          <Space orientation="vertical" style={{ width: '100%' }} size="middle">
            <Card title={<><EyeOutlined /> YAML 原始配置</>} type="inner" size="small">
              <pre style={{
                background: '#f5f5f5',
                padding: 16,
                borderRadius: 4,
                overflow: 'auto',
                margin: 0,
                fontSize: 12,
                maxHeight: 400,
              }}>
                {rawYaml || '无配置内容'}
              </pre>
            </Card>
            <Card title="解析后结构（JSON）" type="inner" size="small">
              <pre style={{
                background: '#f5f5f5',
                padding: 16,
                borderRadius: 4,
                overflow: 'auto',
                margin: 0,
                fontSize: 12,
                maxHeight: 400,
              }}>
                {rules ? JSON.stringify(rules, null, 2) : '无配置内容'}
              </pre>
            </Card>
          </Space>
        )}
      </Card>
    </div>
  );
};

export default MaskRules;
