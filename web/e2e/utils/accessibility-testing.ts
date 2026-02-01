/**
 * Accessibility Testing Utilities
 *
 * Helper functions for accessibility (a11y) testing
 */

import { Page, Locator } from '@playwright/test';

/**
 * Accessibility violation
 */
export interface A11yViolation {
  id: string;
  impact: 'critical' | 'serious' | 'moderate' | 'minor';
  description: string;
  help: string;
  helpUrl: string;
  nodes: Array<{
    html: string;
    target: string[];
    failureSummary: string;
  }>;
}

/**
 * Run axe-core accessibility scan
 */
export async function runAxeScan(
  page: Page,
  context?: string | string[] | { include?: string[]; exclude?: string[] }
): Promise<A11yViolation[]> {
  return await page.evaluate(async (ctx) => {
    // @ts-ignore - axe-core will be injected
    if (typeof axe === 'undefined') {
      // Inject axe-core if not present
      await new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js';
        script.onload = resolve;
        document.head.appendChild(script);
      });
    }

    // @ts-ignore
    const results = await axe.run(ctx || document, {
      resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable'],
    });

    return results.violations.map((v: any) => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      help: v.help,
      helpUrl: v.helpUrl,
      nodes: v.nodes.map((n: any) => ({
        html: n.html,
        target: n.target,
        failureSummary: n.failureSummary,
      })),
    }));
  }, context);
}

/**
 * Verify no critical accessibility violations
 */
export async function verifyNoCriticalViolations(page: Page): Promise<void> {
  const violations = await runAxeScan(page);
  const criticalViolations = violations.filter((v) => v.impact === 'critical');

  if (criticalViolations.length > 0) {
    const message = criticalViolations
      .map((v) => `- ${v.id}: ${v.description}`)
      .join('\n');
    throw new Error(`Critical accessibility violations found:\n${message}`);
  }
}

/**
 * Verify all accessibility violations
 */
export async function verifyNoViolations(
  page: Page,
  allowedImpactTypes: Array<'critical' | 'serious' | 'moderate' | 'minor'> = []
): Promise<void> {
  const violations = await runAxeScan(page);
  const filteredViolations = violations.filter(
    (v) => v.impact && !allowedImpactTypes.includes(v.impact)
  );

  if (filteredViolations.length > 0) {
    const message = filteredViolations
      .map((v) => `- [${v.impact}] ${v.id}: ${v.description}`)
      .join('\n');
    throw new Error(`Accessibility violations found:\n${message}`);
  }
}

/**
 * Get accessibility report
 */
export async function getAccessibilityReport(page: Page): Promise<{
  violations: A11yViolation[];
  passes: number;
  incomplete: number;
  timestamp: number;
}> {
  const results = await page.evaluate(async () => {
    // @ts-ignore
    if (typeof axe === 'undefined') {
      await new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js';
        script.onload = resolve;
        document.head.appendChild(script);
      });
    }

    // @ts-ignore
    const axeResults = await axe.run(document, {
      resultTypes: ['violations', 'passes', 'incomplete', 'inapplicable'],
    });

    return {
      violations: axeResults.violations.length,
      passes: axeResults.passes.length,
      incomplete: axeResults.incomplete.length,
    };
  });

  const violations = await runAxeScan(page);

  return {
    violations,
    passes: results.passes,
    incomplete: results.incomplete,
    timestamp: Date.now(),
  };
}

/**
 * Check page title
 */
export async function verifyPageTitle(page: Page, expected?: string): Promise<boolean> {
  const title = await page.title();

  if (expected) {
    return title === expected || title.includes(expected);
  }

  return title.length > 0 && title.length < 200;
}

/**
 * Check page language
 */
export async function verifyPageLanguage(page: Page): Promise<boolean> {
  const lang = await page.locator('html').getAttribute('lang');
  return lang !== null && lang.length >= 2;
}

/**
 * Check heading hierarchy
 */
export async function verifyHeadingHierarchy(page: Page): Promise<{
  valid: boolean;
  issues: string[];
}> {
  const issues: string[] = [];

  const result = await page.evaluate(() => {
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    const issues: string[] = [];
    let previousLevel = 0;

    headings.forEach((heading, index) => {
      const level = parseInt(heading.tagName.substring(1));

      // First heading should be h1
      if (index === 0 && level !== 1) {
        issues.push(`First heading is ${heading.tagName}, expected h1`);
      }

      // Heading levels should not skip (e.g., h1 to h3)
      if (previousLevel > 0 && level > previousLevel + 1) {
        issues.push(
          `Heading level skipped: ${previousLevel} to ${level} at "${heading.textContent}"`
        );
      }

      previousLevel = level;
    });

    return { issues, headingCount: headings.length };
  });

  issues.push(...result.issues);

  if (result.headingCount === 0) {
    issues.push('No headings found on page');
  }

  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * Check image alt text
 */
export async function verifyImageAltText(page: Page): Promise<{
  valid: boolean;
  images: {
    total: number;
    withAlt: number;
    withoutAlt: number;
    missingAlt: Array<{ src: string; decorated: boolean }>;
  };
}> {
  const result = await page.evaluate(() => {
    const images = document.querySelectorAll('img');
    const missingAlt: Array<{ src: string; decorated: boolean }> = [];

    images.forEach((img) => {
      const alt = img.getAttribute('alt');
      const role = img.getAttribute('role');

      // Check if image is decorative (alt="" or role="presentation")
      const isDecorative = alt === '' || role === 'presentation';

      if (alt === null) {
        missingAlt.push({
          src: img.src.substring(0, 100),
          decorated: isDecorative,
        });
      }
    });

    return {
      total: images.length,
      withAlt: images.length - missingAlt.length,
      withoutAlt: missingAlt.length,
      missingAlt,
    };
  });

  return {
    valid: result.missingAlt.length === 0,
    images: {
      total: result.total,
      withAlt: result.withAlt,
      withoutAlt: result.withoutAlt,
      missingAlt: result.missingAlt,
    },
  };
}

/**
 * Check form labels
 */
export async function verifyFormLabels(page: Page): Promise<{
  valid: boolean;
  issues: string[];
}> {
  const issues: string[] = [];

  const result = await page.evaluate(() => {
    const inputs = document.querySelectorAll('input, select, textarea');
    const issues: string[] = [];

    inputs.forEach((input) => {
      // Skip hidden inputs and submit buttons
      const type = input.getAttribute('type');
      if (type === 'hidden' || type === 'submit' || type === 'button') {
        return;
      }

      // Check for label
      const id = input.id;
      const ariaLabel = input.getAttribute('aria-label');
      const ariaLabelledBy = input.getAttribute('aria-labelledby');
      const hasLabel = id
        ? document.querySelector(`label[for="${id}"]`)
        : false;

      if (!hasLabel && !ariaLabel && !ariaLabelledBy) {
        const placeholder = input.getAttribute('placeholder');
        const name = input.getAttribute('name');
        issues.push(
          `Input lacks label: ${name ? `name="${name}"` : placeholder ? `placeholder="${placeholder}"` : 'unnamed input'}`
        );
      }
    });

    return { issues };
  });

  issues.push(...result.issues);

  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * Check link accessibility
 */
export async function verifyLinks(page: Page): Promise<{
  valid: boolean;
  issues: string[];
}> {
  const issues: string[] = [];

  const result = await page.evaluate(() => {
    const links = document.querySelectorAll('a');
    const issues: string[] = [];

    links.forEach((link) => {
      const text = link.textContent?.trim();
      const ariaLabel = link.getAttribute('aria-label');
      const title = link.getAttribute('title');

      // Check if link has accessible text
      if (!text && !ariaLabel && !title) {
        const href = link.getAttribute('href');
        issues.push(`Link has no accessible text: href="${href}"`);
      }

      // Check for empty links
      if (text === '' && !ariaLabel) {
        issues.push(`Empty link found`);
      }

      // Check for generic link text
      if (text === '点击这里' || text === 'click here' || text === '更多') {
        issues.push(`Generic link text: "${text}"`);
      }
    });

    return { issues };
  });

  issues.push(...result.issues);

  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * Check color contrast
 */
export async function verifyColorContrast(page: Page): Promise<{
  valid: boolean;
  issues: string[];
}> {
  const issues: string[] = [];

  const result = await page.evaluate(() => {
    const issues: string[] = [];

    // Get all text elements
    const textElements = document.querySelectorAll('p, span, div, a, button, h1, h2, h3, h4, h5, h6, label');

    textElements.forEach((el) => {
      if (!(el instanceof HTMLElement)) return;

      const computed = window.getComputedStyle(el);
      const color = computed.color;
      const backgroundColor = computed.backgroundColor;

      // Skip if transparent
      if (backgroundColor === 'rgba(0, 0, 0, 0)' || backgroundColor === 'transparent') {
        // Try to get parent background
        const parent = el.parentElement;
        if (parent) {
          const parentBg = window.getComputedStyle(parent).backgroundColor;
          if (parentBg === 'rgba(0, 0, 0, 0)' || parentBg === 'transparent') {
            return;
          }
        }
      }

      // Parse RGB values
      const parseColor = (c: string) => {
        const match = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (match) {
          return {
            r: parseInt(match[1]),
            g: parseInt(match[2]),
            b: parseInt(match[3]),
          };
        }
        return null;
      };

      const fg = parseColor(color);
      const bg = parseColor(backgroundColor);

      if (fg && bg) {
        // Calculate relative luminance
        const luminance = (r: number, g: number, b: number) => {
          const [R, G, B] = [r, g, b].map((v) => {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
          });
          return 0.2126 * R + 0.7152 * G + 0.0722 * B;
        };

        const L1 = luminance(fg.r, fg.g, fg.b) + 0.05;
        const L2 = luminance(bg.r, bg.g, bg.b) + 0.05;

        const ratio = Math.max(L1, L2) / Math.min(L1, L2);

        // WCAG AA requires 4.5:1 for normal text, 3:1 for large text
        const fontSize = parseFloat(computed.fontSize);
        const fontWeight = parseInt(computed.fontWeight);
        const isLargeText = fontSize >= 18 || (fontSize >= 14 && fontWeight >= 700);

        const minRatio = isLargeText ? 3 : 4.5;

        if (ratio < minRatio) {
          const text = el.textContent?.substring(0, 30);
          issues.push(
            `Low contrast (${ratio.toFixed(2)}:1) at "${text}..."`
          );
        }
      }
    });

    return { issues };
  });

  issues.push(...result.issues);

  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * Check keyboard navigation
 */
export async function verifyKeyboardNavigation(page: Page): Promise<{
  valid: boolean;
  issues: string[];
  focusableElements: number;
}> {
  const issues: string[] = [];

  // Check for skip navigation link
  const skipLink = await page.locator('a[href^="#"]:has-text("跳过"), a[href^="#skip"]').count();
  if (skipLink === 0) {
    issues.push('No skip navigation link found');
  }

  // Check focus order
  const focusableElements = await page.evaluate(() => {
    const focusable = 'a, button, input, textarea, select, [tabindex]:not([tabindex="-1"])';
    const elements = document.querySelectorAll(focusable);
    return elements.length;
  });

  return {
    valid: issues.length === 0,
    issues,
    focusableElements,
  };
}

/**
 * Check ARIA attributes
 */
export async function verifyAriaAttributes(page: Page): Promise<{
  valid: boolean;
  issues: string[];
}> {
  const issues: string[] = [];

  const result = await page.evaluate(() => {
    const issues: string[] = [];

    // Check for ARIA labels on interactive elements
    const interactive = document.querySelectorAll('button, a, input, select, textarea');

    interactive.forEach((el) => {
      const ariaLabel = el.getAttribute('aria-label');
      const ariaLabelledBy = el.getAttribute('aria-labelledby');
      const hasTextContent = el.textContent?.trim().length > 0;

      // Icons and buttons with only images need ARIA labels
      if (!hasTextContent && !ariaLabel && !ariaLabelledBy) {
        const tagName = el.tagName.toLowerCase();
        const className = el.className;
        issues.push(`Interactive element without ARIA label: <${tagName} class="${className}">`);
      }
    });

    // Check for invalid ARIA roles
    const allWithRole = document.querySelectorAll('[role]');
    const validRoles = new Set([
      'alert',
      'alertdialog',
      'application',
      'article',
      'banner',
      'button',
      'cell',
      'checkbox',
      'columnheader',
      'combobox',
      'complementary',
      'contentinfo',
      'definition',
      'dialog',
      'directory',
      'document',
      'feed',
      'figure',
      'form',
      'grid',
      'gridcell',
      'group',
      'heading',
      'img',
      'link',
      'list',
      'listbox',
      'listitem',
      'log',
      'main',
      'marquee',
      'math',
      'menu',
      'menubar',
      'menuitem',
      'menuitemcheckbox',
      'menuitemradio',
      'navigation',
      'none',
      'note',
      'option',
      'presentation',
      'progressbar',
      'radio',
      'radiogroup',
      'region',
      'row',
      'rowgroup',
      'rowheader',
      'scrollbar',
      'search',
      'searchbox',
      'separator',
      'slider',
      'spinbutton',
      'status',
      'switch',
      'tab',
      'table',
      'tablist',
      'tabpanel',
      'term',
      'textbox',
      'timer',
      'toolbar',
      'tooltip',
      'tree',
      'treegrid',
      'treeitem',
    ]);

    allWithRole.forEach((el) => {
      const role = el.getAttribute('role');
      if (role && !validRoles.has(role.toLowerCase())) {
        issues.push(`Invalid ARIA role: "${role}"`);
      }
    });

    return { issues };
  });

  issues.push(...result.issues);

  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * Run comprehensive accessibility check
 */
export async function runAccessibilityCheck(page: Page): Promise<{
  passed: boolean;
  results: {
    axe: A11yViolation[];
    pageTitle: boolean;
    language: boolean;
    headings: ReturnType<typeof verifyHeadingHierarchy>;
    images: ReturnType<typeof verifyImageAltText>;
    forms: ReturnType<typeof verifyFormLabels>;
    links: ReturnType<typeof verifyLinks>;
    contrast: ReturnType<typeof verifyColorContrast>;
    keyboard: ReturnType<typeof verifyKeyboardNavigation>;
    aria: ReturnType<typeof verifyAriaAttributes>;
  };
}> {
  const [axe, pageTitle, language, headings, images, forms, links, contrast, keyboard, aria] =
    await Promise.all([
      runAxeScan(page),
      verifyPageTitle(page),
      verifyPageLanguage(page),
      verifyHeadingHierarchy(page),
      verifyImageAltText(page),
      verifyFormLabels(page),
      verifyLinks(page),
      verifyColorContrast(page),
      verifyKeyboardNavigation(page),
      verifyAriaAttributes(page),
    ]);

  const results = {
    axe,
    pageTitle,
    language,
    headings,
    images,
    forms,
    links,
    contrast,
    keyboard,
    aria,
  };

  const passed =
    axe.filter((v) => v.impact === 'critical' || v.impact === 'serious').length === 0 &&
    pageTitle &&
    language &&
    headings.valid &&
    images.valid &&
    forms.valid &&
    links.valid &&
    contrast.valid &&
    aria.valid;

  return {
    passed,
    results,
  };
}

/**
 * Generate accessibility report
 */
export async function generateAccessibilityReport(page: Page): Promise<string> {
  const results = await runAccessibilityCheck(page);

  const lines: string[] = [];
  lines.push('# Accessibility Report');
  lines.push('');
  lines.push(`Overall: ${results.passed ? '✅ PASSED' : '❌ FAILED'}`);
  lines.push('');

  // Page title
  lines.push(`## Page Title: ${results.pageTitle ? '✅' : '❌'}`);

  // Language
  lines.push(`## Language: ${results.language ? '✅' : '❌'}`);

  // Headings
  lines.push(`## Headings: ${results.headings.valid ? '✅' : '❌'}`);
  if (!results.headings.valid) {
    results.headings.issues.forEach((issue) => lines.push(`  - ${issue}`));
  }

  // Images
  lines.push(`## Images: ${results.images.valid ? '✅' : '❌'}`);
  lines.push(
    `  - Total: ${results.images.images.total}, With Alt: ${results.images.images.withAlt}, Without: ${results.images.images.withoutAlt}`
  );

  // Forms
  lines.push(`## Forms: ${results.forms.valid ? '✅' : '❌'}`);
  if (!results.forms.valid) {
    results.forms.issues.forEach((issue) => lines.push(`  - ${issue}`));
  }

  // Links
  lines.push(`## Links: ${results.links.valid ? '✅' : '❌'}`);
  if (!results.links.valid) {
    results.links.issues.forEach((issue) => lines.push(`  - ${issue}`));
  }

  // Color Contrast
  lines.push(`## Color Contrast: ${results.contrast.valid ? '✅' : '❌'}`);
  if (!results.contrast.valid) {
    results.contrast.issues.forEach((issue) => lines.push(`  - ${issue}`));
  }

  // Keyboard
  lines.push(`## Keyboard Navigation: ${results.keyboard.valid ? '✅' : '❌'}`);
  lines.push(`  - Focusable elements: ${results.keyboard.focusableElements}`);

  // ARIA
  lines.push(`## ARIA: ${results.aria.valid ? '✅' : '❌'}`);
  if (!results.aria.valid) {
    results.aria.issues.forEach((issue) => lines.push(`  - ${issue}`));
  }

  // Axe violations
  lines.push(`## Axe Violations: ${results.axe.length}`);
  results.axe.forEach((v) => {
    lines.push(`  - [${v.impact}] ${v.id}: ${v.description}`);
  });

  return lines.join('\n');
}

/**
 * Accessibility test helper
 */
export function testAccessibility(page: Page) {
  return {
    async runAll() {
      return await runAccessibilityCheck(page);
    },

    async verifyCriticalOnly() {
      await verifyNoCriticalViolations(page);
    },

    async verifyWithAllowed(allowed: Array<'critical' | 'serious' | 'moderate' | 'minor'>) {
      await verifyNoViolations(page, allowed);
    },

    async getReport() {
      return await generateAccessibilityReport(page);
    },
  };
}
