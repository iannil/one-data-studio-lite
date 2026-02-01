import React, { useEffect } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, loading, error, isAuthenticated } = useAuthStore();
  const [form] = Form.useForm();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (error) {
      message.error(error);
    }
  }, [error]);

  const onFinish = async (values: { username: string; password: string }) => {
    const success = await login(values.username, values.password);
    if (success) {
      message.success('登录成功');
      navigate('/dashboard');
    }
  };

  return (
    <div
      data-testid="login-page"
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card
        style={{
          width: 400,
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          borderRadius: 12,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 data-testid="login-title" style={{ color: '#1890ff', marginBottom: 8 }}>
            ONE-DATA-STUDIO
          </h1>
          <p style={{ color: '#666' }}>智能大数据平台</p>
        </div>
        <Form
          data-testid="login-form"
          form={form}
          name="login"
          onFinish={onFinish}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              data-testid="username-input"
              prefix={<UserOutlined />}
              placeholder="用户名"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              data-testid="password-input"
              prefix={<LockOutlined />}
              placeholder="密码"
            />
          </Form.Item>
          <Form.Item>
            <Button
              data-testid="login-button"
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              登录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>
          默认账号: admin / admin123
        </div>
      </Card>
    </div>
  );
};

export default Login;
