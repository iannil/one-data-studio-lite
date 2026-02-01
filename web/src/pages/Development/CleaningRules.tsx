import React, { useEffect, useState } from 'react';
import { Card, Input, Button, Table, Tag, Tabs, message, Typography, Space, Spin } from 'antd';
import { ClearOutlined, BulbOutlined, SearchOutlined } from '@ant-design/icons';
import { recommendRulesV1, getCleaningRulesV1 } from '../../api/cleaning';

const { Title } = Typography;

const CleaningRules: React.FC = () => {
  const [tableName, setTableName] = useState('');
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  const fetchTemplates = async () => {
    setLoadingTemplates(true);
    try {
      const resp = await getCleaningRulesV1();
      if (resp.success) {
        setTemplates(resp.data || []);
      } else {
        message.error(resp.message || '获取规则模板失败');
      }
    } catch {
      message.error('获取规则模板失败');
    } finally {
      setLoadingTemplates(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleRecommend = async () => {
    if (!tableName.trim()) {
      message.warning('请输入表名');
      return;
    }
    setLoading(true);
    try {
      const resp = await recommendRulesV1({ table_name: tableName });
      if (resp.success) {
        setRecommendations(resp.data?.recommended_rules || []);
        message.success('AI 推荐完成');
      } else {
        message.error(resp.message || 'AI 推荐失败');
      }
    } catch {
      message.error('AI 推荐失败');
    } finally {
      setLoading(false);
    }
  };

  const recommendColumns = [
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { title: '目标字段', dataIndex: 'column', key: 'column' },
    {
      title: '规则类型',
      dataIndex: 'type',
      key: 'type',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (v: number) => v != null ? `${(v * 100).toFixed(0)}%` : '-',
    },
  ];

  const templateColumns = [
    { title: '模板名称', dataIndex: 'name', key: 'name' },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (text: string) => <Tag color="purple">{text}</Tag>,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '适用场景', dataIndex: 'scenario', key: 'scenario', render: (t: string) => t || '-' },
  ];

  const tabItems = [
    {
      key: 'recommend',
      label: 'AI 推荐',
      children: (
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
          <Card size="small">
            <Space>
              <Input
                data-testid="table-name-input"
                placeholder="输入表名获取 AI 清洗推荐"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                onPressEnter={handleRecommend}
                style={{ width: 300 }}
                prefix={<SearchOutlined />}
              />
              <Button
                data-testid="ai-recommend-button"
                type="primary"
                icon={<BulbOutlined />}
                loading={loading}
                onClick={handleRecommend}
              >
                AI 推荐
              </Button>
            </Space>
          </Card>
          {recommendations.length > 0 && (
            <Card title={`推荐清洗规则 (${recommendations.length})`} size="small">
              <Table
                columns={recommendColumns}
                dataSource={recommendations.map((r, i) => ({ ...r, key: i }))}
                pagination={false}
                size="small"
              />
            </Card>
          )}
        </Space>
      ),
    },
    {
      key: 'templates',
      label: '规则模板',
      children: (
        <Card size="small">
          {loadingTemplates ? (
            <Spin />
          ) : (
            <Table
              columns={templateColumns}
              dataSource={templates.map((t, i) => ({ ...t, key: t.id || i }))}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          )}
        </Card>
      ),
    },
  ];

  return (
    <div data-testid="cleaning-rules-page">
      <Title level={4} style={{ marginBottom: 16 }}>
        <ClearOutlined /> 清洗规则配置
      </Title>
      <Tabs data-testid="cleaning-tabs" items={tabItems} />
    </div>
  );
};

export default CleaningRules;
