/**
 * Billing and Subscription Page
 *
 * Manage subscription, invoices, and payment methods.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Table,
  Space,
  Tag,
  Statistic,
  Progress,
  Tabs,
  List,
  Alert,
  Modal,
  Form,
  Select,
  Radio,
  Divider,
  Typography,
  DatePicker,
} from 'antd';
import {
  DollarOutlined,
  FileTextOutlined,
  CreditCardOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ArrowRightOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { TabPane } = Tabs;
const { Text } = Typography;

interface Invoice {
  id: string;
  invoice_number: string;
  period_start: string;
  period_end: string;
  subtotal: number;
  tax_amount: number;
  total: number;
  status: 'draft' | 'pending' | 'paid' | 'overdue';
  due_date: string;
}

interface UsageMetric {
  resource: string;
  used: number;
  limit: number;
  unit: string;
}

interface PlanFeature {
  name: string;
  free: boolean | string;
  basic: boolean | string;
  professional: boolean | string;
  enterprise: boolean | string;
}

const BillingPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedPlan, setSelectedPlan] = useState('free');
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Mock data
  const subscription = {
    plan: 'free',
    status: 'active',
    current_period_start: '2026-03-01',
    current_period_end: '2026-04-01',
    cancel_at_period_end: false,
  };

  const invoices: Invoice[] = [
    {
      id: 'inv_001',
      invoice_number: 'INV-202603-001001',
      period_start: '2026-02-01',
      period_end: '2026-02-28',
      subtotal: 29.00,
      tax_amount: 2.90,
      total: 31.90,
      status: 'paid',
      due_date: '2026-03-15',
    },
    {
      id: 'inv_002',
      invoice_number: 'INV-202603-001002',
      period_start: '2026-03-01',
      period_end: '2026-03-31',
      subtotal: 29.00,
      tax_amount: 2.90,
      total: 31.90,
      status: 'pending',
      due_date: '2026-04-15',
    },
  ];

  const usageMetrics: UsageMetric[] = [
    { resource: 'CPU Hours', used: 45, limit: 100, unit: 'hours' },
    { resource: 'API Requests', used: 4500, limit: 10000, unit: 'requests' },
    { resource: 'Storage', used: 5.2, limit: 10, unit: 'GB' },
    { resource: 'Models', used: 3, limit: 5, unit: 'models' },
  ];

  const features: PlanFeature[] = [
    { name: 'CPU Cores', free: '4', basic: '16', professional: '64', enterprise: '256' },
    { name: 'Memory', free: '16 GB', basic: '64 GB', professional: '256 GB', enterprise: '1024 GB' },
    { name: 'GPU Support', free: false, basic: '1 GPU', professional: '4 GPU', enterprise: '16 GPU' },
    { name: 'Storage', free: '10 GB', basic: '100 GB', professional: '500 GB', enterprise: '2 TB' },
    { name: 'API Requests/day', free: '1,000', basic: '10,000', professional: '100,000', enterprise: '1,000,000' },
    { name: 'Max Users', free: '3', basic: '10', professional: '50', enterprise: '500' },
    { name: 'Model Deployment', free: '1', basic: '5', professional: '20', enterprise: '100' },
    { name: 'SSO', free: false, basic: false, professional: true, enterprise: true },
    { name: 'Multi-tenant', free: false, basic: false, professional: false, enterprise: true },
    { name: 'SLA', free: false, basic: '99.5%', professional: '99.9%', enterprise: '99.99%' },
    { name: 'Support', free: 'Community', basic: 'Email', professional: 'Priority', enterprise: '24/7 Dedicated' },
  ];

  const planPricing = {
    free: { price: 0, period: 'forever' },
    basic: { price: 29, period: 'month' },
    professional: { price: 99, period: 'month' },
    enterprise: { price: null, period: 'contact' },
  };

  const invoiceColumns: ColumnsType<Invoice> = [
    {
      title: 'Invoice',
      dataIndex: 'invoice_number',
      key: 'invoice_number',
    },
    {
      title: 'Period',
      key: 'period',
      render: (_, record) => (
        <span>{record.period_start} to {record.period_end}</span>
      ),
    },
    {
      title: 'Amount',
      key: 'amount',
      render: (_, record) => <span>${record.total.toFixed(2)}</span>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          draft: 'default',
          pending: 'orange',
          paid: 'green',
          overdue: 'red',
        };
        return <Tag color={colorMap[status]}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Due Date',
      dataIndex: 'due_date',
      key: 'due_date',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: () => (
        <Button type="link" icon={<DownloadOutlined />}>Download</Button>
      ),
    },
  ];

  const handleUpgrade = () => {
    setUpgradeModalOpen(true);
  };

  const handleConfirmUpgrade = async () => {
    setLoading(true);
    // In production, call upgrade API
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
    setUpgradeModalOpen(false);
    setSelectedPlan('basic');
  };

  const renderPlanCard = (plan: string) => {
    const pricing = planPricing[plan as keyof typeof planPricing];
    const isSelected = selectedPlan === plan;
    const isCurrentPlan = subscription.plan === plan;

    return (
      <Card
        key={plan}
        style={{
          border: isSelected ? '2px solid #1890ff' : '1px solid #d9d9d9',
          position: 'relative',
        }}
        hoverable
        onClick={() => setSelectedPlan(plan)}
      >
        {plan === 'professional' && (
          <Tag color="gold" style={{ position: 'absolute', top: -12, right: 16 }}>
            POPULAR
          </Tag>
        )}
        <Card.Meta
          title={<div style={{ fontSize: 18, textTransform: 'capitalize' }}>{plan}</div>}
          description={
            pricing.price !== null ? (
              <div>
                <span style={{ fontSize: 32, fontWeight: 'bold' }}>${pricing.price}</span>
                <span style={{ color: '#999' }}>/{pricing.period}</span>
              </div>
            ) : (
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>Contact Sales</div>
            )
          }
        />
        <Divider style={{ margin: '16px 0' }} />
        <List
          size="small"
          dataSource={features}
          renderItem={(feature) => {
            const value = feature[plan as keyof PlanFeature];
            const isBoolean = typeof value === 'boolean';
            return (
              <List.Item style={{ border: 'none', padding: '4px 0' }}>
                <Space>
                  {isBoolean ? (
                    value ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <span style={{ color: '#d9d9d9' }}>✕</span>
                  ) : (
                    <span>{value}</span>
                  )}
                  <span>{feature.name}</span>
                </Space>
              </List.Item>
            );
          }}
        />
        <Button
          type={isSelected ? 'primary' : 'default'}
          block
          style={{ marginTop: 16 }}
          disabled={isCurrentPlan}
          onClick={plan !== subscription.plan ? handleUpgrade : undefined}
        >
          {isCurrentPlan ? 'Current Plan' : isSelected ? 'Select Plan' : 'Select'}
        </Button>
      </Card>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>Billing & Subscription</h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            Manage your subscription, invoices, and payment methods
          </p>
        </Col>
        <Col>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleUpgrade}>
            Upgrade Plan
          </Button>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="Overview" key="overview">
          <Row gutter={16} style={{ marginBottom: '24px' }}>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Current Plan"
                  value={subscription.plan.toUpperCase()}
                  prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Next Billing Date"
                  value={subscription.current_period_end}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Pending Amount"
                  value={31.90}
                  prefix={<DollarOutlined />}
                  suffix="USD"
                  precision={2}
                />
              </Card>
            </Col>
          </Row>

          <Card title="Current Usage" style={{ marginBottom: '24px' }}>
            <Row gutter={16}>
              {usageMetrics.map((metric) => {
                const percent = (metric.used / metric.limit) * 100;
                const isOverLimit = percent > 100;
                return (
                  <Col span={6} key={metric.resource}>
                    <Card size="small">
                      <Statistic
                        title={metric.resource}
                        value={metric.used}
                        suffix={`/ ${metric.limit} ${metric.unit}`}
                        valueStyle={{
                          color: isOverLimit ? '#cf1322' : percent > 80 ? '#faad14' : undefined,
                          fontSize: 20,
                        }}
                      />
                      <Progress
                        percent={Math.min(percent, 100)}
                        status={isOverLimit ? 'exception' : percent > 80 ? 'warning' : 'normal'}
                        showInfo={false}
                        style={{ marginTop: 8 }}
                      />
                    </Card>
                  </Col>
                );
              })}
            </Row>
          </Card>

          {subscription.plan === 'free' && (
            <Alert
              message="Upgrade Your Plan"
              description="You're currently on the free plan. Upgrade to unlock more features and resources."
              type="info"
              showIcon
              action={
                <Button type="primary" size="small" onClick={handleUpgrade}>
                  View Plans
                </Button>
              }
            />
          )}
        </TabPane>

        <TabPane tab="Plans" key="plans">
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <Row gutter={16}>
              {renderPlanCard('free')}
              {renderPlanCard('basic')}
              {renderPlanCard('professional')}
              {renderPlanCard('enterprise')}
            </Row>
          </div>
        </TabPane>

        <TabPane tab="Invoices" key="invoices">
          <Card title="Billing History">
            <Table
              dataSource={invoices}
              columns={invoiceColumns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="Payment Methods" key="payment">
          <Card title="Payment Methods">
            <Alert
              message="No payment methods configured"
              description="Add a payment method to upgrade your subscription."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Button type="dashed" icon={<CreditCardOutlined />} block>
              Add Payment Method
            </Button>
          </Card>
        </TabPane>
      </Tabs>

      {/* Upgrade Modal */}
      <Modal
        title="Upgrade Subscription"
        open={upgradeModalOpen}
        onOk={handleConfirmUpgrade}
        onCancel={() => setUpgradeModalOpen(false)}
        confirmLoading={loading}
      >
        <Alert
          message={`Upgrade to ${selectedPlan.toUpperCase()} plan`}
          description={
            selectedPlan === 'enterprise'
              ? 'Contact our sales team for enterprise pricing.'
              : `You will be charged $${planPricing[selectedPlan as keyof typeof planPricing]?.price}/${planPricing[selectedPlan as keyof typeof planPricing]?.period}.`
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form layout="vertical">
          <Form.Item label="Billing Period">
            <Radio.Group defaultValue="monthly">
              <Radio value="monthly">Monthly</Radio>
              <Radio value="yearly">Yearly (Save 20%)</Radio>
            </Radio.Group>
          </Form.Item>

          {selectedPlan !== 'free' && selectedPlan !== 'enterprise' && (
            <Form.Item label="Payment Method">
              <Select placeholder="Select payment method">
                <Select.Option value="new">+ Add new card</Select.Option>
              </Select>
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default BillingPage;
