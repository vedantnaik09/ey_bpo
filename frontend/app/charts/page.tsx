"use client"
import React, { useState, useEffect } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Tooltip,
    Legend,
    Title,
} from 'chart.js';
import { Line, Pie, Doughnut, Bubble, Scatter } from 'react-chartjs-2';
// Import the box/violin plot plugin (ensure it's installed)
import 'chartjs-chart-box-and-violin-plot';
// Import shadcn UI components (adjust the import path as needed)
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Tooltip,
    Legend,
    Title
);

/* Helper component that truncates text if it is too long and provides
   a toggle to show the full text. */
interface TruncatedTextProps {
    text: string;
    limit?: number;
}

const TruncatedText: React.FC<TruncatedTextProps> = ({ text, limit = 30 }) => {
    const [expanded, setExpanded] = useState(false);
    if (text.length <= limit) {
        return <span>{text}</span>;
    }
    const displayText = expanded ? text : text.slice(0, limit) + '...';
    return (
        <span>
            {displayText}{' '}
            <button
                onClick={() => setExpanded(!expanded)}
                className="text-blue-500 underline focus:outline-none"
            >
                {expanded ? 'Show Less' : 'Show More'}
            </button>
        </span>
    );
};

// Data interfaces
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

// Helper function to safely set state ensuring an array is always used.
function safeSetState<T>(data: any, setter: (val: T[]) => void) {
    if (Array.isArray(data)) {
        setter(data);
    } else if (data) {
        setter([data]);
    } else {
        setter([]);
    }
}

const ComplaintsDashboard: React.FC = () => {
    // States for each endpoint
    const [trendData, setTrendData] = useState<TrendData[]>([]);
    const [categoriesData, setCategoriesData] = useState<CategoryData[]>([]);
    const [resolutionData, setResolutionData] = useState<ResolutionData[]>([]);
    const [priorityData, setPriorityData] = useState<PriorityData[]>([]);
    const [statusData, setStatusData] = useState<StatusData[]>([]);
    const [pastVsUrgencyData, setPastVsUrgencyData] = useState<PastVsUrgencyData[]>([]);

    useEffect(() => {
        // Fetch Complaint Trends Over Time
        fetch('http://localhost:8000/complaints/trends')
            .then((res) => res.json())
            .then((data) => safeSetState<TrendData>(data, setTrendData))
            .catch((err) => console.error("Error fetching trends:", err));

        // Fetch Complaint Categories Breakdown
        fetch('http://localhost:8000/complaints/categories')
            .then((res) => res.json())
            .then((data) => safeSetState<CategoryData>(data, setCategoriesData))
            .catch((err) => console.error("Error fetching categories:", err));

        // Fetch Complaint Resolution Time Analysis
        fetch('http://localhost:8000/complaints/resolution_time')
            .then((res) => res.json())
            .then((data) => safeSetState<ResolutionData>(data, setResolutionData))
            .catch((err) => console.error("Error fetching resolution data:", err));

        // Fetch Priority Score vs Resolution Speed
        fetch('http://localhost:8000/complaints/priority_vs_resolution')
            .then((res) => res.json())
            .then((data) => safeSetState<PriorityData>(data, setPriorityData))
            .catch((err) => console.error("Error fetching priority data:", err));

        // Fetch Status Distribution of Complaints
        fetch('http://localhost:8000/complaints/status_distribution')
            .then((res) => res.json())
            .then((data) => safeSetState<StatusData>(data, setStatusData))
            .catch((err) => console.error("Error fetching status data:", err));

        // Fetch Past Complaints vs Current Urgency
        fetch('http://localhost:8000/complaints/past_vs_urgency')
            .then((res) => res.json())
            .then((data) => safeSetState<PastVsUrgencyData>(data, setPastVsUrgencyData))
            .catch((err) => console.error("Error fetching past vs urgency data:", err));
    }, []);

    // 1. Complaint Trends Over Time (Line Chart)
    const lineChartData = {
        labels: trendData.map((item) => item.date),
        datasets: [
            {
                label: 'Complaints',
                data: trendData.map((item) => item.count),
                fill: false,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
            },
        ],
    };

    // 2. Complaint Categories Breakdown (Pie Chart)
    const pieChartData = {
        labels: categoriesData.map((item) => item.category),
        datasets: [
            {
                label: 'Complaint Categories',
                data: categoriesData.map((item) => item.count),
                backgroundColor: [
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(54, 162, 235, 0.6)',
                    // Additional colors can be added here
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                ],
                borderWidth: 1,
            },
        ],
    };

    // 3. Complaint Resolution Time Analysis (Box Plot)
    const resolutionTimes = resolutionData.map((item) => item.resolution_time);
    const sortedResolutionTimes = [...resolutionTimes].sort((a, b) => a - b);
    const computeBoxPlotStats = (data: number[]) => {
        if (data.length === 0) return null;
        const min = data[0];
        const max = data[data.length - 1];
        const median = data[Math.floor(data.length / 2)];
        const q1 = data[Math.floor(data.length / 4)];
        const q3 = data[Math.floor(data.length * 3 / 4)];
        return { min, q1, median, q3, max };
    };
    const boxPlotStats = computeBoxPlotStats(sortedResolutionTimes);
    const boxPlotData = {
        labels: ['Resolution Time'],
        datasets: [
            {
                label: 'Resolution Time (days)',
                data: boxPlotStats ? [boxPlotStats] : [],
                backgroundColor: 'rgba(75,192,192,0.4)',
            },
        ],
    };

    // 4. Status Distribution of Complaints (Doughnut Chart)
    const doughnutChartData = {
        labels: statusData.map((item) => item.status),
        datasets: [
            {
                label: 'Status Distribution',
                data: statusData.map((item) => item.count),
                backgroundColor: ['rgba(153, 102, 255, 0.6)'],
                borderColor: ['rgba(153, 102, 255, 1)'],
                borderWidth: 1,
            },
        ],
    };

    // 5. Past Complaints vs Current Urgency (Bubble Chart) – Improved Styling
    const bubbleChartData = {
        datasets: pastVsUrgencyData.map((item, index) => ({
            label: `Record ${index + 1}`,
            data: [
                {
                    x: item.past_count,
                    y: item.priority_score,
                    r: item.priority_score * 12, // Adjusted scale factor for better visibility
                },
            ],
            backgroundColor: 'rgba(255, 159, 64, 0.7)',
            borderColor: 'rgba(255, 159, 64, 1)',
            borderWidth: 1,
            hoverRadius: 8,
        })),
    };

    const bubbleOptions = {
        responsive: true,
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
                position: 'top' as const,
            },
            title: {
                display: true,
                text: 'Past Complaints vs Current Urgency',
                font: { size: 16 },
            },
        },
        scales: {
            x: {
                title: { display: true, text: 'Past Complaints' },
                grid: { color: 'rgba(200,200,200,0.2)' },
            },
            y: {
                title: { display: true, text: 'Urgency Score' },
                grid: { color: 'rgba(200,200,200,0.2)' },
                min: 0,
                max: 1,
            },
        },
    };

    // 6. Priority Score vs Resolution Speed (Scatter Chart) – Improved Styling
    const scatterChartData = {
        datasets: [
            {
                label: 'Priority vs Scheduling Time',
                data: priorityData.map((item: PriorityData) => ({
                    x: item.priority_score,
                    y: item.scheduling_time,
                })),
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                pointRadius: 6,
                pointHoverRadius: 8,
            },
        ],
    };

    const scatterOptions = {
        responsive: true,
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
                position: 'top' as const,
            },
            title: {
                display: true,
                text: 'Priority Score vs Resolution Speed',
                font: { size: 16 },
            },
        },
        scales: {
            x: {
                title: { display: true, text: 'Priority Score' },
                grid: { color: 'rgba(200,200,200,0.2)' },
                min: 0,
                max: 1,
            },
            y: {
                title: { display: true, text: 'Scheduling/Resolution Time (days)' },
                grid: { color: 'rgba(200,200,200,0.2)' },
            },
        },
    };

    return (
        <div className="p-4">
            <h1 className="text-3xl font-bold mb-4">Complaints Dashboard</h1>
            {/* Grid container for 2-column layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className='max-h-max'>
                    <CardHeader>
                        <CardTitle>Complaint Trends Over Time</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Line data={lineChartData} />
                    </CardContent>
                </Card>

                <Card className='max-h-max'>
                    <CardHeader>
                        <CardTitle>Complaint Resolution Time Analysis</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Line
                            data={boxPlotData}
                            options={{
                                plugins: {
                                    tooltip: {
                                        callbacks: {
                                            label: (context: any) => {
                                                const { min, q1, median, q3, max } = context.raw;
                                                return `Min: ${min}, Q1: ${q1}, Median: ${median}, Q3: ${q3}, Max: ${max}`;
                                            },
                                        },
                                    },
                                },
                            }}
                        />
                    </CardContent>
                </Card>


                <Card className='max-h-max'>
                    <CardHeader>
                        <CardTitle>Past Complaints vs Current Urgency</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Bubble data={bubbleChartData} options={bubbleOptions} />
                    </CardContent>
                </Card>

                <Card className='max-h-max'>
                    <CardHeader>
                        <CardTitle>Priority Score vs Resolution Speed</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Scatter data={scatterChartData} options={scatterOptions} />
                    </CardContent>
                </Card>
                <Card className='max-h-max'>
                    <CardHeader>
                        <CardTitle>Complaint Categories Breakdown</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="mb-2">
                            <strong>Categories: </strong>
                            {categoriesData.map((item, idx) => (
                                <div key={idx}>
                                    <TruncatedText text={item.category} limit={40} /> - {item.count}
                                </div>
                            ))}
                        </div>
                        <Pie data={pieChartData} />
                    </CardContent>
                </Card>


                <Card className='max-h-max'>
                    <CardHeader>
                        <CardTitle>Status Distribution of Complaints</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Doughnut data={doughnutChartData} />
                    </CardContent>
                </Card>


            </div>
        </div>
    );
};

export default ComplaintsDashboard;
