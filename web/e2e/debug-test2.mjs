import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();

// Listen for console messages
page.on('console', msg => {
  console.log('Browser console:', msg.type(), msg.text());
});

page.on('pageerror', error => {
  console.log('Browser page error:', error.message);
});

// Clear storage
await page.goto('http://localhost:3000');
await page.evaluate(() => {
  localStorage.clear();
  sessionStorage.clear();
});

// Navigate to login
await page.goto('http://localhost:3000/login');

// Wait for page to load
await page.waitForTimeout(5000);

// Check if React root has children
const rootContent = await page.$eval('#root', el => el.innerHTML);
console.log('Root element HTML length:', rootContent.length);
console.log('Root element HTML preview:', rootContent.substring(0, 500));

// Check URL
console.log('Final URL:', page.url());

await browser.close();
