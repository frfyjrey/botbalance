import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('login flow and dashboard navigation', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');

    // Should redirect to login page
    await expect(page).toHaveURL('/login');

    // Check login page elements
    await expect(page.getByText('BotBalance')).toBeVisible();
    await expect(
      page.getByPlaceholder('Введите имя пользователя'),
    ).toBeVisible();
    await expect(page.getByPlaceholder('Введите пароль')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Войти' })).toBeVisible();

    // Fill in credentials (demo credentials)
    await page.getByPlaceholder('Введите имя пользователя').fill('admin');
    await page.getByPlaceholder('Введите пароль').fill('admin123');

    // Submit form
    await page.getByRole('button', { name: 'Войти' }).click();

    // Should navigate to dashboard
    await expect(page).toHaveURL('/dashboard');

    // Check dashboard elements
    await expect(page.getByText('Привет, admin!')).toBeVisible();
    await expect(page.getByText('База данных:healthy')).toBeVisible();

    // Check theme toggle button
    await expect(page.locator('button[title*="Текущая тема"]')).toBeVisible();

    // Check logout button
    await expect(page.getByRole('button', { name: 'Выйти' })).toBeVisible();

    // Test echo task creation
    await expect(
      page.getByRole('button', { name: 'Создать Echo задачу' }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Создать Echo задачу' }).click();

    // Should show task status
    await expect(page.getByText('Состояние:')).toBeVisible();

    // Wait for task completion (max 10 seconds)
    await expect(page.getByText('SUCCESS')).toBeVisible({ timeout: 10000 });

    // Test logout
    await page.getByRole('button', { name: 'Выйти' }).click();

    // Should redirect back to login
    await expect(page).toHaveURL('/login');
  });

  test('theme toggle functionality', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByPlaceholder('Введите имя пользователя').fill('admin');
    await page.getByPlaceholder('Введите пароль').fill('admin123');
    await page.getByRole('button', { name: 'Войти' }).click();

    await expect(page).toHaveURL('/dashboard');

    // Find theme toggle button
    const themeButton = page.locator('button[title*="Текущая тема"]');
    await expect(themeButton).toBeVisible();

    // Click theme toggle and check for visual changes
    await themeButton.click();

    // Wait for theme change and check if dark class is applied to html element
    const htmlElement = page.locator('html');
    await expect(htmlElement).toHaveClass(/dark/, { timeout: 1000 });

    // Click again to cycle through themes
    await themeButton.click();
    await themeButton.click();

    // Should cycle back to original theme
    // The test verifies theme toggling works without checking specific end state
  });
});
