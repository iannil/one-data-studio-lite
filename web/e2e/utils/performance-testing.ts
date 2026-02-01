/**
 * Performance Testing Utilities
 *
 * Helper functions for performance testing
 */

import { Page, Metrics } from '@playwright/test';

/**
 * Performance metrics
 */
export interface PerformanceMetrics {
  // Timing metrics
  domContentLoaded: number;
  loadComplete: number;
  firstPaint: number;
  firstContentfulPaint: number;
  firstMeaningfulPaint?: number;

  // Resource metrics
  totalRequests: number;
  totalTransferSize: number;
  domSize: number;

  // Navigation timing
  dnsLookup: number;
  tcpConnection: number;
  tlsNegotiation: number;
  requestTime: number;
  responseTime: number;

  // Rendering
  layoutShifts: number;
  layoutShiftScore: number;
  longTasks: number[];
}

/**
 * Navigation timing metrics
 */
export interface NavigationTiming {
  dnsStart: number;
  dnsEnd: number;
  connectStart: number;
  connectEnd: number;
  tlsStart: number;
  tlsEnd: number;
  requestStart: number;
  responseStart: number;
  responseEnd: number;
  domContentLoaded: number;
  loadComplete: number;
}

/**
 * Resource timing info
 */
export interface ResourceInfo {
  name: string;
  duration: number;
  transferSize: number;
  type: string;
}

/**
 * Measure page load performance
 */
export async function measurePagePerformance(page: Page): Promise<PerformanceMetrics> {
  const metrics = await page.evaluate(() => {
    const perfData = window.performance.timing;
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;

    // Paint timing
    const paintEntries = performance.getEntriesByType('paint');
    const fp = paintEntries.find((e) => e.name === 'first-paint');
    const fcp = paintEntries.find((e) => e.name === 'first-contentful-paint');

    // Layout shift
    const lcpEntries = performance.getEntriesByType('layout-shift');
    const layoutShifts = lcpEntries.length;
    const layoutShiftScore = lcpEntries.reduce((sum, entry: any) => sum + entry.value, 0);

    // Long tasks
    const longTaskEntries = performance.getEntriesByType('longtask');
    const longTasks = longTaskEntries.map((entry: any) => entry.duration);

    // Resources
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const totalRequests = resources.length;
    const totalTransferSize = resources.reduce((sum, r) => sum + r.transferSize, 0);

    // DOM size
    const domSize = document.documentElement.outerHTML.length;

    return {
      domContentLoaded: perfData.domContentLoadedEventEnd - perfData.navigationStart,
      loadComplete: perfData.loadEventEnd - perfData.navigationStart,
      firstPaint: fp ? fp.startTime : 0,
      firstContentfulPaint: fcp ? fcp.startTime : 0,
      totalRequests,
      totalTransferSize,
      domSize,
      layoutShifts,
      layoutShiftScore,
      longTasks,
    };
  });

  // Calculate additional metrics
  const navigation = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return {
      dnsLookup: (nav.domainLookupEnd - nav.domainLookupStart) / 1000,
      tcpConnection: (nav.connectEnd - nav.connectStart) / 1000,
      tlsNegotiation: (nav.secureConnectionStart > 0
        ? nav.connectEnd - nav.secureConnectionStart
        : 0) / 1000,
      requestTime: (nav.requestStart - nav.navigationStart) / 1000,
      responseTime: (nav.responseStart - nav.requestStart) / 1000,
    };
  });

  return {
    ...metrics,
    ...navigation,
  };
}

/**
 * Measure navigation timing
 */
export async function measureNavigationTiming(page: Page): Promise<NavigationTiming> {
  return await page.evaluate(() => {
    const perfData = window.performance.timing;
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;

    return {
      dnsStart: perfData.domainLookupStart,
      dnsEnd: perfData.domainLookupEnd,
      connectStart: perfData.connectStart,
      connectEnd: perfData.connectEnd,
      tlsStart: perfData.secureConnectionStart,
      tlsEnd: perfData.connectEnd,
      requestStart: perfData.requestStart,
      responseStart: perfData.responseStart,
      responseEnd: perfData.responseEnd,
      domContentLoaded: perfData.domContentLoadedEventEnd,
      loadComplete: perfData.loadEventEnd,
    };
  });
}

/**
 * Get resource timing data
 */
export async function getResourceTiming(page: Page): Promise<ResourceInfo[]> {
  return await page.evaluate(() => {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];

    return resources.map((r) => ({
      name: r.name,
      duration: r.duration,
      transferSize: r.transferSize,
      type: r.initiatorType,
    })).sort((a, b) => b.duration - a.duration);
  });
}

/**
 * Get slow resources
 */
export async function getSlowResources(
  page: Page,
  threshold: number = 1000
): Promise<ResourceInfo[]> {
  const resources = await getResourceTiming(page);
  return resources.filter((r) => r.duration > threshold);
}

/**
 * Measure Core Web Vitals
 */
export async function measureCoreWebVitals(page: Page): Promise<{
  LCP: number;  // Largest Contentful Paint
  FID: number;  // First Input Delay
  CLS: number;  // Cumulative Layout Shift
  FCP: number;  // First Contentful Paint
  TTI: number;  // Time to Interactive
}> {
  return await page.evaluate(async () => {
    // LCP - would need PerformanceObserver
    const paintEntries = performance.getEntriesByType('paint');
    const fcp = paintEntries.find((e: any) => e.name === 'first-contentful-paint');

    // CLS
    const lcpEntries = performance.getEntriesByType('layout-shift');
    const clsValue = lcpEntries.reduce((sum: number, entry: any) => sum + entry.value, 0);

    // Get FID (would need user interaction)
    const fid = 0; // Placeholder

    // Get TTI - simplified
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const tti = nav.domContentLoadedEventEnd - nav.navigationStart;

    return {
      LCP: 0, // Requires PerformanceObserver
      FID: fid,
      CLS: clsValue,
      FCP: fcp ? fcp.startTime : 0,
      TTI: tti,
    };
  });
}

/**
 * Assert performance threshold
 */
export async function assertPerformanceThreshold(
  page: Page,
  thresholds: {
    domContentLoaded?: number;
    loadComplete?: number;
    firstContentfulPaint?: number;
    totalRequests?: number;
    totalTransferSize?: number;
  }
): Promise<void> {
  const metrics = await measurePagePerformance(page);

  if (thresholds.domContentLoaded) {
    if (metrics.domContentLoaded > thresholds.domContentLoaded) {
      throw new Error(
        `DOM Content Loaded exceeded threshold: ${metrics.domContentLoaded}ms > ${thresholds.domContentLoaded}ms`
      );
    }
  }

  if (thresholds.loadComplete) {
    if (metrics.loadComplete > thresholds.loadComplete) {
      throw new Error(
        `Load Complete exceeded threshold: ${metrics.loadComplete}ms > ${thresholds.loadComplete}ms`
      );
    }
  }

  if (thresholds.firstContentfulPaint) {
    if (metrics.firstContentfulPaint > thresholds.firstContentfulPaint) {
      throw new Error(
        `First Contentful Paint exceeded threshold: ${metrics.firstContentfulPaint}ms > ${thresholds.firstContentfulPaint}ms`
      );
    }
  }

  if (thresholds.totalRequests) {
    if (metrics.totalRequests > thresholds.totalRequests) {
      throw new Error(
        `Total requests exceeded threshold: ${metrics.totalRequests} > ${thresholds.totalRequests}`
      );
    }
  }

  if (thresholds.totalTransferSize) {
    if (metrics.totalTransferSize > thresholds.totalTransferSize) {
      throw new Error(
        `Total transfer size exceeded threshold: ${metrics.totalTransferSize} > ${thresholds.totalTransferSize} bytes`
      );
    }
  }
}

/**
 * Measure page load time
 */
export async function measurePageLoadTime(page: Page, url: string): Promise<number> {
  const startTime = Date.now();

  await page.goto(url, { waitUntil: 'load' });
  await page.waitForLoadState('domcontentloaded');

  return Date.now() - startTime;
}

/**
 * Compare page load times
 */
export async function comparePageLoadTimes(
  page: Page,
  urls: string[]
): Promise<Array<{ url: string; loadTime: number }>> {
  const results: Array<{ url: string; loadTime: number }> = [];

  for (const url of urls) {
    const loadTime = await measurePageLoadTime(page, url);
    results.push({ url, loadTime });
  }

  return results.sort((a, b) => b.loadTime - a.loadTime);
}

/**
 * Memory usage snapshot
 */
export async function getMemoryUsage(page: Page): Promise<{
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}> {
  return await page.evaluate(() => {
    // @ts-ignore
    if (performance.memory) {
      // @ts-ignore
      const { usedJSHeapSize, totalJSHeapSize, jsHeapSizeLimit } = performance.memory;
      return {
        usedJSHeapSize,
        totalJSHeapSize,
        jsHeapSizeLimit,
      };
    }
    return {
      usedJSHeapSize: 0,
      totalJSHeapSize: 0,
      jsHeapSizeLimit: 0,
    };
  });
}

/**
 * Measure memory usage before and after action
 */
export async function measureMemoryImpact<T>(
  page: Page,
  action: () => Promise<T>
): Promise<{ result: T; memoryBefore: number; memoryAfter: number; delta: number }> {
  const before = await getMemoryUsage(page);
  const result = await action();
  const after = await getMemoryUsage(page);

  return {
    result,
    memoryBefore: before.usedJSHeapSize,
    memoryAfter: after.usedJSHeapSize,
    delta: after.usedJSHeapSize - before.usedJSHeapSize,
  };
}

/**
 * Track network requests
 */
export async function trackNetworkRequests(
  page: Page,
  action: () => Promise<void>
): Promise<Array<{ url: string; method: string; status: number; duration: number }>> {
  const requests: Array<{
    url: string;
    method: string;
    status: number;
    duration: number;
  }> = [];

  page.on('request', (request) => {
    // Store request info
  });

  page.on('response', (response) => {
    requests.push({
      url: response.url(),
      method: response.request().method(),
      status: response.status(),
      duration: 0, // Would need to match request with response
    });
  });

  await action();

  return requests;
}

/**
 * Measure FPS (Frames Per Second)
 */
export async function measureFPS(
  page: Page,
  duration: number = 5000
): Promise<{ average: number; min: number; max: number }> {
  const fps = await page.evaluate(async (durationMs) => {
    const frames: number[] = [];
    const startTime = performance.now();

    const measureFrame = () => {
      frames.push(performance.now());
      if (performance.now() - startTime < durationMs) {
        requestAnimationFrame(measureFrame);
      }
    };

    requestAnimationFrame(measureFrame);

    // Wait for measurement
    await new Promise((resolve) => setTimeout(resolve, durationMs + 100));

    // Calculate FPS
    const fpsValues: number[] = [];
    for (let i = 1; i < frames.length; i++) {
      fpsValues.push(1000 / (frames[i] - frames[i - 1]));
    }

    return {
      average: fpsValues.reduce((a, b) => a + b, 0) / fpsValues.length || 0,
      min: Math.min(...fpsValues) || 0,
      max: Math.max(...fpsValues) || 0,
    };
  }, duration);

  return fps;
}

/**
 * Performance test helper
 */
export function testPerformance(page: Page) {
  return {
    async measure() {
      return await measurePagePerformance(page);
    },

    async assertThresholds(thresholds: Parameters<typeof assertPerformanceThreshold>[1]) {
      await assertPerformanceThreshold(page, thresholds);
    },

    async getCoreWebVitals() {
      return await measureCoreWebVitals(page);
    },

    async getResources() {
      return await getResourceTiming(page);
    },

    async getSlowResources(threshold = 1000) {
      return await getSlowResources(page, threshold);
    },

    async measureAction<T>(action: () => Promise<T>) {
      return await measureMemoryImpact(page, action);
    },

    async measureFPS(duration = 5000) {
      return await measureFPS(page, duration);
    },
  };
}

/**
 * Benchmark test
 */
export async function runBenchmark(
  page: Page,
  scenario: {
    name: string;
    setup?: () => Promise<void>;
    action: () => Promise<void>;
    iterations?: number;
  }
): Promise<{
  name: string;
  iterations: number;
  totalTime: number;
  averageTime: number;
  minTime: number;
  maxTime: number;
  memoryDelta: number;
}> {
  const iterations = scenario.iterations || 5;
  const times: number[] = [];

  if (scenario.setup) {
    await scenario.setup();
  }

  const memoryBefore = await getMemoryUsage(page);

  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    await scenario.action();
    const end = performance.now();
    times.push(end - start);
  }

  const memoryAfter = await getMemoryUsage(page);

  const totalTime = times.reduce((a, b) => a + b, 0);

  return {
    name: scenario.name,
    iterations,
    totalTime,
    averageTime: totalTime / iterations,
    minTime: Math.min(...times),
    maxTime: Math.max(...times),
    memoryDelta: memoryAfter.usedJSHeapSize - memoryBefore.usedJSHeapSize,
  };
}

/**
 * Compare benchmark results
 */
export function compareBenchmarks(
  baseline: { name: string; averageTime: number },
  current: { name: string; averageTime: number }
): {
  improved: boolean;
  difference: number;
  percentChange: number;
} {
  const difference = current.averageTime - baseline.averageTime;
  const percentChange = (difference / baseline.averageTime) * 100;

  return {
    improved: difference < 0,
    difference,
    percentChange,
  };
}

/**
 * Generate performance report
 */
export async function generatePerformanceReport(page: Page): Promise<string> {
  const [metrics, resources, vitals] = await Promise.all([
    measurePagePerformance(page),
    getResourceTiming(page),
    measureCoreWebVitals(page),
  ]);

  const slowResources = resources.filter((r) => r.duration > 1000);

  const lines: string[] = [];
  lines.push('# Performance Report');
  lines.push('');
  lines.push(`Generated: ${new Date().toISOString()}`);
  lines.push('');

  // Timing Metrics
  lines.push('## Timing Metrics');
  lines.push(`- DOM Content Loaded: ${metrics.domContentLoaded.toFixed(0)}ms`);
  lines.push(`- Load Complete: ${metrics.loadComplete.toFixed(0)}ms`);
  lines.push(`- First Paint: ${metrics.firstPaint.toFixed(0)}ms`);
  lines.push(`- First Contentful Paint: ${metrics.firstContentfulPaint.toFixed(0)}ms`);
  lines.push('');

  // Network
  lines.push('## Network');
  lines.push(`- Total Requests: ${metrics.totalRequests}`);
  lines.push(`- Total Transfer Size: ${(metrics.totalTransferSize / 1024).toFixed(2)} KB`);
  lines.push(`- Slow Resources (>1s): ${slowResources.length}`);
  if (slowResources.length > 0) {
    slowResources.slice(0, 5).forEach((r) => {
      lines.push(`  - ${r.name.substring(0, 60)} (${r.duration.toFixed(0)}ms)`);
    });
  }
  lines.push('');

  // Core Web Vitals
  lines.push('## Core Web Vitals');
  lines.push(`- FCP: ${vitals.FCP.toFixed(0)}ms`);
  lines.push(`- LCP: ${vitals.LCP}ms`);
  lines.push(`- CLS: ${vitals.CLS.toFixed(4)}`);
  lines.push(`- FID: ${vitals.FID}ms`);
  lines.push(`- TTI: ${vitals.TTI.toFixed(0)}ms`);
  lines.push('');

  // Memory
  const memory = await getMemoryUsage(page);
  lines.push('## Memory');
  lines.push(`- Used JS Heap: ${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`);
  lines.push(`- Total JS Heap: ${(memory.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB`);
  lines.push(`- Heap Limit: ${(memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB`);
  lines.push('');

  // Layout Shifts
  lines.push('## Layout Stability');
  lines.push(`- Layout Shifts: ${metrics.layoutShifts}`);
  lines.push(`- CLS Score: ${metrics.layoutShiftScore.toFixed(4)}`);
  if (metrics.layoutShifts > 0) {
    lines.push(`- Status: ${metrics.layoutShiftScore > 0.1 ? '❌ Needs improvement' : '✅ Good'}`);
  }
  lines.push('');

  return lines.join('\n');
}
