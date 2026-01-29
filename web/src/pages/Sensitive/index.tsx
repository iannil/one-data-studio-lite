import React, { useEffect, useState } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Tabs,
  Form,
  Modal,
  Select,
  message,
  Typography,
  Space,
  Statistic,
  Row,
  Col,
  Spin,
} from 'antd';
import {
  ScanOutlined,
  SafetyOutlined,
  PlusOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { scan, getRules, addRule, getReports } from '../../api/sensitive';
import { SensitiveScanReport, DetectionRule } from '../../types';

const { Title, Text } = Typography;

const riskLevelConfig = {
  low: { color: 'green', text: '低风险' },
  medium: { color: 'orange', text: '中风险' },
  high: { color: 'red', text: '高风险' },
  critical: { color: 'magenta', text: '严重' },
};

const Sensitive: React.FC = () => {
  const [tableName, setTableName] = useState('');
  const [scanning, setScanning] = useState(false);
  const [report, setReport] = useState<SensitiveScanReport | null>(null);
  const [rules, setRules] = useState<DetectionRule[]>([]);
  const [reports, setReports] = useState<SensitiveScanReport[]>([]);
  const [loadingRules, setLoadingRules] = useState(true);
  const [loadingReports, setLoadingReports] = useState(true);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [addForm] = Form.useForm();

  useEffect(() => {
    fetchRules();
    fetchReports();
  }, []);

  const fetchRules = async () => {
    try {
      const data = await getRules();
      setRules(data);
    } catch (error) {
      message.error('获取规则列表失败');
    } finally {
      setLoadingRules(false);
    }
  };

  const fetchReports = async () => {
    try {
      const data = await getReports();
      setReports(data);
    } catch (error) {
      message.error('获取扫描报告失败');
    } finally {
      setLoadingReports(false);
    }
  };

  const handleScan = async () => {
    if (!tableName.trim()) {
      message.warning('请输入表名');
      return;
    }
    setScanning(true);
    setReport(null);
    try {
      const data = await scan({ table_name: tableName });
      setReport(data);
      message.success('扫描完成');
      fetchReports(); // 刷新报告列表
    } catch (error: any) {
      message.error(error.response?.data?.detail || '扫描失败');
    } finally {
      setScanning(false);
    }
  };

  const handleAddRule = async (values: any) => {
    try {
      await addRule(values);
      message.success('规则添加成功');
      setAddModalVisible(false);
      addForm.resetFields();
      fetchRules();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '添加失败');
    }
  };

  // 字段详情表格列
  const fieldColumns = [
    {
      title: '字段名',
      dataIndex: 'column_name',
      key: 'column_name',
    },
    {
      title: '敏感等级',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: string) => {
        const config = riskLevelConfig[level as keyof typeof riskLevelConfig] || riskLevelConfig.low;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '检测类型',
      dataIndex: 'detected_types',
      key: 'detected_types',
      render: (types: string[]) => types?.map((t) => <Tag key={t}>{t}</Tag>),
    },
    {
      title: '检测方法',
      dataIndex: 'detection_method',
      key: 'detection_method',
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
  ];

  // 规则表格列
  const ruleColumns = [
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { title: '正则表达式', dataIndex: 'pattern', key: 'pattern', ellipsis: true },
    {
      title: '敏感等级',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: string) => {
        const config = riskLevelConfig[level as keyof typeof riskLevelConfig] || riskLevelConfig.low;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'default'}>{enabled ? '启用' : '禁用'}</Tag>
      ),
    },
  ];

  // 报告列表列
  const reportColumns = [
    { title: '表名', dataIndex: 'table_name', key: 'table_name' },
    { title: '扫描时间', dataIndex: 'scan_time', key: 'scan_time' },
    { title: '总列数', dataIndex: 'total_columns', key: 'total_columns' },
    { title: '敏感列数', dataIndex: 'sensitive_columns', key: 'sensitive_columns' },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (level: string) => {
        const config = riskLevelConfig[level as keyof typeof riskLevelConfig] || riskLevelConfig.low;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  const tabItems = [
    {
      key: 'scan',
      label: '敏感扫描',
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 扫描输入 */}
          <Card size="small">
            <Space>
              <Input
                placeholder="请输入表名，如：user_info"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                style={{ width: 300 }}
                onPressEnter={handleScan}
              />
              <Button
                type="primary"
                icon={<ScanOutlined />}
                loading={scanning}
                onClick={handleScan}
              >
                开始扫描
              </Button>
            </Space>
          </Card>

          {/* 扫描结果 */}
          {report && (
            <>
              <Row gutter={16}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="风险等级"
                      value={riskLevelConfig[report.risk_level]?.text || report.risk_level}
                      valueStyle={{
                        color: report.risk_level === 'critical' || report.risk_level === 'high'
                          ? '#cf1322'
                          : report.risk_level === 'medium'
                          ? '#fa8c16'
                          : '#3f8600',
                      }}
                      prefix={<ExclamationCircleOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="总列数" value={report.total_columns} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="敏感列数"
                      value={report.sensitive_columns}
                      valueStyle={{ color: report.sensitive_columns > 0 ? '#cf1322' : '#3f8600' }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="扫描时间" value={report.scan_time} />
                  </Card>
                </Col>
              </Row>

              <Card title="敏感字段详情" size="small">
                <Table
                  columns={fieldColumns}
                  dataSource={report.fields.map((f, i) => ({ ...f, key: i }))}
                  pagination={false}
                  size="small"
                />
              </Card>
            </>
          )}
        </Space>
      ),
    },
    {
      key: 'rules',
      label: '检测规则',
      children: (
        <Card
          size="small"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAddModalVisible(true)}
            >
              添加规则
            </Button>
          }
        >
          {loadingRules ? (
            <Spin />
          ) : (
            <Table
              columns={ruleColumns}
              dataSource={rules.map((r) => ({ ...r, key: r.id }))}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          )}
        </Card>
      ),
    },
    {
      key: 'reports',
      label: '扫描历史',
      children: (
        <Card size="small">
          {loadingReports ? (
            <Spin />
          ) : (
            <Table
              columns={reportColumns}
              dataSource={reports.map((r) => ({ ...r, key: r.id }))}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          )}
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <SafetyOutlined /> 敏感数据检测
      </Title>
      <Tabs items={tabItems} />

      {/* 添加规则弹窗 */}
      <Modal
        title="添加检测规则"
        open={addModalVisible}
        onCancel={() => setAddModalVisible(false)}
        onOk={() => addForm.submit()}
      >
        <Form form={addForm} layout="vertical" onFinish={handleAddRule}>
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="如：自定义手机号" />
          </Form.Item>
          <Form.Item
            name="pattern"
            label="正则表达式"
            rules={[{ required: true, message: '请输入正则表达式' }]}
          >
            <Input placeholder="如：^1[3-9]\d{9}$" />
          </Form.Item>
          <Form.Item
            name="sensitivity_level"
            label="敏感等级"
            rules={[{ required: true, message: '请选择敏感等级' }]}
          >
            <Select>
              <Select.Option value="low">低风险</Select.Option>
              <Select.Option value="medium">中风险</Select.Option>
              <Select.Option value="high">高风险</Select.Option>
              <Select.Option value="critical">严重</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="规则描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Sensitive;
