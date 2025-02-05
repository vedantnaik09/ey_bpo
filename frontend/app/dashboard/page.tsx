"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { format, parseISO, add } from "date-fns"
import { Card } from "@/components/ui/card"
import Calendar from "@/components/ui/calendar"
import RescheduleCalendar from "@/components/ui/reschedulecalendar"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Phone, CheckCircle, XCircle, Users, AlertCircle, CheckCircle2, Flag } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { onAuthStateChanged } from "firebase/auth"
import { auth } from "@/firebase/config"

interface Complaint {
  complaint_id: number
  ticket_id: string
  is_escalated: boolean
  customer_name: string
  customer_phone_number: string
  complaint_description: string
  sentiment_score: number
  urgency_score: number
  priority_score: number
  status: string
  scheduled_callback: string | null
  created_at: string
  knowledge_base_solution: string
}

const API_BASE_URL = "http://localhost:8000"

const getSeverityColor = (severity: number): string => {
  if (severity >= 0.8) return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
  if (severity >= 0.5) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
  return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
}

const getPriorityColor = (priority: number): string => {
  if (priority >= 0.7) return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
  if (priority >= 0.4) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
  return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
}

// Function to convert GMT to IST and format date
const formatToIST = (dateString: string): string => {
  if (!dateString) return "Not Scheduled"
  const date = parseISO(dateString)
  // Add 5 hours and 30 minutes to convert to IST
  const istDate = add(date, { hours: 5, minutes: 30 })
  return format(istDate, "dd-MM-yyyy")
}

const formatToISTstartWithYear = (dateString: string): string => {
  if (!dateString) return "Not Scheduled"
  const date = parseISO(dateString)
  // Add 5 hours and 30 minutes to convert to IST
  const istDate = add(date, { hours: 5, minutes: 30 })
  return format(istDate, "yyyy-MM-dd")
}

// Function to format time to IST with both date and time
const formatToISTWithTime = (dateString: string): string => {
  if (!dateString) return "Not Scheduled"
  const date = parseISO(dateString)
  // Add 5 hours and 30 minutes to convert to IST
  const istDate = add(date, { hours: 5, minutes: 30 })
  return format(istDate, "dd-MM-yyyy HH:mm")
}

export default function DashboardPage() {
  const { push } = useRouter()

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (!user) {
        push("/")
      }
    })

    return () => unsubscribe()
  }, [push])

  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [loading, setLoading] = useState<{ [key: number]: boolean }>({})
  const [date, setDate] = useState<Date>(new Date())
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint[] | null>(null)
  const [rescheduleComplaintId, setRescheduleComplaintId] = useState<number | null>(null)
  const [hoveredComplaintId, setHoveredComplaintId] = useState<number | null>(null)
  const [position, setPosition] = useState<{
    top: number
    left: number
  } | null>(null)

  useEffect(() => {
    fetchComplaints()
  }, [])

  useEffect(() => {
    if (complaints.length > 0) {
      const todayComplaints = getDayComplaints(new Date())
      setSelectedComplaint(todayComplaints)
    }
  }, [complaints]) // This will run whenever complaints are loaded or updated

  // Keep your existing useEffect for fetching complaints
  useEffect(() => {
    fetchComplaints()
  }, [])

  const handleOpenReschedule = (id: number) => {
    setRescheduleComplaintId(id)
  }

  const handleCloseReschedule = () => {
    setRescheduleComplaintId(null)
  }

  const fetchComplaints = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/`)
      const data: Complaint[] = await response.json()
      setComplaints(data)
    } catch (error) {
      toast.error("Failed to fetch complaints")
    }
  }

  const handleCall = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }))
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/${id}/resolve`, {
        method: "POST",
      })
      if (response.ok) {
        fetchComplaints()
        toast.success("Calling User")
      } else {
        toast.error("Failed to call")
      }
    } catch (error) {
      toast.error("Failed to call")
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }))
    }
  }

  const toggleResolve = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }))
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/${id}/toggleResolve`, {
        method: "POST",
      })
      if (response.ok) {
        fetchComplaints()
        toast.success("Complaint marked as resolved")
      } else {
        toast.error("Failed to resolve complaint")
      }
    } catch (error) {
      toast.error("Failed to resolve complaint")
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }))
    }
  }

  const getDayComplaints = (day: Date): Complaint[] => {
    const formattedDay = format(day, "yyyy-MM-dd")
    console.log("Formatted day ", formattedDay)
    return complaints.filter((complaint) =>
      formatToISTstartWithYear(complaint.scheduled_callback!).startsWith(formattedDay),
    )
  }

  const handleMouseEnter = (event: React.MouseEvent, complaintId: number) => {
    const rect = (event.target as HTMLElement).getBoundingClientRect()
    setPosition({
      top: rect.top + window.scrollY, // Top position of the row
      left: rect.left + window.scrollX, // Left position of the row
    })
    setHoveredComplaintId(complaintId)
  }

  const handleMouseLeave = () => {
    setHoveredComplaintId(null)
    setPosition(null)
  }

  const totalComplaints = complaints.length
  const resolvedComplaints = complaints.filter((c) => c.status === "resolved").length
  const unresolvedComplaints = totalComplaints - resolvedComplaints

  const toggleEscalation = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }))
    try {
      const response = await fetch(`${API_BASE_URL}/complaints/${id}/toggleEscalation`, {
        method: "POST",
      })
      if (response.ok) {
        fetchComplaints()
        toast.success("Escalation status updated")
      } else {
        toast.error("Failed to update escalation status")
      }
    } catch (error) {
      toast.error("Failed to update escalation status")
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }))
    }
  }

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

      <Card className="bg-white dark:bg-gray-800 mb-8">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer</TableHead>
              <TableHead>Ticket ID</TableHead>
              <TableHead>Phone Number</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Callback</TableHead>
              <TableHead>Sentiment</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Escalation</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {complaints.map((complaint) => (
              <TableRow
                key={complaint.complaint_id}
                className={`group ${complaint.is_escalated ? "hover:bg-red-950/30" : ""}`}
              >
                <TableCell className="font-medium">{complaint.customer_name}</TableCell>
                <TableCell className="font-medium">
                  #{complaint.ticket_id || complaint.complaint_id.toString().padStart(4, "0")}
                </TableCell>
                <TableCell className="font-medium">{complaint.customer_phone_number}</TableCell>
                <TableCell>{complaint.complaint_description}</TableCell>
                <TableCell className="whitespace-nowrap">{formatToIST(complaint.created_at)}</TableCell>
                <TableCell>
                  <div className="text-center">
                    {complaint.scheduled_callback ? formatToIST(complaint.scheduled_callback) : "Not Scheduled"}
                  </div>
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
                  <Badge className={getSeverityColor(complaint.priority_score)}>
                    {(complaint.priority_score * 100).toFixed(0)}%
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge className={getPriorityColor(complaint.priority_score)}>
                    {complaint.priority_score >= 0.7 ? "High" : complaint.priority_score >= 0.4 ? "Medium" : "Low"}
                  </Badge>
                </TableCell>
                <TableCell>
                  {complaint.status === "resolved" ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex justify-center">
                    <button
                      onClick={() => toggleEscalation(complaint.complaint_id)}
                      disabled={loading[complaint.complaint_id]}
                      className="focus:outline-none"
                    >
                      <Flag
                        className={`h-5 w-5 transition-colors ${
                          complaint.is_escalated
                            ? "text-red-500 group-hover:fill-red-500"
                            : "text-gray-400 group-hover:text-red-500 group-hover:fill-red-500"
                        }`}
                      />
                    </button>
                  </div>
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
                        <span className="h-5 w-5 rounded-full bg-blue-500 text-white flex items-center justify-center">
                          i
                        </span>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleCall(complaint.complaint_id)}
                        disabled={loading[complaint.complaint_id]}
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 dark:hover:text-white"
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
                      className={`border-green-500 text-green-500 hover:bg-green-50 dark:hover:bg-green-950 ${
                        complaint.status !== "resolved" ? "mr-20" : ""
                      }`}
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
        {/* Display knowledge base solution when a row is hovered */}
        {hoveredComplaintId !== null && position && (
          <div
            className="absolute bg-gray-700 text-white text-xs rounded-md p-2 w-[200px]"
            style={{
              top: position.top + 30, // Slightly below the row
              left: position.left - 80, // Slightly to the right of the row
            }}
          >
            {complaints.find((complaint) => complaint.complaint_id === hoveredComplaintId)?.knowledge_base_solution}
          </div>
        )}
      </Card>

      {/* Reschedule Modal */}
      {rescheduleComplaintId && (
        <RescheduleCalendar
          complaintId={rescheduleComplaintId}
          onClose={handleCloseReschedule}
          onReschedule={fetchComplaints}
        />
      )}
      <Card className="bg-white dark:bg-gray-800 p-6">
        <div className="flex flex-col md:flex-row gap-8">
          <div className="flex flex-col md:flex-row gap-8">
            <div className="flex-1 max-w-xl">
              <h2 className="text-xl font-semibold mb-4">Complaint Calendar</h2>
              <Calendar
                selected={date}
                onSelect={(newDate) => {
                  if (newDate) {
                    setDate(newDate)
                    const complaintsForDay = getDayComplaints(newDate)
                    setSelectedComplaint(complaintsForDay || null)
                  }
                }}
                className="rounded-md border"
                complaints={complaints}
                defaultMonth={new Date()}
              />
            </div>
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold mb-4">Selected Date Details</h2>
            {date && selectedComplaint && selectedComplaint.length > 0 ? (
              <div className="space-y-4">
                {selectedComplaint.map((complaint) => (
                  <div
                    key={complaint.complaint_id}
                    className="p-6 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-lg">{complaint.customer_name}</h3>
                      <Badge className={getSeverityColor(complaint.priority_score)}>
                        Sentiment: {(complaint.priority_score * 100).toFixed(0)}%
                      </Badge>
                    </div>
                    <p className="text-base text-gray-600 dark:text-gray-400 mb-4">{complaint.complaint_description}</p>
                    <div className="flex justify-between items-center">
                      <p className="text-base">
                        <strong>Call Scheduled:</strong>{" "}
                        {complaint.scheduled_callback
                          ? formatToISTWithTime(complaint.scheduled_callback)
                          : "Not Scheduled"}
                      </p>
                      <Badge className={getPriorityColor(complaint.priority_score)}>
                        {complaint.priority_score >= 0.7
                          ? "High Priority"
                          : complaint.priority_score >= 0.4
                            ? "Medium Priority"
                            : "Low Priority"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                {date ? "No complaints found for this date" : "Select a date to view complaint details"}
              </p>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}

