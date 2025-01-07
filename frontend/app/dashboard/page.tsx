"use client";

import { useState } from "react";
import { format } from "date-fns";
import { Card } from "@/components/ui/card";
import Calendar from "@/components/ui/calendar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Phone,
  CheckCircle,
  XCircle,
  Users,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

interface Complaint {
  id: number;
  customerName: string;
  phone: string;
  subject: string;
  date: string;
  callScheduled: string | null;
  severity: number;
  priority: "Low" | "Medium" | "High" | "Critical";
  resolved: boolean;
}

const baseComplaints: Complaint[] = [
  {
    id: 1,
    customerName: "John Doe",
    phone: "+1234567890",
    subject: "Network Connectivity Issues",
    date: "20-03-2025",
    callScheduled: "22-03-2025",
    severity: 0.8,
    priority: "High",
    resolved: false,
  },
  {
    id: 2,
    customerName: "Jane Smith",
    phone: "+1234567891",
    subject: "Billing Discrepancy",
    date: "19-03-2025",
    callScheduled: "21-03-2025",
    severity: 0.5,
    priority: "Medium",
    resolved: true,
  },
  {
    id: 3,
    customerName: "Robert Johnson",
    phone: "+1234567892",
    subject: "Service Outage",
    date: "20-03-2025",
    callScheduled: null,
    severity: 1.0,
    priority: "Critical",
    resolved: false,
  },
  {
    id: 4,
    customerName: "Sarah Williams",
    phone: "+1234567893",
    subject: "Account Access",
    date: "18-03-2025",
    callScheduled: "23-03-2025",
    severity: 0.3,
    priority: "Low",
    resolved: false,
  },
  {
    id: 5,
    customerName: "Michael Brown",
    phone: "+1234567894",
    subject: "Product Malfunction",
    date: "17-03-2025",
    callScheduled: "19-03-2025",
    severity: 0.7,
    priority: "High",
    resolved: true,
  },
];

const getSeverityColor = (severity: number): string => {
  if (severity >= 0.8)
    return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  if (severity >= 0.5)
    return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
  return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
};

const getPriorityColor = (priority: string): string => {
  switch (priority) {
    case "Critical":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    case "High":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
    case "Medium":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    default:
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
  }
};

export default function DashboardPage() {
  const [complaints, setComplaints] = useState<Complaint[]>(baseComplaints);
  const [loading, setLoading] = useState<{ [key: number]: boolean }>({});
  const [date, setDate] = useState<Date | undefined>(new Date());
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(
    null
  );

  const totalComplaints = complaints.length;
  const resolvedComplaints = complaints.filter((c) => c.resolved).length;
  const unresolvedComplaints = totalComplaints - resolvedComplaints;

  const handleCall = async (phone: string, id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // TODO: Replace with actual API call
      // await fetch('/api/call', {
      //   method: 'POST',
      //   body: JSON.stringify({ phone })
      // });
      toast.success("Call initiated successfully");
    } catch (error) {
      toast.error("Failed to initiate call");
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const handleResolve = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // TODO: Replace with actual API call
      // await fetch('/api/resolve', {
      //   method: 'POST',
      //   body: JSON.stringify({ id })
      // });
      setComplaints((prev) =>
        prev.map((complaint) =>
          complaint.id === id ? { ...complaint, resolved: true } : complaint
        )
      );
      toast.success("Complaint marked as resolved");
    } catch (error) {
      toast.error("Failed to resolve complaint");
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const getDayComplaints = (day: Date) => {
    const formattedDay = format(day, "dd-MM-yyyy");
    return complaints.filter(
      (complaint) =>
        complaint.date === formattedDay ||
        complaint.callScheduled === formattedDay
    );
  };

  const getDateStyle = (day: Date) => {
    const formattedDay = format(day, "dd-MM-yyyy");
    const dayComplaints = complaints.filter(
      (complaint) => complaint.callScheduled === formattedDay
    );

    if (dayComplaints.length === 0) {
      const regularComplaints = complaints.filter(
        (complaint) => complaint.date === formattedDay
      );
      return regularComplaints.length > 0
        ? {
            backgroundColor: "rgba(99, 102, 241, 0.1)",
            borderRadius: "0.375rem",
          }
        : undefined;
    }

    const highestSeverity = Math.max(...dayComplaints.map((c) => c.severity));

    if (highestSeverity >= 0.8) {
      return {
        backgroundColor: "rgba(239, 68, 68, 0.2)",
        borderRadius: "0.375rem",
        fontWeight: "bold",
      };
    } else if (highestSeverity >= 0.5) {
      return {
        backgroundColor: "rgba(234, 179, 8, 0.2)",
        borderRadius: "0.375rem",
        fontWeight: "bold",
      };
    }
    return {
      backgroundColor: "rgba(34, 197, 94, 0.2)",
      borderRadius: "0.375rem",
      fontWeight: "bold",
    };
  };

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 bg-white dark:bg-gray-800">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900">
                <Users className="h-6 w-6 text-purple-600 dark:text-purple-300" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Total Complaints
                </p>
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
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Resolved
                </p>
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
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Unresolved
                </p>
                <p className="text-2xl font-bold">{unresolvedComplaints}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <Card className="bg-white dark:bg-gray-800 mb-8">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Call Scheduled</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {complaints.map((complaint) => (
              <TableRow key={complaint.id}>
                <TableCell className="font-medium">
                  {complaint.customerName}
                </TableCell>
                <TableCell>{complaint.subject}</TableCell>
                <TableCell>{complaint.date}</TableCell>
                <TableCell>
                  {complaint.callScheduled || "Not Scheduled"}
                </TableCell>
                <TableCell>
                  <Badge className={getSeverityColor(complaint.severity)}>
                    {(complaint.severity * 100).toFixed(0)}%
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className={getPriorityColor(complaint.priority)}>
                    {complaint.priority}
                  </Badge>
                </TableCell>
                <TableCell>
                  {complaint.resolved ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleCall(complaint.phone, complaint.id)}
                      disabled={loading[complaint.id]}
                      className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
                    >
                      <Phone className="h-4 w-4 mr-2" />
                      Call
                    </Button>
                    {!complaint.resolved && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleResolve(complaint.id)}
                        disabled={loading[complaint.id]}
                        className="border-green-500 text-green-500 hover:bg-green-50 dark:hover:bg-green-950"
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Resolve
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Card className="bg-white dark:bg-gray-800 p-6">
        <div className="flex flex-col md:flex-row gap-8">
          <div className="flex-1 max-w-xl">
            {" "}
            {/* Added min-width */}
            <h2 className="text-xl font-semibold mb-4">Complaint Calendar</h2>
            <div className="mb-4">
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-red-200"></div>
                  <span>High Severity Call</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-yellow-200"></div>
                  <span>Medium Severity Call</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-green-200"></div>
                  <span>Low Severity Call</span>
                </div>
              </div>
            </div>
            <Calendar
              selected={date}
              onSelect={(newDate) => {
                setDate(newDate);
                const complaints = newDate ? getDayComplaints(newDate) : [];
                setSelectedComplaint(complaints[0] || null);
              }}
              className="rounded-md border"
              complaints={complaints}
              defaultMonth={new Date(2025, 2)}
            />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold mb-4">
              Selected Date Details
            </h2>
            {date && selectedComplaint ? (
              <div className="space-y-4">
                <div className="p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="font-semibold mb-2 text-lg">
                    {selectedComplaint.customerName}
                  </h3>
                  <p className="text-base text-gray-600 dark:text-gray-400 mb-4">
                    {selectedComplaint.subject}
                  </p>
                  <div className="flex gap-2 mb-4">
                    <Badge
                      className={getSeverityColor(selectedComplaint.severity)}
                    >
                      Severity: {(selectedComplaint.severity * 100).toFixed(0)}%
                    </Badge>
                    <Badge
                      className={getPriorityColor(selectedComplaint.priority)}
                    >
                      {selectedComplaint.priority}
                    </Badge>
                  </div>
                  <p className="text-base">
                    <strong>Call Scheduled:</strong>{" "}
                    {selectedComplaint.callScheduled || "Not Scheduled"}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                Select a date to view complaint details
              </p>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
