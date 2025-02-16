"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { format, parseISO, add } from "date-fns";
import { toast } from "sonner";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "@/firebase/config";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import Calendar from "@/components/ui/calendar";
import RescheduleCalendar from "@/components/ui/reschedulecalendar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import axiosManagerInstance from "@/utils/axiosManager";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Phone, CheckCircle, XCircle, Users, AlertCircle, CheckCircle2, Flag } from "lucide-react";
import { Badge } from "@/components/ui/badge";

// ==========================
// Chart.js & React Chart Imports
// ==========================
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, ArcElement, Tooltip as ChartTooltip, Legend, Title } from "chart.js";
import { Line, Pie, Doughnut, Bubble, Scatter } from "react-chartjs-2";
import "chartjs-chart-box-and-violin-plot";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, ChartTooltip, Legend, Title);

const CHART_HEIGHT = "300px";

// ==========================
// Type Definitions & Constants
// ==========================

// For the table and main dashboard
interface Complaint {
  complaint_id: number;
  ticket_id: string;
  is_escalated?: boolean; // optional if not used
  customer_name: string;
  customer_phone_number: string;
  complaint_description: string;
  sentiment_score: number;
  urgency_score: number;
  priority_score: number;
  status: string;
  scheduled_callback: string | null;
  created_at: string;
  knowledge_base_solution: string;
  past_count: number;
  complaint_category: string;
}

// For domain filtering
interface DomainOption {
  value: string;
  label: string;
}

const domainOptions: DomainOption[] = [
  { value: "all", label: "All Categories" },
  { value: "Technical Support", label: "Technical Support" },
  { value: "Billing", label: "Billing" },
  { value: "New Connection", label: "New Connection" },
  { value: "Added Service and Bundle offers", label: "Added Service and Bundle offers" },
];

const API_BASE_URL = "http://localhost:8000";

// ===========================
// Chart-Related Types
// ===========================
interface TrendData {
  date: string;
  count: number;
}

interface CategoryData {
  category: string;
  count: number;
}

interface ResolutionData {
  created_at: string;
  scheduled_callback: string;
  resolution_time: number;
  priority_score: number;
}

interface PriorityData {
  priority_score: number;
  scheduling_time: number;
}

interface StatusData {
  status: string;
  count: number;
}

interface PastVsUrgencyData {
  past_count: number;
  priority_score: number;
}

// ==========================
// Helper Functions
// ==========================
const getSeverityColor = (severity: number): string => {
  if (severity >= 0.8) return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  if (severity >= 0.5) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
  return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
};

const getPriorityColor = (priority: number): string => {
  if (priority >= 0.7) return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  if (priority >= 0.4) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
  return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
};

const formatToIST = (dateString: string): string => {
  if (!dateString) return "Not Scheduled";
  const date = parseISO(dateString);
  const istDate = add(date, { hours: 5, minutes: 30 });
  return format(istDate, "dd-MM-yyyy");
};

const formatToISTstartWithYear = (dateString: string): string => {
  if (!dateString) return "Not Scheduled";
  const date = parseISO(dateString);
  const istDate = add(date, { hours: 5, minutes: 30 });
  return format(istDate, "yyyy-MM-dd");
};

const formatToISTWithTime = (dateString: string): string => {
  if (!dateString) return "Not Scheduled";
  const date = parseISO(dateString);
  const istDate = add(date, { hours: 5, minutes: 30 });
  return format(istDate, "dd-MM-yyyy HH:mm");
};

function processComplaints(complaints: Complaint[]): Complaint[] {
  const ticketMap = new Map<string, Complaint>();
  complaints.forEach((complaint) => {
    const baseTicketId = complaint.ticket_id.trim();
    const key = `${baseTicketId}-${complaint.customer_phone_number}`;
    if (!ticketMap.has(key) || complaint.past_count > (ticketMap.get(key)?.past_count || 0)) {
      ticketMap.set(key, complaint);
    }
  });
  return Array.from(ticketMap.values());
}

// Helpers for chart data setting
function safeSetState<T>(data: any, setter: (val: T[]) => void) {
  if (Array.isArray(data)) {
    setter(data);
  } else if (data) {
    setter([data]);
  } else {
    setter([]);
  }
}

// TruncatedText fix: allow text to be optional, default to ""
interface TruncatedTextProps {
  text?: string;
  limit?: number;
}
const TruncatedText: React.FC<TruncatedTextProps> = ({ text = "", limit = 30 }) => {
  const [expanded, setExpanded] = useState(false);
  if (text.length <= limit) return <span>{text}</span>;

  const displayText = expanded ? text : text.slice(0, limit) + "...";
  return (
    <span>
      {displayText}{" "}
      <button onClick={() => setExpanded(!expanded)} className="text-blue-500 underline focus:outline-none">
        {expanded ? "Show Less" : "Show More"}
      </button>
    </span>
  );
};

// ==========================
// Complaints Dashboard Charts
// ==========================
const ComplaintsDashboardCharts: React.FC = () => {
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [categoriesData, setCategoriesData] = useState<CategoryData[]>([]);
  const [resolutionData, setResolutionData] = useState<ResolutionData[]>([]);
  const [priorityData, setPriorityData] = useState<PriorityData[]>([]);
  const [statusData, setStatusData] = useState<StatusData[]>([]);
  const [pastVsUrgencyData, setPastVsUrgencyData] = useState<PastVsUrgencyData[]>([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/complaints/trends`)
      .then((res) => res.json())
      .then((data) => safeSetState<TrendData>(data, setTrendData))
      .catch((err) => console.error("Error fetching trends:", err));

    fetch(`${API_BASE_URL}/complaints/categories`)
      .then((res) => res.json())
      .then((data) => safeSetState<CategoryData>(data, setCategoriesData))
      .catch((err) => console.error("Error fetching categories:", err));

    fetch(`${API_BASE_URL}/complaints/resolution_time`)
      .then((res) => res.json())
      .then((data) => safeSetState<ResolutionData>(data, setResolutionData))
      .catch((err) => console.error("Error fetching resolution data:", err));

    fetch(`${API_BASE_URL}/complaints/priority_vs_resolution`)
      .then((res) => res.json())
      .then((data) => safeSetState<PriorityData>(data, setPriorityData))
      .catch((err) => console.error("Error fetching priority data:", err));

    fetch(`${API_BASE_URL}/complaints/status_distribution`)
      .then((res) => res.json())
      .then((data) => safeSetState<StatusData>(data, setStatusData))
      .catch((err) => console.error("Error fetching status data:", err));

    fetch(`${API_BASE_URL}/complaints/past_vs_urgency`)
      .then((res) => res.json())
      .then((data) => safeSetState<PastVsUrgencyData>(data, setPastVsUrgencyData))
      .catch((err) => console.error("Error fetching past vs urgency data:", err));
  }, []);

  // Chart 1: Complaint Trends Over Time (Line)
  const lineChartData = {
    labels: trendData.map((item) => item.date),
    datasets: [
      {
        label: "Complaints",
        data: trendData.map((item) => item.count),
        fill: false,
        borderColor: "rgb(75, 192, 192)",
        tension: 0.1,
      },
    ],
  };

  // Chart 2: Complaint Categories Breakdown (Pie)
  const pieChartData = {
    labels: categoriesData.map((item) => item.category),
    datasets: [
      {
        label: "Complaint Categories",
        data: categoriesData.map((item) => item.count),
        backgroundColor: ["rgba(255, 99, 132, 0.6)", "rgba(54, 162, 235, 0.6)"],
        borderColor: ["rgba(255, 99, 132, 1)", "rgba(54, 162, 235, 1)"],
        borderWidth: 1,
      },
    ],
  };

  const resolutionChartData = {
    labels: resolutionData.map((item) => new Date(item.created_at).toLocaleDateString()),
    datasets: [
      {
        label: "Resolution Time (hours)",
        data: resolutionData.map((item) => item.resolution_time),
        fill: false,
        borderColor: "rgb(75, 192, 192)",
        tension: 0.1,
        pointRadius: 5,
        pointHoverRadius: 8,
      },
    ],
  };

  const resolutionChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const dataPoint = resolutionData[context.dataIndex];
            return [`Resolution Time: ${dataPoint.resolution_time.toFixed(2)} hours`, `Priority Score: ${dataPoint.priority_score.toFixed(2)}`];
          },
        },
      },
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: "Resolution Time Analysis",
        font: { size: 16 },
      },
    },
    scales: {
      x: {
        title: { display: true, text: "Date" },
        grid: { color: "rgba(200,200,200,0.2)" },
      },
      y: {
        title: { display: true, text: "Resolution Time (hours)" },
        grid: { color: "rgba(200,200,200,0.2)" },
        beginAtZero: true,
      },
    },
  };

  // Chart 4: Status Distribution of Complaints (Doughnut)
  const statusColorMap: { [key: string]: { background: string; border: string } } = {
    resolved: {
      background: "rgba(75, 192, 192, 0.6)",
      border: "rgba(75, 192, 192, 1)",
    },
    pending: {
      background: "rgba(255, 205, 86, 0.6)",
      border: "rgba(255, 205, 86, 1)",
    },
  };

  const backgroundColors = statusData.map((item) => {
    const lowerStatus = (item.status || "").toLowerCase();
    if (statusColorMap[lowerStatus]) {
      return statusColorMap[lowerStatus].background;
    }
    return "rgba(153, 102, 255, 0.6)";
  });

  const borderColors = statusData.map((item) => {
    const lowerStatus = (item.status || "").toLowerCase();
    if (statusColorMap[lowerStatus]) {
      return statusColorMap[lowerStatus].border;
    }
    return "rgba(153, 102, 255, 1)";
  });

  const doughnutChartData = {
    labels: statusData.map((item) => item.status || "Unknown"),
    datasets: [
      {
        label: "Status Distribution",
        data: statusData.map((item) => item.count),
        backgroundColor: backgroundColors,
        borderColor: borderColors,
        borderWidth: 1,
      },
    ],
  };

  // Chart 5: Past Complaints vs Current Urgency (Bubble)
  const bubbleChartData = {
    datasets: pastVsUrgencyData.map((item, index) => ({
      label: `Record ${index + 1}`,
      data: [
        {
          x: item.past_count,
          y: item.priority_score,
          r: item.priority_score * 12,
        },
      ],
      backgroundColor: "rgba(255, 159, 64, 0.7)",
      borderColor: "rgba(255, 159, 64, 1)",
      borderWidth: 1,
      hoverRadius: 8,
    })),
  };

  const bubbleOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const { x, y, r } = context.raw;
            return `Past: ${x}, Urgency: ${y.toFixed(2)} (Size: ${r})`;
          },
        },
      },
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: "Past Complaints vs Current Urgency",
        font: { size: 16 },
      },
    },
    scales: {
      x: {
        title: { display: true, text: "Past Complaints" },
        grid: { color: "rgba(200,200,200,0.2)" },
      },
      y: {
        title: { display: true, text: "Urgency Score" },
        grid: { color: "rgba(200,200,200,0.2)" },
        min: 0,
        max: 1,
      },
    },
  };

  // Chart 6: Priority Score vs Resolution Speed (Scatter)
  const scatterChartData = {
    datasets: [
      {
        label: "Priority vs Scheduling Time",
        data: priorityData.map((item: PriorityData) => ({
          x: item.priority_score,
          y: item.scheduling_time,
        })),
        backgroundColor: "rgba(54, 162, 235, 0.7)",
        borderColor: "rgba(54, 162, 235, 1)",
        pointRadius: 6,
        pointHoverRadius: 8,
      },
    ],
  };

  const scatterOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const { x, y } = context.raw;
            return `Priority: ${x.toFixed(2)}, Scheduling: ${y.toFixed(2)} days`;
          },
        },
      },
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: "Priority Score vs Resolution Speed",
        font: { size: 16 },
      },
    },
    scales: {
      x: {
        title: { display: true, text: "Priority Score" },
        grid: { color: "rgba(200,200,200,0.2)" },
        min: 0,
        max: 1,
      },
      y: {
        title: { display: true, text: "Scheduling/Resolution Time (hours)" },
        grid: { color: "rgba(200,200,200,0.2)" },
      },
    },
  };

  return (
    <div className="p-4">
      <h1 className="text-3xl font-bold mb-4">Complaints Dashboard Charts</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Chart 1 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Complaint Trends Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ height: CHART_HEIGHT }}>
              <Line data={lineChartData} options={{ maintainAspectRatio: false }} />
            </div>
          </CardContent>
        </Card>

        {/* Chart 2 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Complaint Resolution Time Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ height: CHART_HEIGHT }}>
              <Line data={resolutionChartData} options={resolutionChartOptions} />
            </div>
          </CardContent>
        </Card>

        {/* Chart 3 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Past Complaints vs Current Urgency</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ height: CHART_HEIGHT }}>
              <Bubble data={bubbleChartData} options={bubbleOptions} />
            </div>
          </CardContent>
        </Card>

        {/* Chart 4 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Priority Score vs Resolution Speed</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ height: CHART_HEIGHT }}>
              <Scatter data={scatterChartData} options={scatterOptions} />
            </div>
          </CardContent>
        </Card>

        {/* Chart 5 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Complaint Categories Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-2">
              <strong>Categories: </strong>
              {categoriesData.map((item, idx) => (
                <div key={idx}>
                  {/* Provide fallback for `item.category` */}
                  <TruncatedText text={item.category || ""} limit={40} /> - {item.count}
                </div>
              ))}
            </div>
            <div style={{ height: CHART_HEIGHT }}>
              <Pie data={pieChartData} options={{ maintainAspectRatio: false }} />
            </div>
          </CardContent>
        </Card>

        {/* Chart 6 */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Status Distribution of Complaints</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ height: CHART_HEIGHT }}>
              <Doughnut data={doughnutChartData} options={{ maintainAspectRatio: false }} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// ==========================
// Main Dashboard Page
// ==========================
export default function DashboardPage() {
  const { push } = useRouter();

  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState<{ [key: number]: boolean }>({});
  const [date, setDate] = useState<Date>(new Date());
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint[] | null>(null);
  const [rescheduleComplaintId, setRescheduleComplaintId] = useState<number | null>(null);
  const [hoveredComplaintId, setHoveredComplaintId] = useState<number | null>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [userRole, setUserRole] = useState<string>("");
  const [userDomain, setUserDomain] = useState<string>("");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  // On mount, check auth
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        push("/");
      } else {
        // Refresh token
        const token = await user.getIdToken(true);
        localStorage.setItem("firebaseToken", token);

        // Retrieve role/domain
        const role = localStorage.getItem("userRole");
        const domain = localStorage.getItem("userDomain");
        setUserRole(role || "");
        setUserDomain(domain || "");

        // If employee, limit domain
        if (role === "employee" && domain) {
          setSelectedDomain(domain);
        }
        setIsAuthenticated(true);
      }
    });
    return () => unsubscribe();
  }, [push]);

  // If authenticated, fetch complaints
  useEffect(() => {
    if (isAuthenticated) {
      fetchComplaints();
    }
  }, [isAuthenticated]);

  // Re-fetch if domain changes
  useEffect(() => {
    if (isAuthenticated) {
      fetchComplaints();
    }
  }, [selectedDomain, isAuthenticated]);

  // Also handle localStorage changes (just in case)
  useEffect(() => {
    const role = localStorage.getItem("userRole");
    const domain = localStorage.getItem("userDomain");
    setUserRole(role || "");
    setUserDomain(domain || "");
    if (role === "employee" && domain) {
      setSelectedDomain(domain);
    }
  }, []);

  // If we have new complaints, pick today's
  useEffect(() => {
    if (complaints.length > 0) {
      const todayComplaints = getDayComplaints(new Date());
      setSelectedComplaint(todayComplaints);
    }
  }, [complaints]);

  const fetchComplaints = async () => {
    try {
      const response = await axiosManagerInstance.get(`/complaints/by-category/${selectedDomain}`);
      const processedData = processComplaints(response.data);
      setComplaints(processedData);
    } catch (error) {
      console.error("Error fetching complaints:", error);
      toast.error("Failed to fetch complaints");
    }
  };

  const getDayComplaints = (day: Date): Complaint[] => {
    const formattedDay = format(day, "yyyy-MM-dd");
    return complaints.filter((c) => (c.scheduled_callback ? formatToISTstartWithYear(c.scheduled_callback).startsWith(formattedDay) : false));
  };

  const handleOpenReschedule = (id: number) => {
    setRescheduleComplaintId(id);
  };

  const handleCloseReschedule = () => {
    setRescheduleComplaintId(null);
  };

  const handleMouseEnter = (event: React.MouseEvent, complaintId: number) => {
    const rect = (event.target as HTMLElement).getBoundingClientRect();
    setPosition({
      top: rect.top + window.scrollY,
      left: rect.left + window.scrollX,
    });
    setHoveredComplaintId(complaintId);
  };

  const handleMouseLeave = () => {
    setHoveredComplaintId(null);
    setPosition(null);
  };

  const handleCall = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    try {
      const response = await axiosManagerInstance.post(`/complaints/${id}/resolve`);
      if (response.status === 200) {
        fetchComplaints();
        toast.success("Calling User");
      }
    } catch (error) {
      toast.error("Failed to call");
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const toggleResolve = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    try {
      const response = await axiosManagerInstance.post(`/complaints/${id}/toggleResolve`);
      if (response.status === 200) {
        fetchComplaints();
        toast.success("Complaint marked as resolved");
      }
    } catch (error) {
      toast.error("Failed to resolve complaint");
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  // Summaries
  const totalComplaints = complaints.length;
  const resolvedComplaints = complaints.filter((c) => c.status === "resolved").length;
  const unresolvedComplaints = totalComplaints - resolvedComplaints;

  // Domain filter for admin only
  const renderDomainFilter = () => {
    if (userRole !== "admin") return null;
    return (
      <div className="mb-2">
        <Select value={selectedDomain} onValueChange={(value) => setSelectedDomain(value)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Select Category" />
          </SelectTrigger>
          <SelectContent>
            {domainOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8 relative">
      {/* Summary Cards */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 bg-white dark:bg-gray-800">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900">
                <Users className="h-6 w-6 text-purple-600 dark:text-purple-300" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Complaints</p>
                <p className="text-2xl font-bold">{totalComplaints}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-white dark:bg-gray-800">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-green-100 dark:bg-green-900">
                <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-300" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Resolved</p>
                <p className="text-2xl font-bold">{resolvedComplaints}</p>
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-white dark:bg-gray-800">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-red-100 dark:bg-red-900">
                <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-300" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Unresolved</p>
                <p className="text-2xl font-bold">{unresolvedComplaints}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Admin Domain Filter */}

      {/* Charts Section */}
      {userRole !== "employee" && (
        <Card className="mb-8 bg-white dark:bg-gray-800">
          <CardContent>
            <ComplaintsDashboardCharts />
          </CardContent>
        </Card>
      )}

      {/* Complaints Table */}
      <Card className="bg-white dark:bg-gray-800 mb-8">
        {renderDomainFilter()}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer</TableHead>
              {userRole !== "employee" && <TableHead>Category</TableHead>}
              <TableHead>Phone Number</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Callback</TableHead>
              <TableHead>Sentiment</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Repeat Customer</TableHead>
              <TableHead>Knowledge base solution</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {complaints.map((complaint) => (
              <TableRow key={complaint.complaint_id}>
                <TableCell className="font-medium">{complaint.customer_name}</TableCell>
                {userRole !== "employee" ? <TableCell className="font-medium">{complaint.complaint_category}</TableCell> : null}
                <TableCell>{complaint.customer_phone_number}</TableCell>
                <TableCell>{complaint.complaint_description}</TableCell>
                <TableCell className="whitespace-nowrap">{formatToIST(complaint.created_at)}</TableCell>
                <TableCell>
                  <div className="text-center">{complaint.scheduled_callback ? formatToIST(complaint.scheduled_callback) : "Not Scheduled"}</div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleOpenReschedule(complaint.complaint_id)}
                    className="text-blue-500 hover:bg-background"
                  >
                    Reschedule
                  </Button>
                </TableCell>
                <TableCell>
                  <Badge className={getSeverityColor(complaint.priority_score)}>{(complaint.priority_score * 100).toFixed(0)}%</Badge>
                </TableCell>
                <TableCell>
                  <Badge className={getPriorityColor(complaint.priority_score)}>
                    {complaint.priority_score >= 0.7 ? "High" : complaint.priority_score >= 0.4 ? "Medium" : "Low"}
                  </Badge>
                </TableCell>
                <TableCell>
                  {complaint.status === "resolved" ? <CheckCircle className="h-5 w-5 text-green-500" /> : <XCircle className="h-5 w-5 text-red-500" />}
                </TableCell>
                <TableCell>
                  {complaint.past_count > 1 ? (
                    <div className="flex items-center">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <Flag className="h-4 w-4 text-red-500 mr-2" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Ticket ID: {complaint.ticket_id}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      <Badge variant="destructive" className="mr-2">
                        Repeat
                      </Badge>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">New Customer</span>
                  )}
                </TableCell>
                <TableCell>
                  {/* Tooltip for Knowledge Base Solution */}
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger className="cursor-pointer text-blue-500 underline">View Solution</TooltipTrigger>
                      <TooltipContent className="max-w-xs text-sm">{complaint.knowledge_base_solution || "No solution available"}</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </TableCell>
                <TableCell>
                  <div className={`flex gap-2 ${complaint.status === "resolved" ? "" : "justify-end"}`}>
                    {complaint.status === "resolved" ? (
                      <div
                        className="group relative self-center ml-3"
                        onMouseEnter={(e) => handleMouseEnter(e, complaint.complaint_id)}
                        onMouseLeave={handleMouseLeave}
                        style={{ cursor: "pointer" }}
                      >
                        <span className="h-5 w-5 rounded-full bg-blue-500 text-white flex items-center justify-center">i</span>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleCall(complaint.complaint_id)}
                        disabled={loading[complaint.complaint_id]}
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
                      >
                        <Phone className="h-4 w-4 mr-2" />
                        Call
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => toggleResolve(complaint.complaint_id)}
                      disabled={loading[complaint.complaint_id]}
                      className={`border-green-500 text-green-500 hover:bg-green-50 dark:hover:bg-green-950 ${complaint.status !== "resolved" ? "mr-20" : ""}`}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      {complaint.status !== "resolved" ? "Resolve" : "Mark as unresolved"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {hoveredComplaintId !== null && position && (
          <div
            className="absolute bg-gray-700 text-white text-xs rounded-md p-2 w-[200px]"
            style={{
              top: position.top + 30,
              left: position.left - 80,
            }}
          >
            {complaints.find((c) => c.complaint_id === hoveredComplaintId)?.knowledge_base_solution}
          </div>
        )}
      </Card>

      {/* Reschedule Modal */}
      {rescheduleComplaintId && <RescheduleCalendar complaintId={rescheduleComplaintId} onClose={handleCloseReschedule} onReschedule={fetchComplaints} />}

      {/* Calendar & Details */}
      <Card className="bg-white dark:bg-gray-800 p-6">
        <div className="flex flex-col md:flex-row gap-8">
          <div className="flex-1 max-w-xl">
            <h2 className="text-xl font-semibold mb-4">Complaint Calendar</h2>
            <Calendar
              selected={date}
              onSelect={(newDate) => {
                if (newDate) {
                  setDate(newDate);
                  const complaintsForDay = getDayComplaints(newDate);
                  setSelectedComplaint(complaintsForDay || null);
                }
              }}
              className="rounded-md border"
              complaints={complaints}
              defaultMonth={new Date()}
            />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold mb-4">Selected Date Details</h2>
            {date && selectedComplaint && selectedComplaint.length > 0 ? (
              <div className="space-y-4">
                {selectedComplaint.map((complaint) => (
                  <div key={complaint.complaint_id} className="p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-lg">{complaint.customer_name}</h3>
                      <Badge className={getSeverityColor(complaint.priority_score)}>Sentiment: {(complaint.priority_score * 100).toFixed(0)}%</Badge>
                    </div>
                    <p className="text-base text-gray-600 dark:text-gray-400 mb-4">{complaint.complaint_description}</p>
                    <div className="flex justify-between items-center">
                      <p className="text-base">
                        <strong>Call Scheduled:</strong> {complaint.scheduled_callback ? formatToISTWithTime(complaint.scheduled_callback) : "Not Scheduled"}
                      </p>
                      <Badge className={getPriorityColor(complaint.priority_score)}>
                        {complaint.priority_score >= 0.7 ? "High Priority" : complaint.priority_score >= 0.4 ? "Medium Priority" : "Low Priority"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">{date ? "No complaints found for this date" : "Select a date to view complaint details"}</p>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
