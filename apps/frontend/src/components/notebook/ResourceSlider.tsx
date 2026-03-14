/**
 * Resource Slider Component
 *
 * Allows users to select CPU and memory resources for their notebook.
 */

import React from 'react';
import { Card, Col, Row, Slider, Space, Typography, Tag, Switch } from 'antd';
import { ThunderboltOutlined, DatabaseOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface ResourceSliderProps {
  cpuValue?: number;
  memValue?: number;
  gpuValue?: number;
  onCpuChange?: (value: number) => void;
  onMemChange?: (value: number) => void;
  onGpuChange?: (value: number) => void;
  cpuMax?: number;
  memMax?: number;
  gpuMax?: number;
  gpuAvailable?: boolean;
  disabled?: boolean;
}

const ResourceSlider: React.FC<ResourceSliderProps> = ({
  cpuValue = 2,
  memValue = 4,
  gpuValue = 0,
  onCpuChange,
  onMemChange,
  onGpuChange,
  cpuMax = 16,
  memMax = 32,
  gpuMax = 4,
  gpuAvailable = false,
  disabled = false,
}) => {
  const memMarks = {
    1: '1G',
    2: '2G',
    4: '4G',
    8: '8G',
    16: '16G',
    32: '32G',
  };

  const cpuMarks = {
    0.5: '0.5',
    1: '1',
    2: '2',
    4: '4',
    8: '8',
    16: '16',
  };

  return (
    <Card
      title="Resource Configuration"
      size="small"
      style={{ width: '100%' }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* CPU Slider */}
        <div>
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <ThunderboltOutlined />
                <Text strong>CPU Cores</Text>
              </Space>
            </Col>
            <Col>
              <Tag color="blue">{cpuValue} CPU</Tag>
            </Col>
          </Row>
          <Slider
            min={0.5}
            max={cpuMax}
            step={0.5}
            value={cpuValue}
            onChange={(value) => onCpuChange?.(value as number)}
            marks={cpuMarks}
            disabled={disabled}
            style={{ marginTop: '8px' }}
          />
        </div>

        {/* Memory Slider */}
        <div>
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <DatabaseOutlined />
                <Text strong>Memory</Text>
              </Space>
            </Col>
            <Col>
              <Tag color="green">{memValue}G RAM</Tag>
            </Col>
          </Row>
          <Slider
            min={1}
            max={memMax}
            step={1}
            value={memValue}
            onChange={(value) => onMemChange?.(value as number)}
            marks={memMarks}
            disabled={disabled}
            style={{ marginTop: '8px' }}
          />
        </div>

        {/* GPU Slider */}
        {gpuAvailable && (
          <div>
            <Row justify="space-between" align="middle">
              <Col>
                <Space>
                  <span style={{ fontSize: '16px' }}>🎮</span>
                  <Text strong>GPU</Text>
                </Space>
              </Col>
              <Col>
                <Tag color="purple">{gpuValue} GPU</Tag>
              </Col>
            </Row>
            <Slider
              min={0}
              max={gpuMax}
              step={1}
              value={gpuValue}
              onChange={(value) => onGpuChange?.(value as number)}
              marks={{
                0: 'None',
                1: '1',
                2: '2',
                4: '4',
              }}
              disabled={disabled}
              style={{ marginTop: '8px' }}
            />
            {gpuValue > 0 && (
              <Text type="secondary" style={{ fontSize: '12px' }}>
                Note: GPU resources are limited. Your notebook may take longer to start
                if GPU resources are not immediately available.
              </Text>
            )}
          </div>
        )}

        {!gpuAvailable && (
          <div style={{ padding: '12px', background: '#fff7e6', borderRadius: '4px' }}>
            <Text type="warning">
              ⚠️ GPU resources are not currently available in this cluster. Contact
              your administrator to enable GPU support.
            </Text>
          </div>
        )}
      </Space>
    </Card>
  );
};

export default ResourceSlider;
