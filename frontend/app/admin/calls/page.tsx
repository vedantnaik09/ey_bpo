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

// Adjust this interface to match what /transcripts actually returns:
interface Transcript {
  id: number
  phone_number: string
  call_transcript: string
  called_at: string // The date/time field from your DB
}

export default function CallsPage() {
  const { push } = useRouter()
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        push("/")
      } else {
        const token = await user.getIdToken(true)
        localStorage.setItem("firebaseToken", token)
        const role = localStorage.getItem("userRole")
        if (role?.trim() !== "admin") {
          push("/dashboard")
          return
        }
        fetchTranscripts()
      }
    })

    return () => unsubscribe()
  }, [push])

  const fetchTranscripts = async () => {
    try {
      // /transcripts presumably returns an array of objects
      // with { id, phone_number, call_transcript, called_at, ... }
      const response = await axiosManagerInstance.get("/transcripts")
      const data = response.data as Transcript[]

      // Sort in descending order by called_at
      data.sort((a, b) => {
        const dateA = new Date(a.called_at).getTime()
        const dateB = new Date(b.called_at).getTime()
        return dateB - dateA // newest first
      })

      setTranscripts(data)
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
          <span className="ml-2">Loading transcripts...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8">
      <h1 className="text-3xl font-bold mb-6">Call Transcripts</h1>
      <div className="space-y-4">
        {transcripts.map((t) => (
          <Card key={t.id} className="p-4">
            <Accordion type="single" collapsible>
              <AccordionItem value={String(t.id)}>
                <AccordionTrigger>
                  <div className="flex justify-between w-full pr-6">
                    <div>
                      <span className="font-semibold">{t.phone_number}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {/* If called_at is valid, format it; else fallback */}
                      {t.called_at
                        ? format(new Date(t.called_at), "PPpp")
                        : "No Time"}
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2 mt-4">
                    <p>{t.call_transcript}</p>
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
