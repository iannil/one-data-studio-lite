import React from 'react';
import { ConfigProvider, App } from 'antd';
import zhCN from 'antd/locale/zh_CN';

interface ProvidersProps {
  children: React.ReactNode;
}

export default function Providers({ children }: ProvidersProps) {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677ff',
        },
      }}
    >
      <App>{children}</App>
    </ConfigProvider>
  );
}
