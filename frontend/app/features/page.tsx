import Link from "next/link"
import { Check } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Features } from "@/components/sections/features"

export default function PricingPage() {
  return (
    <div className="bg-black min-h-screen">
      <div className="container px-4 py-24 mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
            Features of Resolvr
          </h1>
          <Features/>
        </div>
      </div>
    </div>
  )
}