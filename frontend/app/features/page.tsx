"use client"
import { PhoneCall,Bot } from "lucide-react"
import Link from "next/link"
import { Brain, Headset } from "lucide-react"
import { Card } from "@/components/ui/card"
import { GradientText } from "@/components/ui/gradient-text"
import type { LucideIcon } from "lucide-react"

interface Feature {
  icon: LucideIcon
  title: string
  description: string
  href?: string
}

interface FeatureCardProps extends Feature {
  user: boolean
}

const features: Feature[] = [
  {
    icon: PhoneCall, // For live call-related features
    title: "Complaint Management",
    description: "Effortlessly document customer complaints with real-time call transcription.",
    href: "/dashboard",
  },
  {
    icon: Bot, // Represents AI and automation
    title: "Cold Caller Agent",
    description: "Automate outreach with a CSV of phone numbers and provide personalized services using AI-powered tools.",
    href: "http://localhost:3001/",
  },
];

function FeatureCard({ icon: Icon, title, description, href, user }: FeatureCardProps) {
  const CardWrapper = href && user ? Link : "div"
  const cardProps = href && user ? { href } : {}

  return (
    <CardWrapper {...cardProps}>
      <Card className="group relative overflow-hidden p-8 transition-all hover:shadow-2xl hover:shadow-purple-100/50 dark:hover:shadow-purple-900/50 cursor-pointer">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-950/50 dark:to-indigo-950/50 opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="relative">
          <div className="mb-6 inline-block rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 p-3 text-white">
            <Icon className="h-6 w-6" />
          </div>
          <h3 className="mb-3 text-xl font-semibold">{title}</h3>
          <p className="text-gray-600 dark:text-gray-400">{description}</p>
          {href && user && (
            <p className="mt-4 text-sm font-medium text-purple-600 dark:text-purple-400">
              {title === "Calling BPO" ? "Go to Dashboard" : "Learn More"}
            </p>
          )}
        </div>
      </Card>
    </CardWrapper>
  )
}

interface FeaturesProps {
  user: boolean
}

function Features({ user }: FeaturesProps) {
  return (
    <section className="relative py-20 bg-gray-50/50 dark:bg-gray-900/50">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            <GradientText>Intelligent Features</GradientText> for Modern BPOs
          </h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Streamline your operations with our comprehensive suite of AI-powered tools
          </p>
        </div>
        <div className="flex flex-col md:flex-row justify-between items-center gap-8">
          {features.map((feature) => (
            <div key={feature.title} className="w-full md:w-5/12">
              <FeatureCard {...feature} user={user} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default function FeaturesPage() {
  // You might want to fetch the user state here
  const user = false // This should be replaced with actual user state

  return <Features user={user} />
}