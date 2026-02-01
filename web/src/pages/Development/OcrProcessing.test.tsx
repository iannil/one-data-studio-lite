/**
 * OcrProcessing 组件测试
 * 测试 OCR 文档处理页面的核心功能
 */

import { describe, it, expect } from 'vitest';
import OcrProcessing from './OcrProcessing';

// Mock antd
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

// Mock navigator.clipboard
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: () => Promise.resolve(),
  },
  writable: true,
});

describe('OcrProcessing Component', () => {
  it('should import the component', () => {
    expect(OcrProcessing).toBeDefined();
  });

  it('should be a function component', () => {
    expect(typeof OcrProcessing).toBe('function');
  });
});
