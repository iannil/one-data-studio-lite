import React, { useState } from 'react';
import { Card, Input, Button, message, Typography, Space, Select, Tag } from 'antd';
import { SettingOutlined, CopyOutlined } from '@ant-design/icons';
import { generateConfigV1 } from '../../api/cleaning';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const TransformConfig: React.FC = () => {
  const [tableName, setTableName] = useState('');
  const [selectedRules, setSelectedRules] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<string>('');

  const ruleOptions = [
    { label: '去除空值', value: 'remove_null' },
    { label: '去重', value: 'dedup' },
    { label: '类型转换', value: 'type_cast' },
    { label: '字符串清洗', value: 'string_clean' },
    { label: '日期标准化', value: 'date_normalize' },
    { label: '枚举映射', value: 'enum_mapping' },
    { label: '数值范围校验', value: 'range_check' },
    { label: '正则替换', value: 'regex_replace' },
  ];

  const handleGenerate = async () => {
    if (!tableName.trim()) {
      message.warning('请输入表名');
      return;
    }
    if (selectedRules.length === 0) {
      message.warning('请至少选择一个转换规则');
      return;
    }
    setLoading(true);
    try {
      const resp = await generateConfigV1({
        table_name: tableName,
        rules: selectedRules,
        output_format: 'seatunnel',
      });
      if (resp.success && resp.data) {
        const configStr = resp.data.config;
        setConfig(configStr);
        message.success('配置生成成功');
      } else {
        message.error(resp.message || '配置生成失败');
      }
    } catch {
      message.error('配置生成失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(config).then(() => {
      message.success('已复制到剪贴板');
    });
  };

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SettingOutlined /> 数据转换配置
      </Title>
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <Card size="small" title="配置参数">
          <Space orientation="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Paragraph strong>目标表名</Paragraph>
              <Input
                placeholder="如 db.user_info"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                style={{ width: 400 }}
              />
            </div>
            <div>
              <Paragraph strong>转换规则</Paragraph>
              <Select
                mode="multiple"
                placeholder="选择需要的转换规则"
                value={selectedRules}
                onChange={setSelectedRules}
                options={ruleOptions}
                style={{ width: '100%' }}
              />
              <div style={{ marginTop: 8 }}>
                {selectedRules.map((r) => {
                  const opt = ruleOptions.find((o) => o.value === r);
                  return <Tag key={r} color="blue">{opt?.label || r}</Tag>;
                })}
              </div>
            </div>
            <Button type="primary" loading={loading} onClick={handleGenerate}>
              生成 SeaTunnel 配置
            </Button>
          </Space>
        </Card>

        {config && (
          <Card
            title="生成的 SeaTunnel Transform 配置"
            size="small"
            extra={
              <Button icon={<CopyOutlined />} onClick={handleCopy} size="small">
                复制
              </Button>
            }
          >
            <TextArea
              value={config}
              readOnly
              rows={20}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </Card>
        )}
      </Space>
    </div>
  );
};

export default TransformConfig;
