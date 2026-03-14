/**
 * System Monitoring Page
 *
 * Displays system health, Celery status, and other monitoring information.
 */
import { Tabs } from 'antd';
import { CeleryMonitor } from '../components/CeleryMonitor';

export default function MonitoringPage() {
  const items = [
    {
      key: 'celery',
      label: 'Celery Tasks',
      children: <CeleryMonitor />,
    },
    {
      key: 'system',
      label: 'System Health',
      children: (
        <div style={{ padding: 24 }}>
          <p>System health metrics coming soon...</p>
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1>System Monitoring</h1>
      <Tabs defaultActiveKey="celery" items={items} />
    </div>
  );
}
