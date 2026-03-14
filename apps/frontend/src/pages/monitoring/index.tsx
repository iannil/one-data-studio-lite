/**
 * Enterprise Monitoring Dashboard Page
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Alert as AntAlert,
  Button,
  Tag,
  Tabs,
  List,
  Space,
  Badge,
  Progress,
  Select,
  Tooltip,
  Typography,
  Spin,
} from 'antd';
import {
  AlertOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  FireOutlined,
  BellOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { useMonitoringStore } from '@/stores/monitoring';
import styles from './monitoring.module.scss';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  suffix?: string;
  prefix?: React.ReactNode;
  status?: 'success' | 'warning' | 'exception' | 'normal';
  precision?: number;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  suffix,
  prefix,
  status = 'normal',
  precision = 1,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return '#52c41a';
      case 'warning':
        return '#faad14';
      case 'exception':
        return '#f5222d';
      default:
        return undefined;
    }
  };

  return (
    <Card className={styles.metricCard}>
      <Statistic
        title={<Text type="secondary">{title}</Text>}
        value={value}
        precision={precision}
        suffix={suffix || unit}
        prefix={prefix}
        valueStyle={{ color: getStatusColor() }}
      />
    </Card>
  );
};

interface GPUMetricCardProps {
  gpuId: string;
  usage: number;
  memoryUsage: number;
  temperature: number;
}

const GPUMetricCard: React.FC<GPUMetricCardProps> = ({
  gpuId,
  usage,
  memoryUsage,
  temperature,
}) => {
  const getTempStatus = () => {
    if (temperature > 85) return 'exception';
    if (temperature > 70) return 'warning';
    return 'success';
  };

  return (
    <Card className={styles.gpuCard} size="small">
      <div className={styles.gpuHeader}>
        <Text strong>GPU {gpuId}</Text>
        <Tag color={getTempStatus() === 'exception' ? 'red' : getTempStatus() === 'warning' ? 'orange' : 'green'}>
          {temperature}°C
        </Tag>
      </div>
      <div className={styles.gpuMetrics}>
        <div className={styles.gpuMetric}>
          <Text type="secondary" className={styles.metricLabel}>Utilization</Text>
          <Progress
            type="circle"
            size={60}
            percent={usage}
            strokeColor={usage > 90 ? '#f5222d' : usage > 70 ? '#faad14' : '#52c41a'}
          />
        </div>
        <div className={styles.gpuMetric}>
          <Text type="secondary" className={styles.metricLabel}>Memory</Text>
          <Progress
            type="circle"
            size={60}
            percent={memoryUsage}
            strokeColor={memoryUsage > 90 ? '#f5222d' : memoryUsage > 70 ? '#faad14' : '#52c41a'}
          />
        </div>
      </div>
    </Card>
  );
};

interface AlertListItemProps {
  alert: {
    id: string;
    rule_name: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
    message: string;
    started_at: string;
    labels: Record<string, string>;
    firing: boolean;
  };
  onResolve: (id: string) => void;
  onSilence: (id: string) => void;
}

const AlertListItem: React.FC<AlertListItemProps> = ({ alert, onResolve, onSilence }) => {
  const getSeverityColor = () => {
    switch (alert.severity) {
      case 'critical':
        return '#f5222d';
      case 'error':
        return '#ff4d4f';
      case 'warning':
        return '#faad14';
      default:
        return '#1890ff';
    }
  };

  const getSeverityIcon = () => {
    switch (alert.severity) {
      case 'critical':
      case 'error':
        return <FireOutlined style={{ color: getSeverityColor() }} />;
      case 'warning':
        return <WarningOutlined style={{ color: getSeverityColor() }} />;
      default:
        return <AlertOutlined style={{ color: getSeverityColor() }} />;
    }
  };

  return (
    <List.Item
      actions={[
        <Button key="silence" size="small" onClick={() => onSilence(alert.id)}>
          Silence
        </Button>,
        <Button key="resolve" size="small" type="primary" onClick={() => onResolve(alert.id)}>
          Resolve
        </Button>,
      ]}
    >
      <List.Item.Meta
        avatar={getSeverityIcon()}
        title={
          <Space>
            <span>{alert.rule_name}</span>
            <Tag color={alert.severity === 'critical' ? 'red' : alert.severity === 'warning' ? 'orange' : 'blue'}>
              {alert.severity.toUpperCase()}
            </Tag>
            <Badge status={alert.firing ? 'error' : 'success'} text={alert.firing ? 'Firing' : 'Resolved'} />
          </Space>
        }
        description={
          <div>
            <div>{alert.message}</div>
            {Object.keys(alert.labels).length > 0 && (
              <div className={styles.alertLabels}>
                {Object.entries(alert.labels).map(([key, value]) => (
                  <Tag key={key} className={styles.labelTag}>
                    {key}={value}
                  </Tag>
                ))}
              </div>
            )}
            <Text type="secondary" className={styles.alertTime}>
              Started at {new Date(alert.started_at).toLocaleString()}
            </Text>
          </div>
        }
      />
    </List.Item>
  );
};

const MonitoringDashboard: React.FC = () => {
  const {
    systemMetrics,
    alerts,
    alertsLoading,
    rules,
    rulesLoading,
    fetchSystemMetrics,
    fetchAlerts,
    fetchRules,
    resolveAlert,
    silenceAlert,
  } = useMonitoringStore();

  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    // Initial load
    fetchSystemMetrics();
    fetchAlerts();
    fetchRules();

    // Set up polling interval
    const interval = setInterval(() => {
      fetchSystemMetrics();
      fetchAlerts();
    }, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, [fetchSystemMetrics, fetchAlerts, fetchRules]);

  const handleRefresh = () => {
    fetchSystemMetrics();
    fetchAlerts();
    fetchRules();
  };

  const handleResolveAlert = async (id: string) => {
    try {
      await resolveAlert(id);
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const handleSilenceAlert = async (id: string) => {
    try {
      await silenceAlert(id, 60); // Silence for 60 minutes
    } catch (error) {
      console.error('Failed to silence alert:', error);
    }
  };

  const firingAlerts = alerts.filter((a) => a.firing);
  const criticalAlerts = firingAlerts.filter((a) => a.severity === 'critical' || a.severity === 'error');
  const warningAlerts = firingAlerts.filter((a) => a.severity === 'warning');

  return (
    <div className={styles.monitoringDashboard}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <Title level={2}>
            <CloudServerOutlined className={styles.titleIcon} />
            Enterprise Monitoring
          </Title>
          <Text type="secondary">Real-time system monitoring and alerting</Text>
        </div>
        <Space>
          <Select
            defaultValue="1h"
            style={{ width: 120 }}
            onChange={setTimeRange}
            options={[
              { label: 'Last 15m', value: '15m' },
              { label: 'Last 1h', value: '1h' },
              { label: 'Last 6h', value: '6h' },
              { label: 'Last 24h', value: '24h' },
            ]}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={alertsLoading}
          >
            Refresh
          </Button>
        </Space>
      </div>

      {/* Alert Summary Banner */}
      {criticalAlerts.length > 0 && (
        <AntAlert
          message="Critical Alerts Active"
          description={`You have ${criticalAlerts.length} critical alert(s) requiring immediate attention.`}
          type="error"
          showIcon
          closable
          className={styles.alertBanner}
          icon={<FireOutlined />}
        />
      )}

      {criticalAlerts.length === 0 && warningAlerts.length > 0 && (
        <AntAlert
          message="Warning Alerts Active"
          description={`You have ${warningAlerts.length} warning alert(s).`}
          type="warning"
          showIcon
          closable
          className={styles.alertBanner}
        />
      )}

      {/* Summary Statistics */}
      <Row gutter={16} className={styles.summaryRow}>
        <Col span={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title={<Text type="secondary">Active Alerts</Text>}
              value={firingAlerts.length}
              prefix={<AlertOutlined />}
              valueStyle={{ color: firingAlerts.length > 0 ? '#f5222d' : undefined }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title={<Text type="secondary">Alert Rules</Text>}
              value={rules.length}
              prefix={<BellOutlined />}
              suffix={`/ ${rules.filter((r) => r.enabled).length} enabled`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title={<Text type="secondary">System Health</Text>}
              value={firingAlerts.length === 0 ? 'Good' : 'Degraded'}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: firingAlerts.length === 0 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className={styles.summaryCard}>
            <Statistic
              title={<Text type="secondary">Last Update</Text>}
              value={new Date().toLocaleTimeString()}
              valueStyle={{ fontSize: '1.2rem' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content Tabs */}
      <Tabs defaultActiveKey="metrics" className={styles.contentTabs}>
        <TabPane
          tab={
            <span>
              <ThunderboltOutlined />
              System Metrics
            </span>
          }
          key="metrics"
        >
          {systemMetrics ? (
            <>
              {/* CPU Metrics */}
              <Card title="CPU Usage" className={styles.sectionCard} extra={<Tag color={systemMetrics.cpu.usage_percent > 90 ? 'red' : systemMetrics.cpu.usage_percent > 70 ? 'orange' : 'green'}>
                {systemMetrics.cpu.usage_percent.toFixed(1)}%
              </Tag>}>
                <Row gutter={16}>
                  <Col span={8}>
                    <MetricCard
                      title="CPU Usage"
                      value={systemMetrics.cpu.usage_percent}
                      unit="%"
                      status={systemMetrics.cpu.usage_percent > 90 ? 'exception' : systemMetrics.cpu.usage_percent > 70 ? 'warning' : 'success'}
                      prefix={<ThunderboltOutlined />}
                    />
                  </Col>
                  <Col span={8}>
                    <MetricCard
                      title="CPU Cores"
                      value={systemMetrics.cpu.cores}
                      unit="cores"
                    />
                  </Col>
                  <Col span={8}>
                    <Card className={styles.metricCard}>
                      <Progress
                        type="dashboard"
                        percent={Math.round(systemMetrics.cpu.usage_percent)}
                        strokeColor={systemMetrics.cpu.usage_percent > 90 ? '#f5222d' : systemMetrics.cpu.usage_percent > 70 ? '#faad14' : '#52c41a'}
                      />
                    </Card>
                  </Col>
                </Row>
              </Card>

              {/* Memory Metrics */}
              <Card title="Memory Usage" className={styles.sectionCard} extra={<Tag color={systemMetrics.memory.usage_percent > 90 ? 'red' : systemMetrics.memory.usage_percent > 70 ? 'orange' : 'green'}>
                {systemMetrics.memory.usage_percent.toFixed(1)}%
              </Tag>}>
                <Row gutter={16}>
                  <Col span={8}>
                    <MetricCard
                      title="Memory Usage"
                      value={systemMetrics.memory.usage_percent}
                      unit="%"
                      status={systemMetrics.memory.usage_percent > 90 ? 'exception' : systemMetrics.memory.usage_percent > 70 ? 'warning' : 'success'}
                    />
                  </Col>
                  <Col span={8}>
                    <MetricCard
                      title="Used Memory"
                      value={systemMetrics.memory.used_bytes / 1024 / 1024 / 1024}
                      unit="GB"
                      precision={2}
                    />
                  </Col>
                  <Col span={8}>
                    <MetricCard
                      title="Total Memory"
                      value={systemMetrics.memory.total_bytes / 1024 / 1024 / 1024}
                      unit="GB"
                      precision={2}
                    />
                  </Col>
                </Row>
                <div className={styles.memoryProgress}>
                  <Progress
                    percent={Math.round(systemMetrics.memory.usage_percent)}
                    strokeColor={systemMetrics.memory.usage_percent > 90 ? '#f5222d' : systemMetrics.memory.usage_percent > 70 ? '#faad14' : '#52c41a'}
                    status={systemMetrics.memory.usage_percent > 90 ? 'exception' : systemMetrics.memory.usage_percent > 70 ? 'warning' : 'success'}
                  />
                </div>
              </Card>

              {/* Database Metrics */}
              <Card title="Database Connections" className={styles.sectionCard} extra={<DatabaseOutlined />}>
                <Row gutter={16}>
                  <Col span={8}>
                    <MetricCard
                      title="Total Connections"
                      value={systemMetrics.database.connections_total}
                      unit="connections"
                    />
                  </Col>
                  <Col span={8}>
                    <MetricCard
                      title="Active Connections"
                      value={systemMetrics.database.connections_in_use}
                      unit="connections"
                      status={systemMetrics.database.connections_in_use / systemMetrics.database.connections_total > 0.8 ? 'warning' : 'success'}
                    />
                  </Col>
                  <Col span={8}>
                    <MetricCard
                      title="Idle Connections"
                      value={systemMetrics.database.connections_idle}
                      unit="connections"
                    />
                  </Col>
                </Row>
              </Card>

              {/* GPU Metrics */}
              {systemMetrics.gpu.length > 0 && (
                <Card title="GPU Status" className={styles.sectionCard}>
                  <Row gutter={16}>
                    {systemMetrics.gpu.map((gpu) => (
                      <Col span={6} key={gpu.gpu_id}>
                        <GPUMetricCard
                          gpuId={gpu.gpu_id}
                          usage={gpu.usage_percent}
                          memoryUsage={gpu.memory_usage_percent}
                          temperature={gpu.temperature_celsius}
                        />
                      </Col>
                    ))}
                  </Row>
                </Card>
              )}
            </>
          ) : (
            <div className={styles.loadingContainer}>
              <Spin size="large" tip="Loading metrics..." />
            </div>
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <AlertOutlined />
              Active Alerts
              {firingAlerts.length > 0 && <Badge count={firingAlerts.length} offset={[10, 0]} />}
            </span>
          }
          key="alerts"
        >
          {alertsLoading ? (
            <div className={styles.loadingContainer}>
              <Spin size="large" tip="Loading alerts..." />
            </div>
          ) : firingAlerts.length === 0 ? (
            <Card className={styles.emptyState}>
              <CheckCircleOutlined className={styles.emptyIcon} />
              <Title level={4}>No Active Alerts</Title>
              <Text type="secondary">All systems are operating normally</Text>
            </Card>
          ) : (
            <List
              className={styles.alertsList}
              itemLayout="horizontal"
              dataSource={firingAlerts}
              renderItem={(alert) => (
                <AlertListItem
                  key={alert.id}
                  alert={alert}
                  onResolve={handleResolveAlert}
                  onSilence={handleSilenceAlert}
                />
              )}
            />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <BellOutlined />
              Alert Rules
            </span>
          }
          key="rules"
        >
          <List
            className={styles.rulesList}
            itemLayout="horizontal"
            dataSource={rules}
            renderItem={(rule) => (
              <List.Item
                actions={[
                  <Tag key="state" color={rule.enabled ? 'green' : 'default'}>
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </Tag>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <span>{rule.name}</span>
                      <Tag color={
                        rule.severity === 'critical' ? 'red' :
                        rule.severity === 'error' ? 'orange' :
                        rule.severity === 'warning' ? 'gold' : 'blue'
                      }>
                        {rule.severity}
                      </Tag>
                    </Space>
                  }
                  description={
                    <div>
                      <div>{rule.description}</div>
                      <Text type="secondary">
                        Evaluates every {rule.evaluation_interval_seconds}s |{' '}
                        {rule.conditions.length} condition(s) |{' '}
                        {rule.state === 'firing' ? (
                          <Badge status="error" text="Firing" />
                        ) : (
                          <Badge status="default" text={rule.state} />
                        )}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default MonitoringDashboard;
