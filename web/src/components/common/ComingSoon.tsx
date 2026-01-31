import React from 'react';
import { Result } from 'antd';
import { ToolOutlined } from '@ant-design/icons';

interface Props {
  title: string;
  description?: string;
}

const ComingSoon: React.FC<Props> = ({ title, description }) => (
  <Result
    icon={<ToolOutlined />}
    title={title}
    subTitle={description || '该功能正在开发中，敬请期待...'}
  />
);

export default ComingSoon;
