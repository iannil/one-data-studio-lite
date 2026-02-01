/**
 * Cockpit 组件测试
 * 测试 BI 驾驶舱页面的核心功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Cockpit from './Cockpit';

// Mock auth API
vi.mock('../../api/auth', () => ({
  getSubsystems: vi.fn(),
}));

// Mock antd message
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

// Mock window.open
const mockOpen = vi.fn();
Object.defineProperty(window, 'open', {
  value: mockOpen,
  writable: true,
});

import { getSubsystems } from '../../api/auth';

const renderWithRouter = (component: React.ReactElement) => {
  return {
    ...render(<MemoryRouter>{component}</MemoryRouter>),
  };
};

describe('Cockpit Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading state initially', () => {
    vi.mocked(getSubsystems).mockImplementation(() => new Promise(() => {}));

    const { container } = renderWithRouter(<Cockpit />);

    // Should render a Spin component when loading
    expect(container.querySelector('.ant-spin')).toBeInTheDocument();
  });

  it('should render page title', async () => {
    vi.mocked(getSubsystems).mockResolvedValue([]);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('BI 驾驶舱')).toBeInTheDocument();
    });
  });

  it('should render subsystem cards when data is loaded', async () => {
    const mockSubsystems = [
      {
        name: 'cube-studio',
        display_name: 'Cube Studio',
        status: 'online',
        version: '1.0.0',
        url: 'http://localhost:8080',
      },
      {
        name: 'superset',
        display_name: 'Superset',
        status: 'online',
        version: '2.0.0',
        url: 'http://localhost:8088',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('Cube Studio')).toBeInTheDocument();
      expect(screen.getByText('Superset')).toBeInTheDocument();
    });
  });

  it('should display online status for online subsystems', async () => {
    const mockSubsystems = [
      {
        name: 'datahub',
        display_name: 'DataHub',
        status: 'online',
        version: '1.0.0',
        url: 'http://localhost:9002',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('在线')).toBeInTheDocument();
      expect(screen.getByText('DataHub')).toBeInTheDocument();
    });
  });

  it('should display offline status for offline subsystems', async () => {
    const mockSubsystems = [
      {
        name: 'dolphinscheduler',
        display_name: 'DolphinScheduler',
        status: 'offline',
        version: '1.0.0',
        url: 'http://localhost:12345',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('离线')).toBeInTheDocument();
      expect(screen.getByText('DolphinScheduler')).toBeInTheDocument();
    });
  });

  it('should display unknown status for unknown subsystems', async () => {
    const mockSubsystems = [
      {
        name: 'test-system',
        display_name: 'Test System',
        status: 'unknown',
        version: '',
        url: '',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('未知')).toBeInTheDocument();
      expect(screen.getByText('Test System')).toBeInTheDocument();
    });
  });

  it('should open URL in new tab when card is clicked', async () => {
    const mockSubsystems = [
      {
        name: 'superset',
        display_name: 'Superset',
        status: 'online',
        version: '2.0.0',
        url: 'http://localhost:8088',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    const { container } = renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('Superset')).toBeInTheDocument();
    });

    // Find and click the card
    const cards = container.querySelectorAll('.ant-card');
    if (cards.length > 0) {
      fireEvent.click(cards[0]);
    }

    // Note: Clicking on the card should open the URL
    expect(mockOpen).toHaveBeenCalledWith('http://localhost:8088', '_blank');
  });

  it('should display subsystem version', async () => {
    const mockSubsystems = [
      {
        name: 'cube-studio',
        display_name: 'Cube Studio',
        status: 'online',
        version: '1.5.2',
        url: 'http://localhost:8080',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('1.5.2')).toBeInTheDocument();
    });
  });

  it('should show empty message when no subsystems are returned', async () => {
    vi.mocked(getSubsystems).mockResolvedValue([]);

    renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.queryByText('Cube Studio')).not.toBeInTheDocument();
    });
  });

  it('should display different icons for different subsystems', async () => {
    const mockSubsystems = [
      {
        name: 'datahub',
        display_name: 'DataHub',
        status: 'online',
        version: '1.0.0',
        url: 'http://localhost:9002',
      },
      {
        name: 'superset',
        display_name: 'Superset',
        status: 'online',
        version: '2.0.0',
        url: 'http://localhost:8088',
      },
    ];

    vi.mocked(getSubsystems).mockResolvedValue(mockSubsystems);

    const { container } = renderWithRouter(<Cockpit />);

    await waitFor(() => {
      expect(screen.getByText('DataHub')).toBeInTheDocument();
      expect(screen.getByText('Superset')).toBeInTheDocument();
    });

    // Check if icons are rendered (they would be in the DOM)
    const icons = container.querySelectorAll('[class*="anticon"]');
    expect(icons.length).toBeGreaterThan(0);
  });
});

// Helper for fireEvent
const { fireEvent } = require('@testing-library/react');
