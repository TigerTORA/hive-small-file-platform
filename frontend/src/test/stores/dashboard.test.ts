import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useDashboardStore } from "@/stores/dashboard";
import { dashboardApi } from "@/api/dashboard";
import type { DashboardSummary } from "@/api/dashboard";

// Mock the dashboard API
vi.mock("@/api/dashboard", () => ({
  dashboardApi: {
    getSummary: vi.fn(),
    getTrends: vi.fn(),
    getFileDistribution: vi.fn(),
    getTopTables: vi.fn(),
    getRecentTasks: vi.fn(),
    getClusterStats: vi.fn(),
  },
}));

// Mock Element Plus
vi.mock("element-plus", () => ({
  ElMessage: {
    error: vi.fn(),
  },
}));

describe("Dashboard Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should have correct initial state", () => {
      const store = useDashboardStore();

      expect(store.summary).toEqual({
        total_clusters: 0,
        active_clusters: 0,
        total_tables: 0,
        monitored_tables: 0,
        total_files: 0,
        total_small_files: 0,
        small_file_ratio: 0,
        total_size_gb: 0,
        small_file_size_gb: 0,
      });

      expect(store.trends).toEqual([]);
      expect(store.fileDistribution).toEqual([]);
      expect(store.topTables).toEqual([]);
      expect(store.recentTasks).toEqual([]);
      expect(store.clusterStats).toEqual([]);
    });

    it("should have correct initial loading states", () => {
      const store = useDashboardStore();

      expect(store.loading.summary).toBe(false);
      expect(store.loading.trends).toBe(false);
      expect(store.loading.fileDistribution).toBe(false);
      expect(store.loading.topTables).toBe(false);
      expect(store.loading.recentTasks).toBe(false);
      expect(store.loading.clusterStats).toBe(false);
    });

    it("should have null error states initially", () => {
      const store = useDashboardStore();

      expect(store.errors.summary).toBe(null);
      expect(store.errors.trends).toBe(null);
      expect(store.errors.fileDistribution).toBe(null);
      expect(store.errors.topTables).toBe(null);
      expect(store.errors.recentTasks).toBe(null);
      expect(store.errors.clusterStats).toBe(null);
    });
  });

  describe("Computed Properties", () => {
    it("should calculate isLoading correctly", () => {
      const store = useDashboardStore();

      expect(store.isLoading).toBe(false);

      store.loading.summary = true;
      expect(store.isLoading).toBe(true);

      store.loading.summary = false;
      store.loading.trends = true;
      expect(store.isLoading).toBe(true);

      store.loading.trends = false;
      expect(store.isLoading).toBe(false);
    });

    it("should calculate hasErrors correctly", () => {
      const store = useDashboardStore();

      expect(store.hasErrors).toBe(false);

      store.errors.summary = "Test error";
      expect(store.hasErrors).toBe(true);

      store.errors.summary = null;
      store.errors.trends = "Another error";
      expect(store.hasErrors).toBe(true);

      store.errors.trends = null;
      expect(store.hasErrors).toBe(false);
    });

    it("should calculate smallFileRatio correctly", () => {
      const store = useDashboardStore();

      // Test with zero total files
      expect(store.smallFileRatio).toBe(0);

      // Test with normal values
      store.summary.total_files = 1000;
      store.summary.total_small_files = 300;
      expect(store.smallFileRatio).toBe(30); // 300/1000 * 100 = 30%

      // Test with decimal result
      store.summary.total_files = 1000;
      store.summary.total_small_files = 333;
      expect(store.smallFileRatio).toBe(33); // Should round to 33%
    });
  });

  describe("loadSummary", () => {
    it("should load summary data successfully", async () => {
      const store = useDashboardStore();
      const mockSummary: DashboardSummary = {
        total_clusters: 3,
        active_clusters: 2,
        total_tables: 100,
        monitored_tables: 80,
        total_files: 50000,
        total_small_files: 15000,
        small_file_ratio: 30,
        total_size_gb: 1000,
        small_file_size_gb: 200,
      };

      vi.mocked(dashboardApi.getSummary).mockResolvedValue(mockSummary);

      await store.loadSummary();

      expect(store.loading.summary).toBe(false);
      expect(store.errors.summary).toBe(null);
      expect(store.summary).toEqual(mockSummary);
      expect(dashboardApi.getSummary).toHaveBeenCalledOnce();
    });

    it("should handle summary loading error", async () => {
      const store = useDashboardStore();
      const errorMessage = "Failed to load summary";

      vi.mocked(dashboardApi.getSummary).mockRejectedValue(
        new Error(errorMessage),
      );

      await store.loadSummary();

      expect(store.loading.summary).toBe(false);
      expect(store.errors.summary).toBe(errorMessage);
    });

    it("should set loading state during summary fetch", async () => {
      const store = useDashboardStore();
      let resolvePromise: (value: any) => void;

      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      vi.mocked(dashboardApi.getSummary).mockReturnValue(promise as any);

      const loadPromise = store.loadSummary();

      expect(store.loading.summary).toBe(true);

      resolvePromise!({});
      await loadPromise;

      expect(store.loading.summary).toBe(false);
    });
  });

  describe("loadTrends", () => {
    it("should load trends with default parameters", async () => {
      const store = useDashboardStore();
      const mockTrends = [
        {
          date: "2023-12-01",
          total_files: 1000,
          small_files: 300,
          ratio: 30.0,
        },
      ];

      vi.mocked(dashboardApi.getTrends).mockResolvedValue(mockTrends);

      await store.loadTrends();

      expect(dashboardApi.getTrends).toHaveBeenCalledWith(undefined, 30);
      expect(store.trends).toEqual(mockTrends);
      expect(store.errors.trends).toBe(null);
    });

    it("should load trends with custom parameters", async () => {
      const store = useDashboardStore();
      const mockTrends = [];

      vi.mocked(dashboardApi.getTrends).mockResolvedValue(mockTrends);

      await store.loadTrends(1, 7);

      expect(dashboardApi.getTrends).toHaveBeenCalledWith(1, 7);
    });

    it("should handle trends loading error", async () => {
      const store = useDashboardStore();
      const errorMessage = "Failed to load trends";

      vi.mocked(dashboardApi.getTrends).mockRejectedValue(
        new Error(errorMessage),
      );

      await store.loadTrends();

      expect(store.errors.trends).toBe(errorMessage);
    });
  });

  describe("loadAllData", () => {
    it("should load all dashboard data", async () => {
      const store = useDashboardStore();

      vi.mocked(dashboardApi.getSummary).mockResolvedValue({} as any);
      vi.mocked(dashboardApi.getTrends).mockResolvedValue([]);
      vi.mocked(dashboardApi.getFileDistribution).mockResolvedValue([]);
      vi.mocked(dashboardApi.getTopTables).mockResolvedValue([]);
      vi.mocked(dashboardApi.getRecentTasks).mockResolvedValue([]);
      vi.mocked(dashboardApi.getClusterStats).mockResolvedValue({
        clusters: [],
      });

      await store.loadAllData();

      expect(dashboardApi.getSummary).toHaveBeenCalledOnce();
      expect(dashboardApi.getTrends).toHaveBeenCalledWith(undefined, 7);
      expect(dashboardApi.getFileDistribution).toHaveBeenCalledWith(undefined);
      expect(dashboardApi.getTopTables).toHaveBeenCalledWith(undefined, 10);
      expect(dashboardApi.getRecentTasks).toHaveBeenCalledWith(10, undefined);
      expect(dashboardApi.getClusterStats).toHaveBeenCalledOnce();
    });

    it("should load all data with cluster filter", async () => {
      const store = useDashboardStore();

      vi.mocked(dashboardApi.getSummary).mockResolvedValue({} as any);
      vi.mocked(dashboardApi.getTrends).mockResolvedValue([]);
      vi.mocked(dashboardApi.getFileDistribution).mockResolvedValue([]);
      vi.mocked(dashboardApi.getTopTables).mockResolvedValue([]);
      vi.mocked(dashboardApi.getRecentTasks).mockResolvedValue([]);
      vi.mocked(dashboardApi.getClusterStats).mockResolvedValue({
        clusters: [],
      });

      await store.loadAllData(1);

      expect(dashboardApi.getTrends).toHaveBeenCalledWith(1, 7);
      expect(dashboardApi.getFileDistribution).toHaveBeenCalledWith(1);
      expect(dashboardApi.getTopTables).toHaveBeenCalledWith(1, 10);
    });
  });

  describe("refresh", () => {
    it("should call loadAllData", async () => {
      const store = useDashboardStore();

      // Mock all the API calls that loadAllData uses
      vi.mocked(dashboardApi.getSummary).mockResolvedValue({} as any);
      vi.mocked(dashboardApi.getTrends).mockResolvedValue([]);
      vi.mocked(dashboardApi.getFileDistribution).mockResolvedValue([]);
      vi.mocked(dashboardApi.getTopTables).mockResolvedValue([]);
      vi.mocked(dashboardApi.getRecentTasks).mockResolvedValue([]);
      vi.mocked(dashboardApi.getClusterStats).mockResolvedValue({
        clusters: [],
      });

      await store.refresh(1);

      // Verify the individual API calls that loadAllData makes
      expect(dashboardApi.getTrends).toHaveBeenCalledWith(1, 7);
      expect(dashboardApi.getFileDistribution).toHaveBeenCalledWith(1);
      expect(dashboardApi.getTopTables).toHaveBeenCalledWith(1, 10);
    });
  });

  describe("clearErrors", () => {
    it("should clear all error states", () => {
      const store = useDashboardStore();

      // Set some errors
      store.errors.summary = "Error 1";
      store.errors.trends = "Error 2";
      store.errors.fileDistribution = "Error 3";

      store.clearErrors();

      expect(store.errors.summary).toBe(null);
      expect(store.errors.trends).toBe(null);
      expect(store.errors.fileDistribution).toBe(null);
      expect(store.errors.topTables).toBe(null);
      expect(store.errors.recentTasks).toBe(null);
      expect(store.errors.clusterStats).toBe(null);
    });
  });

  describe("reset", () => {
    it("should reset all state to initial values", () => {
      const store = useDashboardStore();

      // Set some data
      store.summary.total_clusters = 5;
      store.trends = [
        {
          date: "2023-12-01",
          total_files: 1000,
          small_files: 300,
          ratio: 30.0,
        },
      ];
      store.fileDistribution = [{ size_range: "< 1MB", count: 100 }];
      store.errors.summary = "Error";

      store.reset();

      expect(store.summary.total_clusters).toBe(0);
      expect(store.trends).toEqual([]);
      expect(store.fileDistribution).toEqual([]);
      expect(store.topTables).toEqual([]);
      expect(store.recentTasks).toEqual([]);
      expect(store.clusterStats).toEqual([]);
      expect(store.errors.summary).toBe(null);
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors with message property", async () => {
      const store = useDashboardStore();
      const error = { message: "Custom error message" };

      vi.mocked(dashboardApi.getSummary).mockRejectedValue(error);

      await store.loadSummary();

      expect(store.errors.summary).toBe("Custom error message");
    });

    it("should handle API errors without message property", async () => {
      const store = useDashboardStore();
      const error = "String error";

      vi.mocked(dashboardApi.getSummary).mockRejectedValue(error);

      await store.loadSummary();

      expect(store.errors.summary).toBe("加载概要数据失败");
    });
  });
});
