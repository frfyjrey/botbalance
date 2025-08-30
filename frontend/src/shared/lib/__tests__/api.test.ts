import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, tokenManager } from '../api';

// Mock fetch
global.fetch = vi.fn();

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  describe('tokenManager', () => {
    it('should have basic functionality', () => {
      // Basic test to verify tokenManager exists and has expected methods
      expect(tokenManager.setTokens).toBeDefined();
      expect(tokenManager.getAccessToken).toBeDefined();
      expect(tokenManager.getRefreshToken).toBeDefined();
      expect(tokenManager.isAuthenticated).toBeDefined();
      expect(tokenManager.clearTokens).toBeDefined();
    });
  });

  describe('apiClient', () => {
    it('should make login request', async () => {
      const mockResponse = {
        status: 'success',
        user: { id: 1, username: 'admin' },
        tokens: { access: 'token', refresh: 'refresh' },
      };

      (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.login({
        username: 'admin',
        password: 'password',
      });

      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/login/',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ username: 'admin', password: 'password' }),
        }),
      );
    });

    it('should make profile request', async () => {
      (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ user: { id: 1 } }),
      });

      await apiClient.getUserProfile();

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/profile/',
        expect.any(Object),
      );
    });
  });
});
