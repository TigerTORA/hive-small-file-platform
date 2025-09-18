import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ClusterList from "../ClusterList.vue";
import type { Cluster } from "@/api/clusters";

// Mock ElementPlus components
vi.mock("element-plus", () => ({
  ElEmpty: { template: '<div class="el-empty"><slot /></div>' },
  ElButton: { template: '<button class="el-button"><slot /></button>' },
  ElIcon: { template: '<i class="el-icon"><slot /></i>' },
  ElTooltip: { template: '<div class="el-tooltip"><slot /></div>' },
  ElDropdown: { template: '<div class="el-dropdown"><slot /></div>' },
  ElDropdownMenu: { template: '<div class="el-dropdown-menu"><slot /></div>' },
  ElDropdownItem: { template: '<div class="el-dropdown-item"><slot /></div>' },
}));

// Mock icons
vi.mock("@element-plus/icons-vue", () => ({
  Monitor: { template: '<i class="monitor-icon" />' },
  Right: { template: '<i class="right-icon" />' },
  Connection: { template: '<i class="connection-icon" />' },
  Edit: { template: '<i class="edit-icon" />' },
  Delete: { template: '<i class="delete-icon" />' },
  MoreFilled: { template: '<i class="more-icon" />' },
}));

// Mock components
vi.mock("@/components/ConnectionStatusIndicator.vue", () => ({
  default: {
    template: '<div class="connection-status-indicator" />',
    props: ["hiveserverStatus", "hdfsStatus", "metastoreStatus", "loading"],
  },
}));

describe("ClusterList", () => {
  const mockClusters: Cluster[] = [
    {
      id: 1,
      name: "Test Cluster 1",
      description: "Test cluster description",
      hive_host: "test-host-1",
      hive_port: 10000,
      status: "active",
    },
    {
      id: 2,
      name: "Test Cluster 2",
      description: "Another test cluster",
      hive_host: "test-host-2",
      hive_port: 10000,
      status: "inactive",
    },
  ];

  const mockClusterStats = {
    1: { databases: 5, tables: 100, small_files: 50, pending_tasks: 2 },
    2: { databases: 3, tables: 50, small_files: 25, pending_tasks: 1 },
  };

  const mockConnectionStatus = {
    1: {
      hiveserver: { status: "success", message: "Connected" },
      hdfs: { status: "success", message: "Connected" },
      metastore: { status: "success", message: "Connected" },
    },
    2: {
      hiveserver: { status: "error", message: "Connection failed" },
      hdfs: { status: "unknown", message: "Not tested" },
      metastore: { status: "error", message: "Connection failed" },
    },
  };

  const defaultProps = {
    clusters: mockClusters,
    loading: false,
    clusterStats: mockClusterStats,
    connectionStatus: mockConnectionStatus,
    searchText: "",
    statusFilter: "",
  };

  it("renders cluster list correctly", () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    expect(wrapper.find(".clusters-grid").exists()).toBe(true);
    expect(wrapper.findAll(".cluster-card")).toHaveLength(2);
  });

  it("displays cluster information correctly", () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    const firstCluster = wrapper.find(".cluster-card");
    expect(firstCluster.find(".cluster-name").text()).toBe("Test Cluster 1");
    expect(firstCluster.text()).toContain("test-host-1:10000");
  });

  it("displays cluster statistics correctly", () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    const firstCluster = wrapper.find(".cluster-card");
    expect(firstCluster.text()).toContain("5"); // databases
    expect(firstCluster.text()).toContain("100"); // tables
    expect(firstCluster.text()).toContain("50"); // small_files
  });

  it("applies online status class for active clusters", () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    const clusters = wrapper.findAll(".cluster-card");
    expect(clusters[0].classes()).toContain("cluster-online");
    expect(clusters[1].classes()).not.toContain("cluster-online");
  });

  it("filters clusters by search text", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        searchText: "Cluster 1",
      },
    });

    expect(wrapper.findAll(".cluster-card")).toHaveLength(1);
    expect(wrapper.find(".cluster-name").text()).toBe("Test Cluster 1");
  });

  it("filters clusters by status", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        statusFilter: "active",
      },
    });

    expect(wrapper.findAll(".cluster-card")).toHaveLength(1);
    expect(wrapper.find(".cluster-name").text()).toBe("Test Cluster 1");
  });

  it("shows empty state when no clusters match filters", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        clusters: [],
        loading: false,
      },
    });

    expect(wrapper.find(".empty-state").exists()).toBe(true);
    expect(wrapper.text()).toContain("暂无集群数据");
  });

  it("shows loading state", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        loading: true,
      },
    });

    expect(wrapper.find('[v-loading="true"]').exists()).toBeTruthy();
  });

  it("emits enter-cluster event when cluster is clicked", async () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    await wrapper.find(".cluster-card").trigger("click");
    expect(wrapper.emitted("enter-cluster")).toBeTruthy();
    expect(wrapper.emitted("enter-cluster")[0]).toEqual([1]);
  });

  it("emits create-cluster event when create button is clicked", async () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        clusters: [],
        loading: false,
      },
    });

    await wrapper.find(".empty-state .el-button").trigger("click");
    expect(wrapper.emitted("create-cluster")).toBeTruthy();
  });

  it("emits edit-cluster event when edit button is clicked", async () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    const editButton = wrapper.find(".cluster-operations .el-button");
    await editButton.trigger("click");
    expect(wrapper.emitted("edit-cluster")).toBeTruthy();
  });

  it("emits test-connection event when connection test button is clicked", async () => {
    const wrapper = mount(ClusterList, {
      props: defaultProps,
    });

    const connectionButton = wrapper.findAll(
      ".cluster-operations .el-button",
    )[0];
    await connectionButton.trigger("click");
    expect(wrapper.emitted("test-connection")).toBeTruthy();
    expect(wrapper.emitted("test-connection")[0]).toEqual([
      mockClusters[0],
      "enhanced",
    ]);
  });

  it("displays redirect notice when redirectUrl is provided", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        redirectUrl: "/dashboard",
      },
    });

    expect(wrapper.find(".cluster-selection-notice").exists()).toBe(true);
    expect(wrapper.text()).toContain("请选择要使用的集群");
  });

  it("handles missing cluster stats gracefully", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        clusterStats: {},
      },
    });

    const firstCluster = wrapper.find(".cluster-card");
    // Should show 0 for missing stats
    expect(firstCluster.findAll(".stat-value")[0].text()).toBe("0");
  });

  it("handles missing connection status gracefully", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        connectionStatus: {},
      },
    });

    // Should not throw errors when connection status is missing
    expect(wrapper.find(".cluster-card").exists()).toBe(true);
  });

  it("filters clusters by both search text and status", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        searchText: "Test",
        statusFilter: "active",
      },
    });

    expect(wrapper.findAll(".cluster-card")).toHaveLength(1);
    expect(wrapper.find(".cluster-name").text()).toBe("Test Cluster 1");
  });

  it("case insensitive search", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        searchText: "test cluster 1",
      },
    });

    expect(wrapper.findAll(".cluster-card")).toHaveLength(1);
    expect(wrapper.find(".cluster-name").text()).toBe("Test Cluster 1");
  });

  it("searches in description field", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        searchText: "Another",
      },
    });

    expect(wrapper.findAll(".cluster-card")).toHaveLength(1);
    expect(wrapper.find(".cluster-name").text()).toBe("Test Cluster 2");
  });

  it("searches in host field", () => {
    const wrapper = mount(ClusterList, {
      props: {
        ...defaultProps,
        searchText: "test-host-2",
      },
    });

    expect(wrapper.findAll(".cluster-card")).toHaveLength(1);
    expect(wrapper.find(".cluster-name").text()).toBe("Test Cluster 2");
  });
});
