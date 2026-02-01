import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();

// Listen for ALL console messages
page.on('console', msg => {
  console.log('Console:', msg.type(), msg.text());
});

page.on('pageerror', error => {
  console.log('Page error:', error.toString());
});

// Clear storage
await page.goto('http://localhost:3000');
await page.evaluate(() => {
  localStorage.clear();
  sessionStorage.clear();
});

// Navigate to login
await page.goto('http://localhost:3000/login');

// Wait longer for debugging
await page.waitForTimeout(8000);

await browser.close();
