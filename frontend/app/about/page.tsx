import Image from "next/image"
import { Button } from "@/components/ui/button"
import { ArrowRight, Brain, Clock, Heart, TrendingUp } from 'lucide-react'

export default function AboutPage() {
  return (
    <div className="bg-black min-h-screen">
      <div className="container px-4 py-24 mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
            Transforming BPO Operations with AI
          </h1>
          <p className="mt-6 text-xl text-gray-400 max-w-3xl mx-auto">
            We're revolutionizing claims processing in Indian BPOs through intelligent automation, 
            making life easier for agents like Nisha while delivering exceptional client experiences.
          </p>
        </div>

        {/* Problem Solution Section */}
        <div className="grid md:grid-cols-2 gap-12 items-center my-20">
          <div>
            <h2 className="text-3xl font-bold text-white mb-6">The Challenge We're Solving</h2>
            <p className="text-gray-400 leading-relaxed">
              BPO agents handle overwhelming volumes of claims calls daily, struggling with manual scheduling,
              multiple system entries, and outdated knowledge bases. We've created an AI-powered solution that
              automates routine tasks, analyzes client sentiment, and provides instant access to relevant information.
            </p>
            <Button className="mt-8 bg-purple-600 hover:bg-purple-700">
              Learn More
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              {
                icon: Clock,
                title: "Automated Scheduling",
                description: "Smart callback scheduling based on claim priority"
              },
              {
                icon: Heart,
                title: "Sentiment Analysis",
                description: "Real-time client emotion detection"
              },
              {
                icon: Brain,
                title: "Smart Knowledge Base",
                description: "AI-powered information retrieval"
              },
              {
                icon: TrendingUp,
                title: "Enhanced Efficiency",
                description: "Streamlined workflow automation"
              }
            ].map((feature) => (
              <div key={feature.title} className="bg-gray-900 p-6 rounded-lg">
                <feature.icon className="h-8 w-8 text-purple-500 mb-4" />
                <h3 className="text-white font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-400 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Impact Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 my-20">
          {[
            { number: "60%", label: "Reduction in Processing Time" },
            { number: "85%", label: "Agent Satisfaction" },
            { number: "40%", label: "Increase in First Call Resolution" },
            { number: "90%", label: "Accurate Sentiment Analysis" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-4xl font-bold text-purple-500 mb-2">{stat.number}</div>
              <div className="text-gray-400">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Case Study */}
        <div className="bg-gray-900 rounded-xl p-8 my-20">
          <h2 className="text-2xl font-bold text-white mb-6">Success Story: Claims Processing Transformation</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <p className="text-gray-400 mb-4">
                "The AI-powered system has transformed how we handle claims. Our agents are more efficient,
                our clients are happier, and our processing times have been cut in half. The automated
                scheduling and sentiment analysis features have been game-changers for our operations."
              </p>
              <p className="text-white font-semibold">- Leading Indian BPO Manager</p>
            </div>
            <div className="relative h-[200px] rounded-lg overflow-hidden">
              <Image
                src="/placeholder.svg"
                alt="BPO Success Story"
                fill
                className="object-cover"
              />
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center mt-20">
          <h2 className="text-3xl font-bold text-white mb-6">Ready to Transform Your BPO Operations?</h2>
          <p className="text-gray-400 mb-8">
            Join leading Indian BPOs in revolutionizing claims processing with AI-powered automation
          </p>
          <div className="flex gap-4 justify-center">
            <Button className="bg-purple-600 hover:bg-purple-700">
              Start Free Trial
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button variant="outline">Schedule Demo</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
