"use client"

import { useState, useEffect } from "react"
import { onAuthStateChanged, type User } from "firebase/auth"
import { auth } from "@/firebase/config"
import { Hero } from "@/components/sections/hero"
import { Features } from "@/components/sections/features"
import { CTA } from "@/components/sections/cta"

export default function Home() {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser)
    })

    // Cleanup subscription on unmount
    return () => unsubscribe()
  }, [])

  return (
    <main className="min-h-screen bg-white dark:bg-gray-950">
      <Hero />
      <Features user={!!user} />
      <CTA />
    </main>
  )
}