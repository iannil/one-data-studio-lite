/**
 * Image Selector Component
 *
 * Allows users to select a notebook image template.
 */

import React from 'react';
import { Card, Radio, Space, Tag, Typography, Tooltip } from 'antd';
import {
  CodeOutlined,
  RocketOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type { NotebookImage } from '@/types/notebook';

const { Text } = Typography;

interface ImageSelectorProps {
  images: NotebookImage[];
  value?: string;
  onChange?: (imageId: string) => void;
  gpuAvailable?: boolean;
  disabled?: boolean;
}

const ImageSelector: React.FC<ImageSelectorProps> = ({
  images,
  value,
  onChange,
  gpuAvailable = false,
  disabled = false,
}) => {
  const filteredImages = gpuAvailable
    ? images
    : images.filter((img) => !img.gpu_required);

  const getImageIcon = (image: NotebookImage) => {
    const icons: Record<string, React.ReactNode> = {
      pytorch: <RocketOutlined style={{ color: '#EE4C2C' }} />,
      tensorflow: <RocketOutlined style={{ color: '#FF6F00' }} />,
      sklearn: <CodeOutlined style={{ color: '#F7931E' }} />,
      nlp: <CodeOutlined style={{ color: '#76B900' }} />,
      minimal: <CodeOutlined />,
    };
    return icons[image.id] || <CodeOutlined />;
  };

  return (
    <Radio.Group
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      disabled={disabled}
      style={{ width: '100%' }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {filteredImages.map((image) => (
          <Radio
            key={image.id}
            value={image.id}
            style={{ display: 'block', width: '100%' }}
            disabled={disabled}
          >
            <Card
              size="small"
              style={{
                width: '100%',
                borderColor: value === image.id ? '#1890ff' : undefined,
                background: value === image.id ? '#f0f5ff' : undefined,
              }}
              bodyStyle={{ padding: '12px' }}
            >
              <Space>
                <Radio
                  value={image.id}
                  checked={value === image.id}
                  disabled={disabled}
                >
                  {getImageIcon(image)}
                </Radio>
                <div style={{ flex: 1 }}>
                  <Space>
                    <Text strong>{image.name}</Text>
                    {image.default && (
                      <Tag color="blue" size="small">
                        Default
                      </Tag>
                    )}
                    {image.gpu_required && (
                      <Tag color="purple" size="small">
                        GPU Required
                      </Tag>
                    )}
                    {image.gpu_recommended && !image.gpu_required && (
                      <Tag color="cyan" size="small">
                        GPU Recommended
                      </Tag>
                    )}
                    {image.id === value && !gpuAvailable && image.gpu_recommended && (
                      <Tooltip title="This image works best with GPU">
                        <Tag color="warning" size="small" icon={<QuestionCircleOutlined />}>
                          GPU Recommended
                        </Tag>
                      </Tooltip>
                    )}
                  </Space>
                  <div style={{ marginTop: '4px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {image.description}
                    </Text>
                  </div>
                  {image.packages && image.packages.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <Space size="small" wrap>
                        {image.packages.slice(0, 5).map((pkg) => (
                          <Tag key={pkg} style={{ fontSize: '11px' }}>
                            {pkg}
                          </Tag>
                        ))}
                        {image.packages.length > 5 && (
                          <Tag style={{ fontSize: '11px' }}>
                            +{image.packages.length - 5} more
                          </Tag>
                        )}
                      </Space>
                    </div>
                  )}
                </div>
              </Space>
            </Card>
          </Radio>
        ))}
      </Space>
    </Radio.Group>
  );
};

export default ImageSelector;
