/**
 * Node Configuration Panel Component
 *
 * Configuration panel for editing DAG node properties.
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Button,
  Space,
  Divider,
  Card,
  Row,
  Col,
  InputNumber,
  Switch,
  Collapse,
  Tag,
} from 'antd';
import { SaveOutlined, PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import type { DAGNode, TaskType } from '@/types/workflow';

const { Panel } = Collapse;

interface NodeConfigPanelProps {
  node: DAGNode;
  taskTypes: TaskType[];
  nodes: DAGNode[];
  onUpdate: (node: DAGNode) => void;
  onClose: () => void;
}

export const NodeConfigPanel: React.FC<NodeConfigPanelProps> = ({
  node,
  taskTypes,
  nodes,
  onUpdate,
  onClose,
}) => {
  const [form] = Form.useForm();
  const [parameters, setParameters] = useState<Record<string, any>>({});

  useEffect(() => {
    form.setFieldsValue({
      name: node.name,
      description: node.config?.description || '',
      retry_count: node.config?.retry_count || 0,
      retry_delay_seconds: node.config?.retry_delay_seconds || 300,
      timeout_seconds: node.config?.timeout_seconds,
      depends_on: node.config?.depends_on || [],
    });
    setParameters(node.config?.parameters || {});
  }, [node]);

  const handleSave = () => {
    const values = form.getFieldsValue();

    const updatedNode: DAGNode = {
      ...node,
      name: values.name,
      config: {
        ...node.config,
        description: values.description,
        retry_count: values.retry_count,
        retry_delay_seconds: values.retry_delay_seconds,
        timeout_seconds: values.timeout_seconds,
        depends_on: values.depends_on,
        parameters,
      },
    };

    onUpdate(updatedNode);
    onClose();
  };

  const availableDependencies = nodes.filter((n) => n.id !== node.id);

  const addParameter = () => {
    const key = `param_${Date.now()}`;
    setParameters({ ...parameters, [key]: '' });
  };

  const removeParameter = (key: string) => {
    const newParams = { ...parameters };
    delete newParams[key];
    setParameters(newParams);
  };

  const updateParameter = (oldKey: string, newKey: string, value: any) => {
    const newParams = { ...parameters };
    delete newParams[oldKey];
    newParams[newKey] = value;
    setParameters(newParams);
  };

  return (
    <div style={{ padding: '16px' }}>
      <Form form={form} layout="vertical">
        <Form.Item
          label="Task Name"
          name="name"
          rules={[{ required: true, message: 'Task name is required' }]}
        >
          <Input placeholder="Enter task name" />
        </Form.Item>

        <Form.Item label="Description" name="description">
          <Input.TextArea rows={3} placeholder="Enter task description" />
        </Form.Item>

        <Collapse
          defaultActiveKey={['retry', 'dependencies', 'parameters']}
          items={[
            {
              key: 'retry',
              label: 'Retry Configuration',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="Retry Count"
                        name="retry_count"
                        style={{ marginBottom: 0 }}
                      >
                        <InputNumber min={0} max={10} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        label="Retry Delay (sec)"
                        name="retry_delay_seconds"
                        style={{ marginBottom: 0 }}
                      >
                        <InputNumber min={0} max={3600} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item label="Timeout (sec)" name="timeout_seconds">
                    <InputNumber
                      min={0}
                      max={86400}
                      placeholder="No timeout"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </>
              ),
            },
            {
              key: 'dependencies',
              label: 'Dependencies',
              children: (
                <Form.Item
                  name="depends_on"
                  label="Select tasks this task depends on"
                  style={{ marginBottom: 0 }}
                >
                  <Select
                    mode="multiple"
                    placeholder="Select dependencies"
                    options={availableDependencies.map((n) => ({
                      label: n.name,
                      value: n.id,
                    }))}
                  />
                </Form.Item>
              ),
            },
            {
              key: 'parameters',
              label: 'Task Parameters',
              children: (
                <>
                  {Object.entries(parameters).map(([key, value]) => (
                    <Row
                      key={key}
                      gutter={8}
                      align="middle"
                      style={{ marginBottom: 8 }}
                    >
                      <Col flex="1">
                        <Input
                          value={key}
                          onChange={(e) =>
                            updateParameter(key, e.target.value, value)
                          }
                          placeholder="Parameter name"
                        />
                      </Col>
                      <Col flex="1">
                        <Input
                          value={value}
                          onChange={(e) =>
                            updateParameter(key, key, e.target.value)
                          }
                          placeholder="Parameter value"
                        />
                      </Col>
                      <Col>
                        <Button
                          type="text"
                          danger
                          size="small"
                          icon={<MinusCircleOutlined />}
                          onClick={() => removeParameter(key)}
                        />
                      </Col>
                    </Row>
                  ))}
                  <Button
                    type="dashed"
                    icon={<PlusOutlined />}
                    onClick={addParameter}
                    block
                  >
                    Add Parameter
                  </Button>
                </>
              ),
            },
          ]}
        />

        <Divider />

        <Space style={{ width: '100%' }}>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            Save Changes
          </Button>
          <Button onClick={onClose}>Cancel</Button>
        </Space>
      </Form>
    </div>
  );
};

export default NodeConfigPanel;
