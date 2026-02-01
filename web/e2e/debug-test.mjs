import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();

// Clear storage
await page.goto('http://localhost:3000');
await page.evaluate(() => {
  localStorage.clear();
  sessionStorage.clear();
});

// Navigate to login
await page.goto('http://localhost:3000/login');

// Wait for page to load
await page.waitForTimeout(3000);

// Get page content
const content = await page.content();
console.log('Page HTML length:', content.length);

// Check for specific elements
const hasLoginDataTestId = await page.$('[data-testid="login-page"]');
const hasLoginTitle = await page.$('h1');
const hasAnyInput = await page.$('input');

console.log('Has data-testid="login-page":', !!hasLoginDataTestId);
console.log('Has h1:', !!hasLoginTitle);
console.log('Has any input:', !!hasAnyInput);

if (hasLoginTitle) {
  const h1Text = await page.$eval('h1', el => el.textContent);
  console.log('H1 text:', h1Text);
}

// Check URL
console.log('Current URL:', page.url());

// Take screenshot
await page.screenshot({ path: 'e2e/debug-screenshot.png' });
console.log('Screenshot saved to e2e/debug-screenshot.png');

await browser.close();
