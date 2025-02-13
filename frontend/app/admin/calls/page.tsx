"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card } from "@/components/ui/card"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { format } from "date-fns"
import { toast } from "sonner"
import axiosManagerInstance from "@/utils/axiosManager"
import { onAuthStateChanged } from "firebase/auth"
import { auth } from "@/firebase/config"
import { Loader2 } from "lucide-react"

interface Message {
  message_id: string
  sender: string
  message: string
  timestamp: string
}

interface Call {
  call_id: string
  caller: string
  receiver: string
  start_time: string
  end_time: string | null
  created_at: string
  messages: Message[]
}

export default function CallsPage() {
  const { push } = useRouter()
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        push("/")
      } else {
        const token = await user.getIdToken(true)
        localStorage.setItem("firebaseToken", token)
        const role = localStorage.getItem("userRole")
        if (role !== "admin") {
          push("/dashboard")
        }
        fetchCalls()
      }
    })

    return () => unsubscribe()
  }, [push])

  const fetchCalls = async () => {
    try {
      const response = await axiosManagerInstance.get("/calls")
      setCalls(response.data)
    } catch (error) {
      toast.error("Failed to fetch calls")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
          <span className="ml-2">Loading calls...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8">
      <h1 className="text-3xl font-bold mb-6">Call Transcripts</h1>
      <div className="space-y-4">
        {calls.map((call) => (
          <Card key={call.call_id} className="p-4">
            <Accordion type="single" collapsible>
              <AccordionItem value={call.call_id}>
                <AccordionTrigger>
                  <div className="flex justify-between w-full pr-6">
                    <div>
                      <span className="font-semibold">
                        {call.caller} → {call.receiver}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {format(new Date(call.start_time), "PPpp")}
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2 mt-4">
                    {call.messages?.map((msg) => (
                      <div
                        key={msg.message_id}
                        className={`flex gap-2 ${
                          msg.sender === call.caller
                            ? "justify-start"
                            : "justify-end"
                        }`}
                      >
                        <div
                          className={`rounded-lg p-3 max-w-[80%] ${
                            msg.sender === call.caller
                              ? "bg-gray-100 dark:bg-gray-800"
                              : "bg-blue-100 dark:bg-blue-900"
                          }`}
                        >
                          <p className="text-sm font-semibold">{msg.sender}</p>
                          <p>{msg.message}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {format(new Date(msg.timestamp), "pp")}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </Card>
        ))}
      </div>
    </div>
  )
}