/**
 * Cluster Management Page
 *
 * Manage multiple Kubernetes clusters for workload distribution.
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
  Modal,
  Form,
  Input,
  Select,
  Alert,
  Descriptions,
  Typography,
  Divider,
  List,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  SettingOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Option } = Select;
const { Text } = Typography;

interface Cluster {
  id: string;
  name: string;
  type: 'managed' | 'attached' | 'hybrid';
  status: 'active' | 'degraded' | 'maintenance' | 'unreachable';
  region: string;
  kubernetes_version: string;
  node_count: number;
  cpu_capacity: number;
  memory_capacity_gb: number;
  gpu_capacity: number;
  utilization: {
    cpu_percent: number;
    memory_percent: number;
    gpu_percent: number;
  };
  tags: string[];
}

interface NodePool {
  id: string;
  name: string;
  instance_type: string;
  node_count: number;
  cpu_per_node: number;
  memory_per_node_gb: number;
  gpu_per_node: number;
  phase: string;
}

const ClusterPage: React.FC = () => {
  const [form] = Form.useForm();
  const [nodePoolForm] = Form.useForm();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [nodePoolModalOpen, setNodePoolModalOpen] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [loading, setLoading] = useState(false);

  // Mock data
  const [clusters, setClusters] = useState<Cluster[]>([
    {
      id: 'cluster_001',
      name: 'production-us-west',
      type: 'managed',
      status: 'active',
      region: 'us-west-2',
      kubernetes_version: 'v1.28.0',
      node_count: 12,
      cpu_capacity: 192,
      memory_capacity_gb: 768,
      gpu_capacity: 8,
      utilization: { cpu_percent: 65, memory_percent: 72, gpu_percent: 45 },
      tags: ['gpu', 'production'],
    },
    {
      id: 'cluster_002',
      name: 'development-us-east',
      type: 'managed',
      status: 'active',
      region: 'us-east-1',
      kubernetes_version: 'v1.27.3',
      node_count: 6,
      cpu_capacity: 96,
      memory_capacity_gb: 384,
      gpu_capacity: 2,
      utilization: { cpu_percent: 35, memory_percent: 48, gpu_percent: 20 },
      tags: ['development'],
    },
    {
      id: 'cluster_003',
      name: 'inference-eu-central',
      type: 'attached',
      status: 'degraded',
      region: 'eu-central-1',
      kubernetes_version: 'v1.28.0',
      node_count: 8,
      cpu_capacity: 128,
      memory_capacity_gb: 512,
      gpu_capacity: 16,
      utilization: { cpu_percent: 82, memory_percent: 88, gpu_percent: 75 },
      tags: ['gpu', 'inference'],
    },
  ]);

  const nodePools: NodePool[] = [
    {
      id: 'pool_001',
      name: 'gpu-pool-a100',
      instance_type: 'p4d.24xlarge',
      node_count: 4,
      cpu_per_node: 96,
      memory_per_node_gb: 384,
      gpu_per_node: 8,
      phase: 'Running',
    },
    {
      id: 'pool_002',
      name: 'cpu-pool-general',
      instance_type: 'c5.4xlarge',
      node_count: 6,
      cpu_per_node: 16,
      memory_per_node_gb: 32,
      gpu_per_node: 0,
      phase: 'Running',
    },
  ];

  const clusterColumns: ColumnsType<Cluster> = [
    {
      title: 'Cluster',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Cluster) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.id}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'managed' ? 'blue' : 'green'}>{type}</Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
          active: { color: 'success', icon: <CheckCircleOutlined /> },
          degraded: { color: 'warning', icon: <ExclamationCircleOutlined /> },
          maintenance: { color: 'default', icon: <SettingOutlined /> },
          unreachable: { color: 'error', icon: <CloseCircleOutlined /> },
        };
        const config = statusConfig[status] || statusConfig.active;
        return (
          <Tag color={config.color} icon={config.icon}>
            {status.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'Region',
      dataIndex: 'region',
      key: 'region',
    },
    {
      title: 'Nodes',
      dataIndex: 'node_count',
      key: 'node_count',
      render: (count: number) => <Text>{count} nodes</Text>,
    },
    {
      title: 'Utilization',
      key: 'utilization',
      render: (_: any, record: Cluster) => (
        <Space direction="vertical" size={4} style={{ width: 120 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span>CPU</span>
            <span>{record.utilization.cpu_percent}%</span>
          </div>
          <Progress
            percent={record.utilization.cpu_percent}
            size="small"
            showInfo={false}
            status={record.utilization.cpu_percent > 80 ? 'exception' : 'normal'}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span>Memory</span>
            <span>{record.utilization.memory_percent}%</span>
          </div>
          <Progress
            percent={record.utilization.memory_percent}
            size="small"
            showInfo={false}
            status={record.utilization.memory_percent > 80 ? 'exception' : 'normal'}
          />
        </Space>
      ),
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space size={4}>
          {tags.slice(0, 2).map(tag => (
            <Tag key={tag} style={{ fontSize: 11 }}>{tag}</Tag>
          ))}
          {tags.length > 2 && <Tag style={{ fontSize: 11 }}>+{tags.length - 2}</Tag>}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Cluster) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => handleViewCluster(record)}
          >
            View
          </Button>
          <Button
            type="link"
            size="small"
            icon={<SyncOutlined />}
            onClick={() => handleSyncCluster(record.id)}
          >
            Sync
          </Button>
        </Space>
      ),
    },
  ];

  const handleCreateCluster = async () => {
    const values = form.getFieldsValue();
    setLoading(true);
    // In production, call create API
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
    setCreateModalOpen(false);
    form.resetFields();
  };

  const handleViewCluster = (cluster: Cluster) => {
    setSelectedCluster(cluster);
  };

  const handleSyncCluster = async (clusterId: string) => {
    // In production, call sync API
  };

  const handleCreateNodePool = async () => {
    const values = nodePoolForm.getFieldsValue();
    setLoading(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
    setNodePoolModalOpen(false);
    nodePoolForm.resetFields();
  };

  const aggregatedMetrics = {
    total_clusters: clusters.length,
    active_clusters: clusters.filter(c => c.status === 'active').length,
    total_nodes: clusters.reduce((sum, c) => sum + c.node_count, 0),
    total_cpu: clusters.reduce((sum, c) => sum + c.cpu_capacity, 0),
    total_memory_gb: clusters.reduce((sum, c) => sum + c.memory_capacity_gb, 0),
    total_gpu: clusters.reduce((sum, c) => sum + c.gpu_capacity, 0),
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
        <Col flex="auto">
          <h1 style={{ margin: 0 }}>Cluster Management</h1>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            Manage multiple Kubernetes clusters for workload distribution
          </p>
        </Col>
        <Col>
          <Space>
            <Button icon={<SyncOutlined />}>Sync All</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
              Add Cluster
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Aggregated Metrics */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Clusters"
              value={aggregatedMetrics.total_clusters}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Active"
              value={aggregatedMetrics.active_clusters}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Total Nodes"
              value={aggregatedMetrics.total_nodes}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="CPU Capacity"
              value={aggregatedMetrics.total_cpu}
              suffix="cores"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="Memory"
              value={aggregatedMetrics.total_memory_gb}
              suffix="GB"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="GPUs"
              value={aggregatedMetrics.total_gpu}
            />
          </Card>
        </Col>
      </Row>

      {selectedCluster ? (
        // Cluster Detail View
        <Card>
          <Row gutter={16} align="middle" style={{ marginBottom: '24px' }}>
            <Col flex="auto">
              <Space direction="vertical" size={0}>
                <Text strong style={{ fontSize: 18 }}>{selectedCluster.name}</Text>
                <Text type="secondary">{selectedCluster.id}</Text>
              </Space>
            </Col>
            <Col>
              <Button onClick={() => setSelectedCluster(null)}>Back to List</Button>
            </Col>
          </Row>

          <Descriptions column={4} size="small" style={{ marginBottom: '24px' }}>
            <Descriptions.Item label="Status">
              <Tag
                color={selectedCluster.status === 'active' ? 'success' : 'warning'}
                icon={selectedCluster.status === 'active' ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
              >
                {selectedCluster.status.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Type">{selectedCluster.type}</Descriptions.Item>
            <Descriptions.Item label="Region">{selectedCluster.region}</Descriptions.Item>
            <Descriptions.Item label="Version">{selectedCluster.kubernetes_version}</Descriptions.Item>
          </Descriptions>

          <Row gutter={16} style={{ marginBottom: '24px' }}>
            <Col span={16}>
              <Card title="Resource Utilization" size="small">
                <Row gutter={16}>
                  <Col span={8}>
                    <Progress
                      type="circle"
                      percent={selectedCluster.utilization.cpu_percent}
                      format={percent => <span>{percent}%</span>}
                      strokeColor={selectedCluster.utilization.cpu_percent > 80 ? '#cf1322' : '#1890ff'}
                    />
                    <div style={{ textAlign: 'center', marginTop: 8 }}>CPU</div>
                  </Col>
                  <Col span={8}>
                    <Progress
                      type="circle"
                      percent={selectedCluster.utilization.memory_percent}
                      format={percent => <span>{percent}%</span>}
                      strokeColor={selectedCluster.utilization.memory_percent > 80 ? '#cf1322' : '#52c41a'}
                    />
                    <div style={{ textAlign: 'center', marginTop: 8 }}>Memory</div>
                  </Col>
                  {selectedCluster.gpu_capacity > 0 && (
                    <Col span={8}>
                      <Progress
                        type="circle"
                        percent={selectedCluster.utilization.gpu_percent}
                        format={percent => <span>{percent}%</span>}
                        strokeColor={selectedCluster.utilization.gpu_percent > 80 ? '#cf1322' : '#722ed1'}
                      />
                      <div style={{ textAlign: 'center', marginTop: 8 }}>GPU</div>
                    </Col>
                  )}
                </Row>
              </Card>
            </Col>
            <Col span={8}>
              <Card title="Capacity" size="small">
                <Statistic title="Nodes" value={selectedCluster.node_count} />
                <Divider style={{ margin: '12px 0' }} />
                <Statistic title="CPU" value={selectedCluster.cpu_capacity} suffix="cores" />
                <Divider style={{ margin: '12px 0' }} />
                <Statistic title="Memory" value={selectedCluster.memory_capacity_gb} suffix="GB" />
                {selectedCluster.gpu_capacity > 0 && (
                  <>
                    <Divider style={{ margin: '12px 0' }} />
                    <Statistic title="GPU" value={selectedCluster.gpu_capacity} />
                  </>
                )}
              </Card>
            </Col>
          </Row>

          <Card
            title="Node Pools"
            extra={
              <Button size="small" icon={<PlusOutlined />} onClick={() => setNodePoolModalOpen(true)}>
                Add Pool
              </Button>
            }
          >
            <List
              grid={{ gutter: 16, column: 2 }}
              dataSource={nodePools}
              renderItem={pool => (
                <List.Item>
                  <Card size="small" style={{ width: '100%' }}>
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Text strong>{pool.name}</Text>
                      <Tag color={pool.phase === 'Running' ? 'success' : 'processing'}>
                        {pool.phase}
                      </Tag>
                    </Space>
                    <Divider style={{ margin: '8px 0' }} />
                    <Row gutter={8}>
                      <Col span={12}>
                        <Text type="secondary">Instance</Text>
                        <div>{pool.instance_type}</div>
                      </Col>
                      <Col span={12}>
                        <Text type="secondary">Nodes</Text>
                        <div>{pool.node_count}</div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">CPU</Text>
                        <div>{pool.cpu_per_node} cores</div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">Memory</Text>
                        <div>{pool.memory_per_node_gb} GB</div>
                      </Col>
                      <Col span={8}>
                        <Text type="secondary">GPU</Text>
                        <div>{pool.gpu_per_node}</div>
                      </Col>
                    </Row>
                  </Card>
                </List.Item>
              )}
            />
          </Card>
        </Card>
      ) : (
        // Cluster List View
        <Card title="Clusters">
          <Table
            dataSource={clusters}
            columns={clusterColumns}
            rowKey="id"
            pagination={false}
          />
        </Card>
      )}

      {/* Create Cluster Modal */}
      <Modal
        title="Add Cluster"
        open={createModalOpen}
        onOk={handleCreateCluster}
        onCancel={() => setCreateModalOpen(false)}
        confirmLoading={loading}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Cluster Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="my-cluster" />
          </Form.Item>
          <Form.Item
            name="type"
            label="Cluster Type"
            initialValue="managed"
          >
            <Select>
              <Option value="managed">Managed</Option>
              <Option value="attached">Attached</Option>
              <Option value="hybrid">Hybrid</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="region"
            label="Region"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="us-east-1">US East (N. Virginia)</Option>
              <Option value="us-west-2">US West (Oregon)</Option>
              <Option value="eu-west-1">Europe (Ireland)</Option>
              <Option value="eu-central-1">Europe (Frankfurt)</Option>
              <Option value="ap-southeast-1">Asia Pacific (Singapore)</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="api_endpoint"
            label="API Endpoint"
            rules={[{ required: true }]}
          >
            <Input placeholder="https://cluster.example.com" />
          </Form.Item>
          <Form.Item
            name="kubeconfig"
            label="Kubeconfig"
          >
            <Input.TextArea rows={4} placeholder="Paste kubeconfig content..." />
          </Form.Item>
          <Form.Item
            name="tags"
            label="Tags"
          >
            <Select mode="tags" placeholder="Add tags..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Node Pool Modal */}
      <Modal
        title="Add Node Pool"
        open={nodePoolModalOpen}
        onOk={handleCreateNodePool}
        onCancel={() => setNodePoolModalOpen(false)}
        confirmLoading={loading}
      >
        <Form form={nodePoolForm} layout="vertical">
          <Form.Item
            name="name"
            label="Pool Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="gpu-pool" />
          </Form.Item>
          <Form.Item
            name="instance_type"
            label="Instance Type"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="c5.2xlarge">c5.2xlarge (8 vCPU, 16 GB)</Option>
              <Option value="c5.4xlarge">c5.4xlarge (16 vCPU, 32 GB)</Option>
              <Option value="c5.9xlarge">c5.9xlarge (36 vCPU, 72 GB)</Option>
              <Option value="p3.2xlarge">p3.2xlarge (8 vCPU, 61 GB, 1x V100)</Option>
              <Option value="p3.8xlarge">p3.8xlarge (32 vCPU, 244 GB, 4x V100)</Option>
              <Option value="p4d.24xlarge">p4d.24xlarge (96 vCPU, 384 GB, 8x A100)</Option>
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="node_count"
                label="Node Count"
                initialValue={1}
                rules={[{ required: true }]}
              >
                <Input type="number" min={1} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="auto_scaling"
                label="Auto-scaling"
                valuePropName="checked"
              >
                <Select>
                  <Option value="enabled">Enabled</Option>
                  <Option value="disabled">Disabled</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default ClusterPage;
