'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spin } from 'antd';
import { useAuthStore } from '@/stores/auth';
import MainLayout from './MainLayout';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading, loadUser, token } = useAuthStore();

  useEffect(() => {
    if (token) {
      loadUser();
    }
  }, [token, loadUser]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !token) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, token, router]);

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <MainLayout>{children}</MainLayout>;
}
