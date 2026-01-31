import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Tag, Spin, message, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  SafetyOutlined,
  ApiOutlined,
  RobotOutlined,
  ScheduleOutlined,
} from '@ant-design/icons';
import { getSubsystems } from '../../api/auth';
import { Subsystem } from '../../types';

const { Title, Text } = Typography;

const iconMap: Record<string, React.ReactNode> = {
  'cube-studio': <RobotOutlined style={{ fontSize: 32 }} />,
  'superset': <BarChartOutlined style={{ fontSize: 32 }} />,
  'datahub': <DatabaseOutlined style={{ fontSize: 32 }} />,
  'dolphinscheduler': <ScheduleOutlined style={{ fontSize: 32 }} />,
  'hop': <ApiOutlined style={{ fontSize: 32 }} />,
  'seatunnel': <ApiOutlined style={{ fontSize: 32 }} />,
  'shardingsphere': <SafetyOutlined style={{ fontSize: 32 }} />,
};

const statusConfig = {
  online: { color: 'success', icon: <CheckCircleOutlined />, text: '在线' },
  offline: { color: 'error', icon: <CloseCircleOutlined />, text: '离线' },
  unknown: { color: 'default', icon: <QuestionCircleOutlined />, text: '未知' },
};

const Dashboard: React.FC = () => {
  const [subsystems, setSubsystems] = useState<Subsystem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSubsystems = async () => {
      try {
        const data = await getSubsystems();
        setSubsystems(data);
      } catch (error) {
        message.error('获取子系统状态失败');
      } finally {
        setLoading(false);
      }
    };
    fetchSubsystems();
  }, []);

  const handleCardClick = (url: string) => {
    if (url) {
      window.open(url, '_blank');
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>子系统导航</Title>
      <Row gutter={[16, 16]}>
        {subsystems.map((system) => {
          const status = statusConfig[system.status] || statusConfig.unknown;
          return (
            <Col xs={24} sm={12} md={8} lg={6} key={system.name}>
              <Card
                hoverable
                onClick={() => handleCardClick(system.url)}
                style={{ height: '100%' }}
              >
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: '#1890ff', marginBottom: 16 }}>
                    {iconMap[system.name] || <ApiOutlined style={{ fontSize: 32 }} />}
                  </div>
                  <Title level={5} style={{ marginBottom: 8 }}>
                    {system.display_name}
                  </Title>
                  <div style={{ marginBottom: 8 }}>
                    <Tag color={status.color as any} icon={status.icon}>
                      {status.text}
                    </Tag>
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {system.version || '-'}
                  </Text>
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

export default Dashboard;
